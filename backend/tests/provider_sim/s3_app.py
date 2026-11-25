"""Minimal S3-compatible object store for tests (M45.S01.T020): path-style PUT/GET/HEAD/LIST of objects in memory.
Signatures are not verified (it stands in for a local MinIO). Run with `serve()` on a free localhost port."""
from __future__ import annotations

import socket
import threading
import time

from fastapi import FastAPI, Request, Response

STORE: dict[str, bytes] = {}
app = FastAPI()


@app.put("/{bucket}/{key:path}")
async def put(bucket: str, key: str, request: Request):
    STORE[f"{bucket}/{key}"] = await request.body()
    return Response(status_code=200, headers={"ETag": '"sim"'})


@app.get("/{bucket}/{key:path}")
async def get(bucket: str, key: str):
    data = STORE.get(f"{bucket}/{key}")
    return Response(status_code=404) if data is None else Response(content=data)


def serve() -> str:
    import uvicorn
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(50):
        if server.started:
            break
        time.sleep(0.1)
    return f"http://127.0.0.1:{port}"
