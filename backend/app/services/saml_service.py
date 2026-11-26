"""M50.S01.T010 staff single sign-on with SAML 2.0 (SP-initiated, HTTP-Redirect AuthnRequest, HTTP-POST response).

Library: python3-saml (OneLogin SAML toolkit) on xmlsec/lxml. Official contract: OASIS SAML 2.0 Core, Bindings and Profiles
(https://docs.oasis-open.org/security/saml/v2.0/) and the Web Browser SSO profile; toolkit docs
https://github.com/SAML-Toolkits/python3-saml (v1.16).

What is enforced, and by whom:
- The assertion must be signed by the IdP certificate configured by an administrator (xmlsec, RSA-SHA256/SHA-512; SHA-1 and
  other deprecated algorithms are rejected). A wrong or missing signature, a signature wrapping attempt or a DOCTYPE is refused.
- Audience = our SP entity id, Recipient/Destination = our ACS URL, Issuer = the configured IdP entity id (toolkit, strict mode).
- NotBefore / NotOnOrAfter / SubjectConfirmation NotOnOrAfter with the configured clock skew (<= 120 s).
- SP-initiated only: the response must answer an AuthnRequest we issued (InResponseTo), once, within 10 minutes. The request
  id is bound to the browser by a cookie (login CSRF). IdP-initiated responses are refused.
- Replay: every accepted assertion id is stored until it expires; presenting it again is refused.
- Only a pre-provisioned, active, non-privileged ERP user (matched by the e-mail attribute) is signed in; groups map to roles.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlsplit

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.m50_data_sso import SamlAssertionSeen, SamlConfig, SamlRequest
from app.services.sso_service import SSOError, login_user

REQUEST_TTL = timedelta(minutes=10)
ACS_PATH = "/api/v1/sso/saml/acs"
METADATA_PATH = "/api/v1/sso/saml/metadata"
MAX_RESPONSE_BYTES = 512 * 1024


def available() -> tuple[bool, str]:
    try:
        import xmlsec  # noqa: F401
        from onelogin.saml2.auth import OneLogin_Saml2_Auth  # noqa: F401
        return True, "python3-saml + xmlsec"
    except Exception as e:                   # missing wheel / native library
        return False, f"{type(e).__name__}: {e}"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def acs_url() -> str:
    return settings.PUBLIC_API_URL.rstrip("/") + ACS_PATH


def default_sp_entity_id() -> str:
    return settings.PUBLIC_API_URL.rstrip("/") + METADATA_PATH


def pem(cert: str) -> str:
    """The certificate as PEM; accepts PEM or the bare base64 body."""
    body = "".join(l for l in cert.strip().splitlines() if "CERTIFICATE" not in l).replace(" ", "")
    return "-----BEGIN CERTIFICATE-----\n" + "\n".join(body[i:i + 64] for i in range(0, len(body), 64)) + "\n-----END CERTIFICATE-----\n"


def check_certificate(cert: str) -> dict:
    """Parse the IdP certificate (public part only); refuse private keys and unparsable input."""
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes
    if "PRIVATE KEY" in cert:
        raise ValueError("Paste the IdP's public certificate, never a private key.")
    try:
        c = x509.load_pem_x509_certificate(pem(cert).encode())
    except Exception:
        raise ValueError("The certificate could not be read (expected PEM / base64 X.509).")
    return {"subject": c.subject.rfc4514_string(), "not_after": c.not_valid_after_utc.isoformat(),
            "expired": c.not_valid_after_utc < _now(), "sha256": c.fingerprint(hashes.SHA256()).hex()}


def sp_settings(cfg: SamlConfig) -> dict:
    return {
        "strict": True, "debug": False,
        "sp": {"entityId": cfg.sp_entity_id,
               "assertionConsumerService": {"url": acs_url(), "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"},
               "NameIDFormat": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"},
        "idp": {"entityId": cfg.idp_entity_id,
                "singleSignOnService": {"url": cfg.idp_sso_url, "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"},
                "x509cert": pem(cfg.idp_x509_cert)},
        "security": {"authnRequestsSigned": False, "wantAssertionsSigned": True, "wantMessagesSigned": False,
                     "wantAssertionsEncrypted": False, "wantNameId": True, "rejectDeprecatedAlgorithm": True,
                     "requestedAuthnContext": False, "allowRepeatAttributeName": False,
                     "signatureAlgorithm": "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256",
                     "digestAlgorithm": "http://www.w3.org/2001/04/xmlenc#sha256"},
    }


def _request_data(post: Optional[dict] = None) -> dict:
    u = urlsplit(settings.PUBLIC_API_URL)
    port = u.port or (443 if u.scheme == "https" else 80)
    return {"https": "on" if u.scheme == "https" else "off", "http_host": u.hostname, "server_port": str(port),
            "script_name": ACS_PATH, "get_data": {}, "post_data": post or {}}


async def active_config(db: AsyncSession) -> Optional[SamlConfig]:
    return (await db.execute(select(SamlConfig).where(SamlConfig.active.is_(True)).order_by(SamlConfig.updated_at.desc()))).scalars().first()


def metadata_xml(cfg: SamlConfig) -> str:
    from onelogin.saml2.settings import OneLogin_Saml2_Settings
    st = OneLogin_Saml2_Settings(sp_settings(cfg), sp_validation_only=True)
    xml = st.get_sp_metadata()
    errors = st.validate_metadata(xml)
    if errors:
        raise SSOError(500, "Service provider metadata is invalid: " + ", ".join(errors))
    return xml.decode() if isinstance(xml, bytes) else xml


async def start(db: AsyncSession, cfg: SamlConfig, redirect_to: Optional[str] = None) -> tuple[str, str]:
    """→ (IdP redirect URL, request id). The request id is also set as a browser-bound cookie by the caller."""
    from onelogin.saml2.auth import OneLogin_Saml2_Auth
    ok, why = available()
    if not ok:
        raise SSOError(503, f"SAML library unavailable ({why}).")
    auth = OneLogin_Saml2_Auth(_request_data(), sp_settings(cfg))
    state = secrets.token_urlsafe(16)
    url = auth.login(return_to=state)
    rid = auth.get_last_request_id()
    db.add(SamlRequest(request_id=rid, config_id=cfg.id,
                       redirect_to=redirect_to if (redirect_to or "").startswith("/dashboard") else "/dashboard"))
    await db.flush()
    return url, rid


def _in_response_to(b64: str) -> Optional[str]:
    """InResponseTo of the (still unverified) response, read with a hardened parser; only used to look up our own request."""
    import base64
    from lxml import etree
    try:
        raw = base64.b64decode(b64, validate=False)
        if len(raw) > MAX_RESPONSE_BYTES or b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
            return None
        root = etree.fromstring(raw, etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False, huge_tree=False))
        return root.get("InResponseTo")
    except Exception:
        return None


async def acs(db: AsyncSession, saml_response: str, cookie_request_id: str) -> tuple:
    """→ (user, attributes, redirect_to). Raises SSOError for every refusal (the caller audits `audit_reason`)."""
    import hmac
    from onelogin.saml2.auth import OneLogin_Saml2_Auth
    from onelogin.saml2.constants import OneLogin_Saml2_Constants
    cfg = await active_config(db)
    if cfg is None:
        raise SSOError(403, "SAML single sign-on is not active.", "saml_inactive")
    if not saml_response or len(saml_response) > MAX_RESPONSE_BYTES * 2:
        raise SSOError(400, "No SAML response received.", "saml_empty")
    rid = _in_response_to(saml_response)
    if not rid:
        raise SSOError(400, "This response does not answer a sign-in started here (IdP-initiated sign-in is not accepted).", "saml_no_in_response_to")
    if not hmac.compare_digest((cookie_request_id or "").encode(), rid.encode()):
        raise SSOError(400, "This sign-in was not started in this browser; start again.", "saml_not_bound")
    req = await db.get(SamlRequest, rid, with_for_update=True)
    if req is None or req.config_id != cfg.id:
        raise SSOError(400, "Unknown sign-in request.", "saml_unknown_request")
    if req.used_at is not None:
        raise SSOError(400, "This sign-in was already used.", "saml_request_replay")
    req.used_at = _now()                                       # burned even if the response then fails
    await db.flush()
    if req.created_at < _now() - REQUEST_TTL:
        raise SSOError(400, "This sign-in request expired; start again.", "saml_request_expired")
    OneLogin_Saml2_Constants.ALLOWED_CLOCK_DRIFT = max(0, min(int(cfg.clock_skew_seconds or 60), 120))
    auth = OneLogin_Saml2_Auth(_request_data({"SAMLResponse": saml_response}), sp_settings(cfg))
    try:
        auth.process_response(request_id=rid)
    except Exception as e:                                     # malformed / hostile XML
        raise SSOError(401, "The SAML response could not be processed.", f"saml_invalid_xml:{type(e).__name__}")
    errors = auth.get_errors()
    if errors or not auth.is_authenticated():
        reason = (auth.get_last_error_reason() or ",".join(errors) or "not authenticated")[:200]
        raise SSOError(401, "The identity provider's response was rejected.", f"saml_rejected:{','.join(errors) or 'unauthenticated'}:{reason}")
    aid = auth.get_last_assertion_id()
    if not aid:
        raise SSOError(401, "The assertion has no id.", "saml_no_assertion_id")
    exp = auth.get_last_assertion_not_on_or_after()
    seen = await db.execute(insert(SamlAssertionSeen).values(
        assertion_id=aid[:200], config_id=cfg.id, not_on_or_after=datetime.fromtimestamp(exp, timezone.utc) if exp else None)
        .on_conflict_do_nothing().returning(SamlAssertionSeen.assertion_id))
    if seen.first() is None:
        raise SSOError(401, "This assertion was already used.", "saml_assertion_replay")
    await db.execute(SamlAssertionSeen.__table__.delete().where(SamlAssertionSeen.not_on_or_after < _now() - timedelta(hours=1)))
    attrs = auth.get_attributes()
    email = ((attrs.get(cfg.email_attribute) or [None])[0] or auth.get_nameid() or "").strip().lower()
    if "@" not in email:
        raise SSOError(403, "The identity provider did not send an e-mail address.", "saml_no_email")
    user = await login_user(db, email, list(attrs.get(cfg.groups_attribute) or []), cfg.role_mapping or {})
    return user, {"nameid": auth.get_nameid(), "assertion_id": aid, "email": email}, req.redirect_to
