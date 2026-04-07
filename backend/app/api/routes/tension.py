"""
Tension API Routes
GET /api/tension/global/trend
GET /api/tension/regions
GET /api/tension/countries
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.cache import cache_get_or_compute
from app.core.config import get_settings
from app.services.query_service import QueryService

router = APIRouter()
settings = get_settings()

TTL_TENSION = 3600   # 1 小時
TTL_COUNTRIES = 3600


@router.get("/tension/global/trend")
async def get_global_trend(
    range: str = Query("30d", pattern="^(7d|30d|90d|1y)$"),
    db: AsyncSession = Depends(get_db),
):
    """全球緊張度時序資料"""
    cache_key = f"tension:global:trend:{range}"

    async def compute():
        svc = QueryService(db, scoring_version=settings.scoring_version)
        return await svc.get_global_trend(range)

    return await cache_get_or_compute(cache_key, compute, TTL_TENSION)


@router.get("/tension/regions")
async def get_regions(
    date: str | None = Query(None, description="YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
):
    """區域緊張度排行"""
    from datetime import datetime, timezone
    from app.core.config import get_settings
    sv = settings.scoring_version
    target_date_str = date or str(datetime.now(timezone.utc).date())
    cache_key = f"tension:regions:{target_date_str}:{sv}"

    async def compute():
        svc = QueryService(db, scoring_version=sv)
        target = None
        if date:
            from datetime import date as date_type
            target = date_type.fromisoformat(date)
        return await svc.get_regions(target)

    return await cache_get_or_compute(cache_key, compute, TTL_TENSION)


@router.get("/tension/countries")
async def get_countries(
    date:   str | None = Query(None, description="YYYY-MM-DD"),
    region: str | None = Query(None, description="區域代碼，如 middle_east"),
    limit:  int        = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """國家緊張度排行（可按區域過濾）"""
    from datetime import datetime, timezone
    sv = settings.scoring_version
    target_date_str = date or str(datetime.now(timezone.utc).date())
    cache_key = f"tension:countries:{region or 'all'}:{target_date_str}:{sv}"

    async def compute():
        svc = QueryService(db, scoring_version=sv)
        target = None
        if date:
            from datetime import date as date_type
            target = date_type.fromisoformat(date)
        return await svc.get_countries(target, region=region, limit=limit)

    return await cache_get_or_compute(cache_key, compute, TTL_COUNTRIES)
