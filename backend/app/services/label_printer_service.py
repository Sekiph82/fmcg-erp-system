"""Network label printing: ZPL (Zebra) / TSPL (TSC, Godex-compatible) over raw TCP (port 9100).

Labels are rendered server-side from GS1 records — lot labels carry a GS1-128 barcode of the
record's AI string, pallet labels the SSCC as AI (00) — and streamed to a registered printer.
Printer hosts are resolved once, every address must be private/loopback/link-local (never the
cloud metadata address), and the connection goes to the validated IP literal, so DNS cannot
redirect a print job to the internet or a metadata endpoint between check and connect.
Barcode data is never truncated or altered: unprintable data fails the job instead.
"""
from __future__ import annotations

import asyncio
import ipaddress
import socket
from dataclasses import dataclass
from datetime import date
from typing import Optional

CONNECT_TIMEOUT_SECONDS = 5.0
SEND_TIMEOUT_SECONDS = 10.0
MAX_GS1_DATA_CHARS = 48       # GS1-128 limit on encoded data characters (AIs + values, excluding brackets)
MAX_PLAIN_DATA_CHARS = 80
_METADATA = ipaddress.ip_address("169.254.169.254")
_TEREDO = ipaddress.ip_network("2001::/32")


class PrinterError(RuntimeError):
    pass


@dataclass(frozen=True)
class LabelContent:
    """One label: barcode data (GS1 element string in AI form, or plain value) plus caption lines."""
    barcode_ai_string: str            # e.g. "(01)06123456789012(10)LOT42(17)271231"
    title: str
    lines: tuple[str, ...] = ()
    copies: int = 1
    gs1: bool = True                  # False: plain Code 128 of the value (no FNC1 / AI parsing)


@dataclass(frozen=True)
class PrinterSpec:
    protocol: str                     # ZPL | TSPL
    dpi: int = 203
    width_mm: int = 100
    height_mm: int = 150


def _caption(text: str) -> str:
    """Caption text: printable ASCII without ZPL/TSPL control characters, shortened to fit."""
    return "".join(ch for ch in (text or "") if 32 <= ord(ch) < 127 and ch not in '^~"\\')[:60]


def _barcode_data(label: LabelContent) -> str:
    """Barcode payload is printed exactly as recorded or the job fails — never silently changed."""
    data = label.barcode_ai_string or ""
    bad = sorted({ch for ch in data if not (32 <= ord(ch) < 127) or ch in '^~"\\'})
    if bad:
        raise PrinterError(f"Barcode data {data!r} contains characters that cannot be printed: {''.join(bad)!r}.")
    encoded = len(data.replace("(", "").replace(")", "")) if label.gs1 else len(data)
    limit = MAX_GS1_DATA_CHARS if label.gs1 else MAX_PLAIN_DATA_CHARS
    if not data or encoded > limit:
        raise PrinterError(f"Barcode data {data!r} has {encoded} characters; the limit is {limit}.")
    return data


def _dots(spec: PrinterSpec, mm: float) -> int:
    return round(mm * spec.dpi / 25.4)


def _module_width(data: str) -> int:
    return 2 if len(data) <= 30 else 1     # keep long GS1-128 symbols inside a 100 mm label


def render_zpl(spec: PrinterSpec, label: LabelContent) -> str:
    """ZPL II with ^BC mode D (GS1-128: FNC1 start, AIs in parentheses printed as HRI)."""
    data = _barcode_data(label)
    copies = max(1, min(int(label.copies), 999))
    out = ["^XA", f"^PW{_dots(spec, spec.width_mm)}", f"^LL{_dots(spec, spec.height_mm)}", "^CI28",
           f"^FO40,30^A0N,40,40^FD{_caption(label.title)}^FS"]
    y = 90
    for line in label.lines[:6]:
        out.append(f"^FO40,{y}^A0N,28,28^FD{_caption(line)}^FS")
        y += 38
    mode = "D" if label.gs1 else "N"
    out.append(f"^FO40,{y + 20}^BY{_module_width(data)}^BCN,{_dots(spec, 20)},Y,N,N,{mode}^FD{data}^FS")
    out += [f"^PQ{copies}", "^XZ"]
    return "\n".join(out) + "\n"


