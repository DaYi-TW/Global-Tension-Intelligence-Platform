from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.database import get_db
from app.core.redis import get_redis

router = APIRouter()


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """系統健康檢查"""
    # 檢查 DB 連線
    try:
        await db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {e}"

    # 檢查 Redis 連線
    try:
        redis = await get_redis()
        await redis.ping()
        redis_status = "ok"
    except Exception as e:
        redis_status = f"error: {e}"

    overall = "ok" if db_status == "ok" and redis_status == "ok" else "degraded"

    return {
        "status": overall,
        "services": {
            "database": db_status,
            "redis": redis_status,
        },
    }
