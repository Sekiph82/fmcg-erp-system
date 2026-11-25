"""Local provider simulator (M43.S00.T004): documented public OAuth / provider HTTP contracts served locally.

It is a test mechanism, not an integration: the ERP's real adapter code talks to it over HTTP exactly as it would
to Google or Microsoft. In-process tests use ``httpx.ASGITransport(app=create_app())`` with
``app.core.provider_http.set_test_transport``; browser E2E runs it as a server:

    python -m tests.provider_sim --port 8765        (from backend/)

and points the ERP at it with ``sim_settings("http://127.0.0.1:8765")``. Every identity it issues is synthetic
(@povu-demo.test). M43.S01 adds Gmail, Graph mail/calendar, Google Calendar and voice contracts here.
"""
from tests.provider_sim.app import create_app, sim_settings  # noqa: F401
