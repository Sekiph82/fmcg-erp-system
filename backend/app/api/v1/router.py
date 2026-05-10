from fastapi import APIRouter

from app.core.config import settings
from app.core.module_registry import register_endpoint_routes, register_module_routes


api_router = APIRouter()

register_endpoint_routes(api_router, environment=settings.ENVIRONMENT)
register_module_routes(api_router, environment=settings.ENVIRONMENT)
