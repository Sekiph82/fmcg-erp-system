"""Local simulator for the M51.S01.T006 image providers (synthetic, in-memory, never a real provider).

Contracts followed (docs checked 2026-11-26):
- OpenAI Images API  https://developers.openai.com/api/reference/resources/images
  POST /v1/images/generations  JSON {model, prompt, n, size, output_format, moderation}; header Authorization: Bearer <key>
  POST /v1/images/edits        multipart {model, prompt, size, image[]}
  200 {"created", "data": [{"b64_json", "revised_prompt"}], "output_format", "size", "usage": {...}}; 401 bad key; 429 + Retry-After;
  400 {"error": {"code": "moderation_blocked"}}; 5xx. GPT image models never return a url.
- Stability AI Stable Image Core (v2beta)  https://docs.stability.ai/api-reference
  POST /v2beta/stable-image/generate/core  multipart {prompt, ...}; Authorization: Bearer; Accept image/* -> PNG bytes with headers
  `finish-reason` (SUCCESS | CONTENT_FILTERED) and `seed`; 401, 402 credits, 403 moderation, 413, 422, 429.
Control: POST /_control {"faults": {"openai": ["429", "500", "moderation", "bad_image"], "stability": ["filtered", "403"]}, "revised": "text"};
GET /_control/calls; POST /_control/reset.
"""
from __future__ import annotations

import base64
import hashlib
import io

from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse, Response

OPENAI_KEY, STABILITY_KEY = "sim-image-key", "sim-stability-key"


def png(seed: str, size=(64, 64)) -> bytes:
    from PIL import Image
    h = hashlib.sha256(seed.encode()).digest()
    buf = io.BytesIO()
    Image.new("RGB", size, (h[0], h[1], h[2])).save(buf, "PNG")
    return buf.getvalue()


def create_app() -> FastAPI:
    app = FastAPI(title="POVU image provider simulator")
    st = {"calls": [], "faults": {"openai": [], "stability": []}, "revised": None}

    @app.post("/_control")
    async def control(request: Request):
        b = await request.json()
        for k, v in (b.get("faults") or {}).items():
            st["faults"][k] = list(v)
        if "revised" in b:
            st["revised"] = b["revised"]
        return {"ok": True}

    @app.post("/_control/reset")
    async def reset():
        st.update(calls=[], faults={"openai": [], "stability": []}, revised=None)
        return {"ok": True}

    @app.get("/_control/calls")
    async def calls():
        return st["calls"]

    def fault(api: str):
        q = st["faults"][api]
        if not q:
            return None
        f = q.pop(0)
        if f == "429":
            return JSONResponse({"error": {"code": "rate_limit_exceeded"}}, 429, headers={"Retry-After": "0"})
        if f == "500":
            return JSONResponse({"error": {"code": "server_error"}}, 500)
        if f == "moderation":
            return JSONResponse({"error": {"code": "moderation_blocked", "message": "Your request was rejected by the safety system."}}, 400)
        return f

    def ok_body(prompt: str, size: str, bad: bool = False):
        img = b"not an image" if bad else png(prompt)
        return {"created": 1764000000, "data": [{"b64_json": base64.b64encode(img).decode(), "revised_prompt": st["revised"]}],
                "output_format": "png", "size": size, "usage": {"input_tokens": 20, "output_tokens": 1056, "total_tokens": 1076}}

    @app.post("/v1/images/generations")
    async def generations(request: Request, authorization: str = Header("")):
        body = await request.json()
        st["calls"].append({"api": "openai", "op": "generations", "model": body.get("model"), "prompt": body.get("prompt"), "size": body.get("size"),
                            "keys": sorted(body)})
        if authorization != f"Bearer {OPENAI_KEY}":
            return JSONResponse({"error": {"code": "invalid_api_key"}}, 401)
        f = fault("openai")
        if isinstance(f, JSONResponse):
            return f
        if not body.get("prompt") or not body.get("model"):
            return JSONResponse({"error": {"code": "missing_required_parameter"}}, 400)
        return JSONResponse(ok_body(body["prompt"], body.get("size", "1024x1024"), f == "bad_image"), headers={"x-request-id": "req_sim_1"})

    @app.post("/v1/images/edits")
    async def edits(request: Request, authorization: str = Header("")):
        form = await request.form()
        files = [v for k, v in form.multi_items() if k == "image[]"]
        st["calls"].append({"api": "openai", "op": "edits", "model": form.get("model"), "prompt": form.get("prompt"), "images": len(files)})
        if authorization != f"Bearer {OPENAI_KEY}":
            return JSONResponse({"error": {"code": "invalid_api_key"}}, 401)
        f = fault("openai")
        if isinstance(f, JSONResponse):
            return f
        if not files or not form.get("prompt"):
            return JSONResponse({"error": {"code": "missing_required_parameter"}}, 400)
        return JSONResponse(ok_body("edit:" + form["prompt"], form.get("size", "1024x1024")), headers={"x-request-id": "req_sim_2"})

    @app.post("/v2beta/stable-image/generate/core")
    async def core(request: Request, authorization: str = Header(""), accept: str = Header("")):
        form = await request.form()
        st["calls"].append({"api": "stability", "prompt": form.get("prompt"), "aspect_ratio": form.get("aspect_ratio"), "accept": accept})
        if authorization != f"Bearer {STABILITY_KEY}":
            return JSONResponse({"errors": ["Unauthorized"]}, 401)
        f = fault("stability")
        if isinstance(f, JSONResponse):
            return f
        if f == "403":
            return JSONResponse({"errors": ["flagged by content moderation"]}, 403)
        if not form.get("prompt"):
            return JSONResponse({"errors": ["prompt is required"]}, 400)
        return Response(png(form["prompt"]), media_type="image/png",
                        headers={"finish-reason": "CONTENT_FILTERED" if f == "filtered" else "SUCCESS", "seed": "42"})

    return app
