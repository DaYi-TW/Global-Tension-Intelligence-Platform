"""
Events API Routes
GET /api/events           - 事件列表（可按國家/區域/類型篩選）
GET /api/events/{event_id} - 單一事件詳情
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.core.cache import cache_get_or_compute
from app.core.config import get_settings
from app.services.query_service import QueryService

router = APIRouter()
settings = get_settings()

TTL_EVENTS = 600   # 10 分鐘


@router.get("/events")
async def get_events(
    country:        Optional[str] = Query(None, description="ISO alpha-3 國家代碼，如 USA"),
    region:         Optional[str] = Query(None, description="區域代碼，如 middle_east"),
    event_type:     Optional[str] = Query(None, description="事件類型，如 military_clash"),
    risk_or_relief: Optional[str] = Query(None, pattern="^(risk|relief)$"),
    date:           Optional[str] = Query(None, description="YYYY-MM-DD，篩選特定日期"),
    limit:          int           = Query(20, ge=1, le=100),
    offset:         int           = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """事件列表，支援依國家/區域/類型篩選，含評分分解與新聞來源"""
    sv = settings.scoring_version
    cache_key = f"events:list:{country or ''}:{region or ''}:{event_type or ''}:{risk_or_relief or ''}:{date or 'all'}:{limit}:{offset}:{sv}"

    async def compute():
        svc = QueryService(db, scoring_version=sv)
        return await svc.get_events(
            country=country,
            region=region,
            event_type=event_type,
            risk_or_relief=risk_or_relief,
            date=date,
            limit=limit,
            offset=offset,
        )

    return await cache_get_or_compute(cache_key, compute, TTL_EVENTS)


@router.get("/events/{event_id}")
async def get_event_detail(
    event_id: str,
    db: AsyncSession = Depends(get_db),
):
    """單一事件完整詳情（含評分分解、新聞來源、涉及國家）"""
    sv = settings.scoring_version
    cache_key = f"events:detail:{event_id}:{sv}"

    async def compute():
        svc = QueryService(db, scoring_version=sv)
        return await svc.get_event_detail(event_id)

    return await cache_get_or_compute(cache_key, compute, TTL_EVENTS)
