"""Outbound HTTP to external providers (M43.S00.T004): one client factory with an egress guard.

Every provider adapter (Gmail, Microsoft Graph, calendars, voice, ads, ...) builds its client here, so tests and
local development cannot reach a real provider by accident:

- PROVIDER_EGRESS = "live"  → any https host (production default).
- PROVIDER_EGRESS = "local" → only loopback / *.localhost / *.test hosts, i.e. the local provider simulator
  (default outside production). A request to anywhere else raises EgressBlocked before a socket is opened.
- PROVIDER_EGRESS = "off"   → no provider traffic at all.

Live mode also PINS the connection (DNS-rebinding defence): the name is resolved once at connect time, every resolved
address must be public, and the socket is opened to one of those validated addresses while the Host header and the TLS
SNI / certificate check keep using the original hostname. The pre-flight check in check_egress is only a fast refusal.

Tests may install an in-process transport (httpx.ASGITransport over tests/provider_sim) with set_test_transport();
the adapter code path is identical, only the wire is replaced.
"""
from __future__ import annotations

import asyncio
import ipaddress
import socket
from typing import Optional
from urllib.parse import urlsplit

import httpcore
import httpx

from app.core.config import settings

_LOCAL_SUFFIXES = (".localhost", ".test")
_test_transport: Optional[httpx.AsyncBaseTransport] = None


class EgressBlocked(RuntimeError):
    """A provider request was refused by the egress policy (nothing was sent)."""


def egress_mode() -> str:
    mode = (getattr(settings, "PROVIDER_EGRESS", "") or "").strip().lower()
    if mode in ("live", "local", "off"):
        return mode
    return "live" if settings.ENVIRONMENT == "production" else "local"


def _is_local_host(host: str) -> bool:
    host = (host or "").strip("[]").lower()
    if host == "localhost" or host.endswith(_LOCAL_SUFFIXES):
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def check_egress(url: str) -> None:
    parts = urlsplit(str(url))
    mode = egress_mode()
    if mode == "off":
        raise EgressBlocked("Provider traffic is switched off (PROVIDER_EGRESS=off).")
    if mode == "local":
        if not _is_local_host(parts.hostname or ""):
            raise EgressBlocked(f"Only local provider simulators are allowed here; refused {parts.hostname}.")
        return
    if parts.scheme != "https":
        raise EgressBlocked("Live provider calls must use https.")
    _refuse_internal(parts.hostname or "")


def _refuse_internal(host: str) -> None:
    """Live mode only talks to public internet hosts: refuse names that resolve to internal addresses (SSRF)."""
    import socket
    try:
        infos = socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
    except OSError:
        raise EgressBlocked(f"Cannot resolve {host}.") from None
    for info in infos:
        ip = ipaddress.ip_address(info[4][0].split("%")[0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
            raise EgressBlocked(f"{host} resolves to an internal address; refused.")


async def _guard(request: httpx.Request) -> None:
    import asyncio
    await asyncio.to_thread(check_egress, str(request.url))   # DNS lookup off the event loop


def _public(ip: ipaddress._BaseAddress) -> bool:
    return ip.is_global and not ip.is_multicast


async def _getaddrinfo(host: str, port: int) -> list[str]:
    infos = await asyncio.get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM)
    return [i[4][0].split("%")[0] for i in infos]


_resolver = _getaddrinfo      # tests replace this through set_resolver()


def set_resolver(fn) -> None:
    """Replace the connect-time DNS resolver (tests only); None restores the system one."""
    global _resolver
    _resolver = fn or _getaddrinfo


class PinnedBackend(httpcore.AsyncNetworkBackend):
    """Resolve once, validate EVERY address, connect to a validated address. Because the TCP target is an IP that was
    checked, a hostname that answers differently the second time (DNS rebinding) cannot redirect the request inwards."""

    def __init__(self, inner: Optional[httpcore.AsyncNetworkBackend] = None):
        self._inner = inner or httpcore.AnyIOBackend()

    async def connect_tcp(self, host, port, timeout=None, local_address=None, socket_options=None):
        try:
            ips = [str(ipaddress.ip_address(host))] if _is_ip(host) else await _resolver(host, port)
        except OSError:
            raise EgressBlocked(f"Cannot resolve {host}.") from None
        addrs = [ipaddress.ip_address(i) for i in ips]
        if not addrs or not all(_public(a) for a in addrs):
            raise EgressBlocked(f"{host} resolves to an internal address; refused.")
        last: Optional[Exception] = None
        for a in addrs:
            try:
                return await self._inner.connect_tcp(str(a), port, timeout=timeout, local_address=local_address,
                                                     socket_options=socket_options)
            except (httpcore.ConnectError, httpcore.ConnectTimeout, OSError) as e:
                last = e
        raise last or EgressBlocked(f"Cannot connect to {host}.")

    async def connect_unix_socket(self, path, timeout=None, socket_options=None):
        raise EgressBlocked("Unix sockets are not allowed for provider traffic.")

    async def sleep(self, seconds: float) -> None:
        await self._inner.sleep(seconds)


def _is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def pinned_transport() -> httpx.AsyncHTTPTransport:
    t = httpx.AsyncHTTPTransport()
    t._pool._network_backend = PinnedBackend()      # httpx exposes no public hook for the network backend
    return t


def set_test_transport(transport: Optional[httpx.AsyncBaseTransport]) -> None:
    """Route every provider client through ``transport`` (tests only); None restores the network."""
    global _test_transport
    _test_transport = transport


def provider_client(timeout: float = 20.0, **kwargs) -> httpx.AsyncClient:
    if _test_transport is not None:
        kwargs.setdefault("transport", _test_transport)
    elif "transport" not in kwargs and egress_mode() == "live":
        kwargs["transport"] = pinned_transport()
    hooks = kwargs.pop("event_hooks", {}) or {}
    hooks = {**hooks, "request": [_guard, *hooks.get("request", [])]}
    return httpx.AsyncClient(timeout=timeout, follow_redirects=False, event_hooks=hooks, **kwargs)
