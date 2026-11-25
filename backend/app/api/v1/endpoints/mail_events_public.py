"""Public signed mail-event webhooks (M44.S01.T011). Prefix /api/v1/public/mail-events; allow-listed in PUBLIC_ROUTES."""
from app.api.v1.endpoints.deliverability import public_router as router  # noqa: F401
