"""Run the local provider simulator for browser E2E: python -m tests.provider_sim --port 8765 (loopback only)."""
import argparse

import uvicorn

from tests.provider_sim.app import create_app

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    uvicorn.run(create_app(), host="127.0.0.1", port=ap.parse_args().port)
