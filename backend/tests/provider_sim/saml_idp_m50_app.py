"""Local SAML 2.0 test identity provider (M50.S01.T010). Synthetic only: keys are generated in memory at start, nothing is
persisted and nothing talks to a real IdP.

Contract followed: OASIS SAML 2.0 Web Browser SSO (SP-initiated): HTTP-Redirect AuthnRequest (deflate + base64 in
SAMLRequest, RelayState echoed), HTTP-POST Response (base64) to the AssertionConsumerService with a signed Assertion
(enveloped XML-DSig, RSA-SHA256, exclusive c14n), SubjectConfirmation bearer with Recipient / NotOnOrAfter / InResponseTo,
Conditions NotBefore / NotOnOrAfter / AudienceRestriction, AuthnStatement, AttributeStatement.

Run for a manual login:  python -m uvicorn tests.provider_sim.saml_idp_m50_app:app --port 9440
 - GET /metadata   -> JSON with entity id, SSO URL and the signing certificate to paste into the ERP SAML configuration
 - GET /sso        -> receives the AuthnRequest, shows a page with the user to sign in as, then posts the signed response
 - POST /_control  -> {"email": ..., "groups": [...], "tamper": "wrong_key|expired|wrong_audience|wrong_recipient|none"}
Tests import TestIdP and build responses directly.
"""
from __future__ import annotations

import base64
import html
import re
import uuid
import zlib
from datetime import datetime, timedelta, timezone
from typing import Optional

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

NS = ('xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol" xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"')


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def make_key_and_cert(cn: str = "povu-demo-idp.test", days: int = 30) -> tuple[str, str]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])
    now = datetime.now(timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(now - timedelta(minutes=5))
            .not_valid_after(now + timedelta(days=days)).sign(key, hashes.SHA256()))
    return (key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode(),
            cert.public_bytes(serialization.Encoding.PEM).decode())


