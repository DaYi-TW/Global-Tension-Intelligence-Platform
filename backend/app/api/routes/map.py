"""
Map Heat API Routes
GET /api/map/heat
GET /api/map/heat/range
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.cache import cache_get_or_compute
from app.core.config import get_settings
from app.services.query_service import QueryService

router = APIRouter()
settings = get_settings()

TTL_MAP = 900    # 15 分鐘
TTL_RANGE = 900


@router.get("/map/heat")
async def get_map_heat(
    date:      str | None = Query(None, description="YYYY-MM-DD"),
    dimension: str        = Query("overall", pattern="^(overall|military|political|economic|social|cyber)$"),
    db: AsyncSession = Depends(get_db),
):
    """地圖熱點資料（單日，所有國家分數）"""
    from datetime import datetime, timezone
    sv = settings.scoring_version
    target_date_str = date or str(datetime.now(timezone.utc).date())
    cache_key = f"map:heat:{target_date_str}:{dimension}:{sv}"

    async def compute():
        svc = QueryService(db, scoring_version=sv)
        target = None
        if date:
            from datetime import date as date_type
            target = date_type.fromisoformat(date)
        return await svc.get_map_heat(target, dimension=dimension)

    return await cache_get_or_compute(cache_key, compute, TTL_MAP)


@router.get("/map/heat/range")
async def get_map_heat_range(
    from_date: str = Query(..., alias="from", description="YYYY-MM-DD"),
    to_date:   str = Query(..., alias="to",   description="YYYY-MM-DD"),
    dimension: str = Query("overall", pattern="^(overall|military|political|economic|social|cyber)$"),
    db: AsyncSession = Depends(get_db),
):
    """批次取得日期範圍的地圖熱點資料（時間軸播放用）"""
    from datetime import date as date_type, timedelta

    # 最多 90 天
    d_from = date_type.fromisoformat(from_date)
    d_to   = date_type.fromisoformat(to_date)
    if (d_to - d_from).days > 90:
        d_from = d_to - timedelta(days=90)

    async def compute():
        svc = QueryService(db, scoring_version=settings.scoring_version)
        return await svc.get_map_heat_range(d_from, d_to, dimension=dimension)

    cache_key = f"map:heat:range:{d_from}:{d_to}:{dimension}:{settings.scoring_version}"
    return await cache_get_or_compute(cache_key, compute, TTL_RANGE)