def render_tspl(spec: PrinterSpec, label: LabelContent) -> str:
    """TSPL/TSPL2 with an EAN128 (GS1-128) or 128 barcode."""
    data = _barcode_data(label)
    copies = max(1, min(int(label.copies), 999))
    out = [f"SIZE {spec.width_mm} mm, {spec.height_mm} mm", "GAP 3 mm, 0 mm", "DIRECTION 1", "CLS",
           f'TEXT 40,30,"3",0,1,1,"{_caption(label.title)}"']
    y = 90
    for line in label.lines[:6]:
        out.append(f'TEXT 40,{y},"2",0,1,1,"{_caption(line)}"')
        y += 38
    symbology = "EAN128" if label.gs1 else "128"
    narrow = _module_width(data)
    out.append(f'BARCODE 40,{y + 20},"{symbology}",{_dots(spec, 20)},1,0,{narrow},{narrow * 2},"{data}"')
    out.append(f"PRINT 1,{copies}")
    return "\r\n".join(out) + "\r\n"


def render(spec: PrinterSpec, labels: list[LabelContent]) -> bytes:
    renderer = {"ZPL": render_zpl, "TSPL": render_tspl}.get(spec.protocol.upper())
    if renderer is None:
        raise PrinterError(f"Unsupported printer protocol {spec.protocol!r}; use ZPL or TSPL.")
    if not labels:
        raise PrinterError("Nothing to print.")
    return "".join(renderer(spec, label) for label in labels).encode("ascii")


def lot_label(gtin: str, lot: str, ai_string: str, expiry: Optional[date], product: Optional[str], copies: int) -> LabelContent:
    lines = [f"GTIN {gtin}", f"LOT {lot}"]
    if expiry:
        lines.append(f"EXP {expiry.isoformat()}")
    return LabelContent(barcode_ai_string=ai_string, title=product or f"GTIN {gtin}", lines=tuple(lines), copies=copies)


def sscc_label(sscc: str, pallet_id: Optional[str], shipment: Optional[str], copies: int) -> LabelContent:
    lines = [f"SSCC {sscc}"] + ([f"PALLET {pallet_id}"] if pallet_id else []) + ([f"SHIPMENT {shipment}"] if shipment else [])
    return LabelContent(barcode_ai_string=f"(00){sscc}", title="SSCC PALLET LABEL", lines=tuple(lines), copies=copies)


def _allowed(address: ipaddress._BaseAddress) -> bool:
    if address.version == 6 and address.ipv4_mapped:
        address = address.ipv4_mapped
    if address == _METADATA or address.is_unspecified or address.is_multicast:
        return False
    if address.version == 6 and address in _TEREDO:
        return False
    return address.is_private or address.is_loopback or address.is_link_local


async def resolve_printer_addresses(host: str) -> list[str]:
    """Resolve once (without blocking the event loop); every address must be on a private network."""
    loop = asyncio.get_running_loop()
    try:
        infos = await loop.getaddrinfo(host.strip(), None, type=socket.SOCK_STREAM)
    except (socket.gaierror, UnicodeError, ValueError) as exc:
        raise PrinterError(f"Printer host {host!r} cannot be resolved.") from exc
    addresses = []
    for info in infos:
        address = ipaddress.ip_address(info[4][0].split("%")[0])
        if not _allowed(address):
            raise PrinterError(f"Printer host {host!r} resolves to {address}, which is not a private network address.")
        if str(address) not in addresses:
            addresses.append(str(address))
    if not addresses:
        raise PrinterError(f"Printer host {host!r} cannot be resolved.")
    return addresses


async def send_raw(host: str, port: int, payload: bytes) -> None:
    addresses = await resolve_printer_addresses(host)
    last_error: Optional[BaseException] = None
    for address in addresses:   # connect to the validated literal, never re-resolve the name
        try:
            _, writer = await asyncio.wait_for(asyncio.open_connection(address, port), CONNECT_TIMEOUT_SECONDS)
            break
        except (OSError, asyncio.TimeoutError) as exc:
            last_error = exc
    else:
        raise PrinterError(f"Cannot connect to printer {host}:{port}: {last_error or 'timeout'}")
    try:
        writer.write(payload)
        await asyncio.wait_for(writer.drain(), SEND_TIMEOUT_SECONDS)
    except (OSError, asyncio.TimeoutError) as exc:
        raise PrinterError(f"Sending to printer {host}:{port} failed: {exc or 'timeout'}") from exc
    finally:
        writer.close()
        try:
            await asyncio.wait_for(writer.wait_closed(), SEND_TIMEOUT_SECONDS)
        except (OSError, asyncio.TimeoutError):
            pass
