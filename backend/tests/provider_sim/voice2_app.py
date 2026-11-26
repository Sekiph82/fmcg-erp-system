"""Local simulator for the M49 voice contracts: Twilio Programmable Voice REST + OpenAI audio transcriptions.

Synthetic only; never a real carrier or provider. Contracts followed (public docs, 2026-11-26):
- Twilio REST 2010-04-01: POST /2010-04-01/Accounts/{sid}/Calls.json (HTTP Basic sid:token; To, From, Url|Twiml required;
  201 {"sid": "CA..", "status": "queued", ..}), POST .../Calls/{sid}.json (Twiml/Url/Status; 400 code 21220 when the call
  is not in progress), GET .../Calls/{sid}.json. Errors: {"code", "message", "more_info", "status"}.
- OpenAI POST /v1/audio/transcriptions (multipart; Bearer): whisper-1 -> verbose_json (language name, segments with
  avg_logprob/no_speech_prob, no speakers); gpt-4o-transcribe-diarize -> diarized_json (segments with speaker A/B, no
  language field). Error object {"error": {"message", "type", "param", "code"}}.
Fault injection via POST /_control: {"twilio": [429, 500], "openai": [429, 503, 401], "twilio_timeout": 1, "call_status":
{sid: "completed"}}. Audio fixtures are the bytes b"POVU-SYN-AUDIO|lang=<en|sw|tr>|".
Run standalone for the browser walkthrough: python -m tests.provider_sim.voice2_app --port 8767 (loopback only).
"""
from __future__ import annotations

import base64
import re
import secrets
from typing import Optional

from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse, Response

ACCOUNT_SID = "ACsimulated000000000000000000000a"
AUTH_TOKEN = "sim-twilio-token"
OPENAI_KEY = "sim-openai-key"
NUMBER = "+254700000001"

TEXTS = {
    "en": ["Hello, this is POVU sales. You can email me at agent@example.com.",
           "The price of POVU AllClean 1 L is too high for our shop. My number is +254 712 345 678.",
           "I will send you a quote by Friday."],
    "sw": ["Habari, hapa ni mauzo ya POVU.", "Bei ya POVU AllClean lita 1 ni ghali sana kwa duka letu.", "Nitakutumia nukuu kesho."],
    "tr": ["Merhaba, burasi POVU satis.", "POVU AllClean 1 L fiyati dukkanimiz icin cok yuksek.", "Teklifi Cuma gunune kadar gonderecegim."],
}
NAMES = {"en": "english", "sw": "swahili", "tr": "turkish"}


def sim_settings(base: str) -> dict:
    base = base.rstrip("/")
    return {
        "VOICE_PROVIDER": "twilio", "VOICE_TWILIO_ACCOUNT_SID": ACCOUNT_SID, "VOICE_TWILIO_AUTH_TOKEN": AUTH_TOKEN,
        "VOICE_TWILIO_PHONE_NUMBER": NUMBER, "VOICE_TWILIO_BASE_URL": f"{base}/twilio",
        "PUBLIC_API_URL": "https://erp.povu-demo.test",
        "TRANSCRIPTION_OPENAI_API_KEY": OPENAI_KEY, "TRANSCRIPTION_OPENAI_BASE_URL": f"{base}/openai/v1",
    }


