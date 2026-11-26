"""Run the local provider simulator for browser E2E: python -m tests.provider_sim --port 8765 (loopback only)."""
import argparse

import uvicorn

from tests.provider_sim.app import create_app

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    app = create_app()
    from tests.provider_sim.warehouse_app import create_warehouse_app
    app.mount("/wh", create_warehouse_app())        # M48 Snowflake / BigQuery (sf_config(base) / bq_config(base))
    uvicorn.run(app, host="127.0.0.1", port=ap.parse_args().port)
