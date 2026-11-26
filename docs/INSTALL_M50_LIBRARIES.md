# SAML, Parquet and OCR libraries (M50.S01.T010)

All three are plain `pip` wheels. Nothing is installed with `apt`, no system binary (such as Tesseract) is needed, no account
or licence key is needed, and nothing is downloaded when the app runs. They are pinned in `backend/requirements.txt`.

| Capability | Package (exact pin) | Licence | Notes |
|---|---|---|---|
| SAML 2.0 sign-in | `python3-saml==1.16.0`, `xmlsec==1.3.18`, `lxml==6.1.0`, `isodate==0.7.2` | MIT, MIT, BSD-3-Clause, BSD-3-Clause | xmlsec wheels bundle libxmlsec1 (Windows and manylinux), so no `libxmlsec1-dev` is needed in the image. |
| Typed Parquet | `pyarrow==26.0.1` | Apache-2.0 | Read and write; zstd compression. |
| Business-card OCR | `rapidocr==3.10.0`, `onnxruntime==1.20.1`, `opencv-python-headless==5.1.0.95` | Apache-2.0, MIT, Apache-2.0 | PP-OCR ONNX models (Apache-2.0) ship inside the `rapidocr` wheel. CPU only, runs in a worker thread. |

Licence review: every package above is permissive (MIT, BSD or Apache-2.0); none is copyleft. `python3-saml` is the
OneLogin/SAML-Toolkits project (maintained; 1.16.0). The alternative `pytesseract` was not chosen because it needs the
Tesseract system binary (apt on Linux, a separate installer on Windows).

## Local install (Windows or Linux)

```
cd backend
pip install -r requirements.txt
python -c "import xmlsec, pyarrow, rapidocr, onnxruntime; from onelogin.saml2.auth import OneLogin_Saml2_Auth; print('ok')"
```

Verified on Windows 11 / Python 3.12 and in the `python:3.12-slim` Linux image with these exact pins (import, an XML-DSig
sign-and-verify round trip, a Parquet round trip and OCR engine start).

## Docker

`backend/Dockerfile` and `backend/Dockerfile.prod` install `requirements.txt` as before and then run an import check, so a
build fails at once if one of the wheels does not load on that platform. No extra `apt-get` packages are required.

## Smoke tests

```
# SAML: signed assertion accepted; wrong signature, replay, wrong audience/recipient, expired refused (local test IdP, keys made in the test)
python -m pytest tests/test_m50_s01_t010_saml.py tests/test_m50_s01_t010_parquet_ocr.py   # add M50_DB=1 and a disposable DATABASE_URL for the database parts
```

Manual: run the test IdP (`python -m uvicorn tests.provider_sim.saml_idp_m50_app:app --port 9440`), open
`http://localhost:9440/metadata`, paste its certificate into **Security -> Single sign-on -> SAML 2.0**
(entity id and SSO URL come from the same page), activate, then use the SAML button on the login page.

## SBOM / dependency checks

```
pip install pip-licenses cyclonedx-bom      # tools, not runtime dependencies
pip-licenses --packages python3-saml xmlsec lxml isodate pyarrow rapidocr onnxruntime opencv-python-headless
cyclonedx-py environment -o sbom.json
pip check
```

## Rollback

Uninstall by removing the pinned block from `requirements.txt` and rebuilding: the SAML status endpoint reports
`NOT_AVAILABLE`, Parquet jobs fail with an explicit error, and the card scanner reports that recognition is unavailable
(typing or pasting the card text keeps working). Nothing else depends on these packages.

## Operational notes

- SAML needs the coordinator-applied allow-list entries and the CSRF exemption for `POST /api/v1/sso/saml/acs` (the IdP posts
  cross-site; the request is authenticated by the assertion signature, the request id and a browser-bound cookie).
- Behind HTTPS set `AUTH_COOKIE_SECURE=true`: the SAML request cookie is then `SameSite=None; Secure`, which cross-site POST needs.
- A card picture is never stored; only recognised text and suggested fields are kept as a draft for 7 days.