def create_app() -> FastAPI:
    app = FastAPI(title="POVU voice simulator (synthetic, local only)")
    st: dict = {}

    def reset() -> None:
        st.clear()
        st.update(calls={}, updates=[], created=[], faults={"twilio": [], "openai": []}, twilio_timeout=0, openai_seen=[])
    reset()

    def twerr(status: int, code: int, message: str) -> JSONResponse:
        return JSONResponse({"code": code, "message": message, "more_info": f"https://www.twilio.com/docs/errors/{code}",
                             "status": status}, status)

    def twauth(authorization: Optional[str]) -> bool:
        try:
            return base64.b64decode((authorization or "").split(" ", 1)[1]).decode() == f"{ACCOUNT_SID}:{AUTH_TOKEN}"
        except Exception:
            return False

    def tw_fault() -> Optional[JSONResponse]:
        q = st["faults"]["twilio"]
        if q:
            f = q.pop(0)
            return JSONResponse({"code": 20429 if f == 429 else 20500, "message": "simulated", "status": f}, f,
                                headers={"Retry-After": "0"} if f == 429 else {})
        return None

    @app.post("/_control")
    async def control(request: Request):
        b = await request.json()
        if b.get("reset"):
            reset()
        for k in ("twilio", "openai"):
            st["faults"][k] += b.get(k, [])
        st["twilio_timeout"] += b.get("twilio_timeout", 0)
        for sid, status in (b.get("call_status") or {}).items():
            if sid in st["calls"]:
                st["calls"][sid]["status"] = status
        return {"ok": True}

    # ── Twilio ───────────────────────────────────────────────────────────────
    base = f"/twilio/2010-04-01/Accounts/{ACCOUNT_SID}"

    @app.post(base + "/Calls.json")
    async def tw_create(request: Request, authorization: Optional[str] = Header(None)):
        if not twauth(authorization):
            return twerr(401, 20003, "Authenticate")
        if f := tw_fault():
            return f
        form = await request.form()
        to, frm = str(form.get("To", "")), str(form.get("From", ""))
        if not re.match(r"^\+[1-9]\d{6,14}$", to):
            return twerr(400, 21211, f"The 'To' number {to} is not a valid phone number.")
        if frm != NUMBER:
            return twerr(400, 21606, f"The From phone number {frm} is not a valid, SMS-capable Twilio phone number.")
        if not (form.get("Url") or form.get("Twiml") or form.get("ApplicationSid")):
            return twerr(400, 21205, "Url parameter is required")
        sid = "CA" + secrets.token_hex(16)
        call = {"sid": sid, "status": "queued", "to": to, "from": frm, "api_version": "2010-04-01",
                "uri": f"{base}/Calls/{sid}.json", "form": {k: form.getlist(k) for k in form.keys()}}
        st["calls"][sid] = call
        st["created"].append(call)
        if st["twilio_timeout"] > 0:             # the call IS created but the client never gets the answer
            st["twilio_timeout"] -= 1
            import asyncio
            await asyncio.sleep(2)
        return JSONResponse({k: v for k, v in call.items() if k != "form"}, 201)

    @app.post(base + "/Calls/{sid}.json")
    async def tw_update(sid: str, request: Request, authorization: Optional[str] = Header(None)):
        if not twauth(authorization):
            return twerr(401, 20003, "Authenticate")
        if f := tw_fault():
            return f
        call = st["calls"].get(sid)
        if call is None:
            return twerr(404, 20404, f"The requested resource {base}/Calls/{sid}.json was not found")
        form = await request.form()
        if call["status"] in ("completed", "busy", "failed", "no-answer", "canceled"):
            return twerr(400, 21220, "Call is not in-progress. Cannot redirect.")
        st["updates"].append({"sid": sid, **{k: str(v) for k, v in form.items()}})
        if form.get("Status"):
            call["status"] = str(form["Status"])
        return {k: v for k, v in call.items() if k != "form"}

    @app.get(base + "/Calls/{sid}.json")
    async def tw_fetch(sid: str, authorization: Optional[str] = Header(None)):
        if not twauth(authorization):
            return twerr(401, 20003, "Authenticate")
        call = st["calls"].get(sid)
        if call is None:
            return twerr(404, 20404, f"The requested resource {base}/Calls/{sid}.json was not found")
        return {k: v for k, v in call.items() if k != "form"}

    # ── recordings (https URL in the ERP, loopback transport in tests) ───────
    @app.get("/recordings/{name}")
    async def recording(name: str):
        lang = name.rsplit(".", 1)[0].rsplit("-", 1)[-1]
        return Response(f"POVU-SYN-AUDIO|lang={lang}|".encode(), media_type="audio/wav")

    # ── OpenAI audio transcriptions ──────────────────────────────────────────
    def oaerr(status: int, message: str, param: Optional[str] = None, headers: Optional[dict] = None) -> JSONResponse:
        return JSONResponse({"error": {"message": message, "type": "invalid_request_error", "param": param, "code": None}},
                            status, headers=headers or {})

    @app.post("/openai/v1/audio/transcriptions")
    async def transcriptions(request: Request, authorization: Optional[str] = Header(None)):
        q = st["faults"]["openai"]
        if q:
            f = q.pop(0)
            return oaerr(f, "simulated fault", headers={"Retry-After": "0"} if f == 429 else {})
        if authorization != f"Bearer {OPENAI_KEY}":
            return oaerr(401, "Incorrect API key provided.")
        form = await request.form()
        upload = form.get("file")
        model, fmt, lang = str(form.get("model", "")), str(form.get("response_format", "json")), form.get("language")
        if upload is None or not hasattr(upload, "read"):
            return oaerr(400, "you must provide a file", "file")
        ext = (upload.filename or "").rsplit(".", 1)[-1].lower()
        if ext not in ("flac", "mp3", "mp4", "mpeg", "mpga", "m4a", "ogg", "wav", "webm"):
            return oaerr(400, "Unrecognized file format.", "file")
        if model not in ("whisper-1", "gpt-4o-transcribe-diarize"):
            return oaerr(400, f"Invalid model {model}", "model")
        if fmt == "diarized_json" and model != "gpt-4o-transcribe-diarize" or fmt == "verbose_json" and model != "whisper-1":
            return oaerr(400, f"response_format {fmt} is not compatible with model {model}", "response_format")
        if model == "gpt-4o-transcribe-diarize" and not form.get("chunking_strategy"):
            return oaerr(400, "chunking_strategy is required for diarization", "chunking_strategy")
        if lang is not None and str(lang) not in ("en", "sw", "tr", "fr", "de"):
            return oaerr(400, f"Invalid language '{lang}'", "language")
        audio = await upload.read()
        m = re.search(rb"lang=(\w\w)", audio)
        used = str(lang) if lang else (m.group(1).decode() if m else "en")
        texts = TEXTS.get(used, TEXTS["en"])
        st["openai_seen"].append({"model": model, "format": fmt, "language": str(lang) if lang else None})
        spans = [(0.0, 3.2), (3.4, 7.9), (8.1, 12.0)]
        if fmt == "diarized_json":
            segs = [{"type": "transcript.text.segment", "id": f"seg_{i}", "start": a, "end": b, "text": t, "speaker": "AB"[i % 2 if i < 2 else 0]}
                    for i, ((a, b), t) in enumerate(zip(spans, texts))]
            return {"task": "transcribe", "duration": 12.0, "text": " ".join(texts), "segments": segs}
        segs = [{"id": i, "seek": 0, "start": a, "end": b, "text": t, "tokens": [], "temperature": 0.0,
                 "avg_logprob": -0.25,
                 "compression_ratio": 1.2, "no_speech_prob": 0.02} for i, ((a, b), t) in enumerate(zip(spans, texts))]
        return {"task": "transcribe", "language": NAMES[used] if used in NAMES else used, "duration": 12.0,
                "text": " ".join(texts), "segments": segs}

    app.state.sim = st
    return app


if __name__ == "__main__":      # browser walkthrough: python -m tests.provider_sim.voice2_app --port 8767 (loopback only)
    import argparse

    import uvicorn
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8767)
    uvicorn.run(create_app(), host="127.0.0.1", port=ap.parse_args().port)
