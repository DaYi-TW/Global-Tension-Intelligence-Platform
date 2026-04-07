from fastapi import APIRouter
from app.api.routes import health, dashboard, tension, map

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(dashboard.router, prefix="/api", tags=["dashboard"])
api_router.include_router(tension.router, prefix="/api", tags=["tension"])
api_router.include_router(map.router, prefix="/api", tags=["map"])
