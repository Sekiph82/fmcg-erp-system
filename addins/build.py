#!/usr/bin/env python3
"""Build the deployable Gmail add-on and Outlook add-in files for one ERP (M50.S01.T011). Python 3 standard library only.

    python addins/build.py --app-origin https://erp.example.com [--api-origin https://api.erp.example.com] --out dist/addins

Writes   <out>/outlook/manifest.xml          Outlook XML manifest (MailApp, read surface)
         <out>/gmail/appsscript.json         Apps Script manifest
         <out>/gmail/Code.gs                 Apps Script source with the origins filled in
         <out>/build-manifest.json           origins, ids and SHA-256 of every file

and refuses (exit 1, nothing written) when a check fails: https only (http://localhost only with --allow-local), one bare
origin without path/query/wildcard, no template placeholder left, Outlook permission limited to ReadItem, every manifest URL on
the ERP origin, Gmail OAuth scopes within the reviewed allow-list, the fetch allow-list equal to the API origin, no token,
code or verifier in any URL of the source. No marketplace listing and no account is involved: sideloading / test deployment
is the owner's activation step (README).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
PLACEHOLDER = "https://erp.povu.example"
GMAIL_SCOPES = {
    "https://www.googleapis.com/auth/gmail.addons.execute",
    "https://www.googleapis.com/auth/gmail.addons.current.message.readonly",
    "https://www.googleapis.com/auth/gmail.addons.current.action.compose",
    "https://www.googleapis.com/auth/script.external_request",
    "https://www.googleapis.com/auth/script.storage",
}
OUTLOOK_PERMISSIONS = {"ReadItem"}
URL_IN_SECRET = re.compile(r"[?&](?:access_token|refresh_token|token|code_verifier|verifier|code)=", re.I)


class BuildError(Exception):
    pass


def origin_of(value: str, allow_local: bool, label: str) -> str:
    u = urlsplit(value or "")
    local = u.hostname in ("localhost", "127.0.0.1")
    if u.scheme != "https" and not (allow_local and local and u.scheme == "http"):
        raise BuildError(f"{label} must be an https origin (got {value!r}).")
    if not u.hostname or u.path not in ("", "/") or u.query or u.fragment or u.username or "*" in value:
        raise BuildError(f"{label} must be a bare origin like https://erp.example.com (no path, query, credentials or wildcard).")
    if u.hostname.endswith(".example") and "povu.example" in u.hostname:
        raise BuildError(f"{label} is still the template placeholder.")
    return f"{u.scheme}://{u.netloc}"


def build_outlook(app: str, api: str, version: str) -> tuple[str, dict]:
    src = (HERE / "outlook" / "manifest.xml").read_text(encoding="utf-8")
    app_id = str(uuid.uuid5(uuid.NAMESPACE_URL, "povu-crm-outlook:" + app))
    src = re.sub(r"<Id>[0-9a-fA-F-]{36}</Id>", f"<Id>{app_id}</Id>", src, count=1)
    src = re.sub(r"<Version>[^<]*</Version>", f"<Version>{version}</Version>", src, count=1)
    out = src.replace(PLACEHOLDER, app)
    if api != app:
        out = out.replace(f"<AppDomains><AppDomain>{app}</AppDomain></AppDomains>",
                          f"<AppDomains><AppDomain>{app}</AppDomain><AppDomain>{api}</AppDomain></AppDomains>")
    validate_outlook(out, {app, api})
    return out, {"id": app_id, "version": version}


def validate_outlook(xml: str, origins: set[str]) -> None:
    if PLACEHOLDER in xml:
        raise BuildError("Outlook manifest still contains the template origin.")
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as e:
        raise BuildError(f"Outlook manifest is not well-formed XML: {e}")
    ns = {"o": "http://schemas.microsoft.com/office/appforoffice/1.1"}
    if root.tag != "{http://schemas.microsoft.com/office/appforoffice/1.1}OfficeApp":
        raise BuildError("Outlook manifest root must be OfficeApp.")
    for tag in ("Id", "Version", "ProviderName", "DisplayName", "Hosts", "Permissions", "FormSettings"):
        if root.find(f"o:{tag}", ns) is None:
            raise BuildError(f"Outlook manifest is missing <{tag}>.")
    uuid.UUID(root.find("o:Id", ns).text)
    perm = root.find("o:Permissions", ns).text
    if perm not in OUTLOOK_PERMISSIONS:
        raise BuildError(f"Outlook permission {perm!r} is broader than the reviewed set {sorted(OUTLOOK_PERMISSIONS)}.")
    for d in root.iter("{http://schemas.microsoft.com/office/appforoffice/1.1}AppDomain"):
        if d.text not in origins:
            raise BuildError(f"AppDomain {d.text!r} is not one of the ERP origins.")
    urls = [el.get("DefaultValue") for el in root.iter() if (el.get("DefaultValue") or "").startswith(("http://", "https://"))]
    urls += [el.text for el in root.iter() if (el.text or "").startswith(("http://", "https://")) and el.tag.endswith("AppDomain") is False]
    for u in urls:
        o = f"{urlsplit(u).scheme}://{urlsplit(u).netloc}"
        if o not in origins:
            raise BuildError(f"Outlook manifest URL {u!r} is not on the ERP origin.")
    if not any("SourceLocation" in el.tag for el in root.iter()):
        raise BuildError("Outlook manifest has no SourceLocation.")
    if URL_IN_SECRET.search(xml):
        raise BuildError("Outlook manifest URL carries a token/code parameter.")


def build_gmail(app: str, api: str) -> tuple[str, str]:
    code = (HERE / "gmail" / "Code.gs").read_text(encoding="utf-8")
    code, n1 = re.subn(r'var APP_ORIGIN = "[^"]*";', f'var APP_ORIGIN = "{app}";', code)
    code, n2 = re.subn(r'var API_ORIGIN = "[^"]*";', f'var API_ORIGIN = "{api}";', code)
    if (n1, n2) != (1, 1):
        raise BuildError("Code.gs must declare APP_ORIGIN and API_ORIGIN exactly once each.")
    manifest = json.loads((HERE / "gmail" / "appsscript.json").read_text(encoding="utf-8"))
    manifest["urlFetchWhitelist"] = [api + "/"]
    manifest["addOns"]["common"]["logoUrl"] = app + "/icons/icon-192.png"
    text = json.dumps(manifest, indent=2) + "\n"
    validate_gmail(manifest, code, app, api)
    return text, code


def validate_gmail(manifest: dict, code: str, app: str, api: str) -> None:
    extra = set(manifest.get("oauthScopes", [])) - GMAIL_SCOPES
    if extra:
        raise BuildError(f"Gmail scopes outside the reviewed list: {sorted(extra)}")
    if manifest.get("urlFetchWhitelist") != [api + "/"]:
        raise BuildError("urlFetchWhitelist must be exactly the API origin.")
    if PLACEHOLDER in json.dumps(manifest) or PLACEHOLDER in code:
        raise BuildError("Gmail files still contain the template origin.")
    if URL_IN_SECRET.search(code):
        raise BuildError("Code.gs builds a URL with a token, code or verifier parameter.")
    for fn in ("onGmailMessage", "onHomepage"):
        if f"function {fn}" not in code:
            raise BuildError(f"Code.gs lacks {fn}.")
        if fn not in json.dumps(manifest["addOns"]):
            raise BuildError(f"appsscript.json does not register {fn}.")
    if "eval(" in code or "new Function(" in code:
        raise BuildError("Code.gs uses dynamic code execution.")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--app-origin", required=True, help="the ERP web app origin, e.g. https://erp.example.com")
    ap.add_argument("--api-origin", help="the ERP API origin if different from the app origin")
    ap.add_argument("--out", required=True, help="output directory (created; existing build files are replaced)")
    ap.add_argument("--version", default="1.1.0.0", help="Outlook manifest version (a.b.c.d)")
    ap.add_argument("--allow-local", action="store_true", help="allow http://localhost origins (local harness builds only)")
    a = ap.parse_args(argv)
    try:
        if not re.fullmatch(r"\d+\.\d+\.\d+\.\d+", a.version):
            raise BuildError("--version must look like 1.1.0.0")
        app = origin_of(a.app_origin, a.allow_local, "--app-origin")
        api = origin_of(a.api_origin or a.app_origin, a.allow_local, "--api-origin")
        outlook, meta = build_outlook(app, api, a.version)
        gmail_json, gmail_code = build_gmail(app, api)
    except (BuildError, OSError, ValueError, KeyError) as e:
        print(f"BUILD FAILED: {e}", file=sys.stderr)
        return 1
    out = Path(a.out)
    files = {"outlook/manifest.xml": outlook, "gmail/appsscript.json": gmail_json, "gmail/Code.gs": gmail_code}
    for rel, text in files.items():
        (out / rel).parent.mkdir(parents=True, exist_ok=True)
        (out / rel).write_text(text, encoding="utf-8", newline="\n")
    manifest = {"app_origin": app, "api_origin": api, "outlook": meta, "allow_local": bool(a.allow_local),
                "files": {rel: hashlib.sha256(text.encode()).hexdigest() for rel, text in files.items()}}
    (out / "build-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"built {len(files)} files in {out} for {app} (Outlook Id {meta['id']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