class TestIdP:
    __test__ = False                                         # not a pytest class

    def __init__(self, entity_id: str = "https://idp.povu-demo.test/metadata", sso_url: str = "http://localhost:9440/sso"):
        self.entity_id, self.sso_url = entity_id, sso_url
        self.key_pem, self.cert_pem = make_key_and_cert()
        self.other_key_pem, self.other_cert_pem = make_key_and_cert("rogue-idp.test")     # a second, untrusted signer

    def parse_authn_request(self, saml_request: str) -> dict:
        raw = zlib.decompress(base64.b64decode(saml_request), -15).decode()
        return {"id": re.search(r'\bID="([^"]+)"', raw).group(1),
                "acs": (re.search(r'AssertionConsumerServiceURL="([^"]+)"', raw) or [None, None])[1],
                "issuer": re.search(r"<saml:Issuer[^>]*>([^<]+)<", raw).group(1)}

    def response(self, *, acs: str, audience: str, in_response_to: Optional[str], email: str, groups: tuple = (),
                 tamper: str = "none", assertion_id: Optional[str] = None, issuer: Optional[str] = None,
                 not_before: Optional[datetime] = None, not_on_or_after: Optional[datetime] = None, sign: bool = True,
                 destination: Optional[str] = None, recipient: Optional[str] = None) -> str:
        from onelogin.saml2.utils import OneLogin_Saml2_Utils
        now = datetime.now(timezone.utc)
        nb = not_before or now - timedelta(minutes=1)
        na = not_on_or_after or now + timedelta(minutes=5)
        if tamper == "expired":
            nb, na = now - timedelta(hours=2), now - timedelta(hours=1)
        if tamper == "not_yet":
            nb, na = now + timedelta(hours=1), now + timedelta(hours=2)
        if tamper == "wrong_audience":
            audience = "https://some-other-app.example/metadata"
        if tamper == "wrong_recipient":
            recipient = "https://evil.example/acs"
        aid = assertion_id or "_" + uuid.uuid4().hex
        issuer = issuer or self.entity_id
        irt = f' InResponseTo="{in_response_to}"' if in_response_to else ""
        grp = "".join(f"<saml:AttributeValue>{html.escape(g)}</saml:AttributeValue>" for g in groups)
        assertion = (
            f'<saml:Assertion xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion" xmlns:xs="http://www.w3.org/2001/XMLSchema" '
            f'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ID="{aid}" Version="2.0" IssueInstant="{_iso(now)}">'
            f"<saml:Issuer>{issuer}</saml:Issuer>"
            f'<saml:Subject><saml:NameID Format="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress">{html.escape(email)}</saml:NameID>'
            f'<saml:SubjectConfirmation Method="urn:oasis:names:tc:SAML:2.0:cm:bearer">'
            f'<saml:SubjectConfirmationData NotOnOrAfter="{_iso(na)}" Recipient="{recipient or acs}"{irt}/></saml:SubjectConfirmation></saml:Subject>'
            f'<saml:Conditions NotBefore="{_iso(nb)}" NotOnOrAfter="{_iso(na)}"><saml:AudienceRestriction><saml:Audience>{audience}</saml:Audience>'
            f"</saml:AudienceRestriction></saml:Conditions>"
            f'<saml:AuthnStatement AuthnInstant="{_iso(now)}" SessionIndex="{aid}"><saml:AuthnContext><saml:AuthnContextClassRef>'
            f"urn:oasis:names:tc:SAML:2.0:ac:classes:PasswordProtectedTransport</saml:AuthnContextClassRef></saml:AuthnContext></saml:AuthnStatement>"
            f'<saml:AttributeStatement><saml:Attribute Name="email"><saml:AttributeValue>{html.escape(email)}</saml:AttributeValue></saml:Attribute>'
            f'<saml:Attribute Name="groups">{grp}</saml:Attribute></saml:AttributeStatement></saml:Assertion>')
        if sign:
            key, cert = (self.other_key_pem, self.other_cert_pem) if tamper == "wrong_key" else (self.key_pem, self.cert_pem)
            assertion = OneLogin_Saml2_Utils.add_sign(assertion, key, cert).decode()
            assertion = re.sub(r"^<\?xml[^>]*\?>\s*", "", assertion)
        xml = (f'<samlp:Response {NS} ID="_{uuid.uuid4().hex}" Version="2.0" IssueInstant="{_iso(now)}" '
               f'Destination="{destination or acs}"{irt}><saml:Issuer>{issuer}</saml:Issuer>'
               f'<samlp:Status><samlp:StatusCode Value="urn:oasis:names:tc:SAML:2.0:status:Success"/></samlp:Status>{assertion}</samlp:Response>')
        if tamper == "modified_after_signing":                       # change the identity inside the signed assertion
            xml = xml.replace(f">{html.escape(email)}<", ">ceo@povu-demo.test<", 1)
        return base64.b64encode(xml.encode()).decode()


def build_app(idp: Optional[TestIdP] = None) -> FastAPI:
    idp = idp or TestIdP()
    app = FastAPI(title="SAML test IdP (synthetic)")
    state = {"email": "amani.wekesa@povu-demo.test", "groups": ["erp-sales"], "tamper": "none"}
    app.state.idp, app.state.control = idp, state

    @app.get("/metadata")
    async def metadata():
        return {"entity_id": idp.entity_id, "sso_url": idp.sso_url, "x509_cert": idp.cert_pem}

    @app.post("/_control")
    async def control(request: Request):
        state.update(await request.json())
        return state

    @app.get("/sso", response_class=HTMLResponse)
    async def sso(SAMLRequest: str, RelayState: str = "", audience: str = ""):
        req = idp.parse_authn_request(SAMLRequest)
        acs = req["acs"] or ""
        aud = audience or req["issuer"]
        resp = idp.response(acs=acs, audience=aud, in_response_to=req["id"], email=state["email"], groups=tuple(state["groups"]),
                            tamper=state["tamper"])
        return HTMLResponse(
            f'<html><body onload="document.forms[0].submit()"><p>Signing in {html.escape(state["email"])} (test IdP)...</p>'
            f'<form method="post" action="{html.escape(acs)}"><input type="hidden" name="SAMLResponse" value="{resp}"/>'
            f'<input type="hidden" name="RelayState" value="{html.escape(RelayState)}"/><noscript><button>Continue</button></noscript>'
            f"</form></body></html>")

    return app


app = build_app()
