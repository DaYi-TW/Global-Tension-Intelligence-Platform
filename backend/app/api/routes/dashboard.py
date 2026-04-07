"""
Dashboard API Routes
GET /api/dashboard/overview
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.cache import cache_get_or_compute
from app.core.config import get_settings
from app.services.query_service import QueryService

router = APIRouter()
settings = get_settings()

TTL_DASHBOARD = 900  # 15 分鐘


@router.get("/dashboard/overview")
async def get_dashboard_overview(
    date: str | None = Query(None, description="YYYY-MM-DD，不填則使用今日"),
    db: AsyncSession = Depends(get_db),
):
    """首頁總覽：全球緊張度、7 日趨勢、區域排行、最快上升國家"""
    cache_key = f"dashboard:overview:{date or 'today'}"

    async def compute():
        svc = QueryService(db, scoring_version=settings.scoring_version)
        target = None
        if date:
            from datetime import date as date_type
            target = date_type.fromisoformat(date)
        return await svc.get_dashboard_overview(target)

    return await cache_get_or_compute(cache_key, compute, TTL_DASHBOARD)
