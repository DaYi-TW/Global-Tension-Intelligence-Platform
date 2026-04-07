"""
Cache helper — Redis 讀寫 + 自動降級至 DB
對應 docs/06-caching-strategy.md
"""

import json
import logging
from typing import Any, Callable, Coroutine

from redis.exceptions import ConnectionError as RedisConnectionError

from app.core.redis import get_redis

logger = logging.getLogger(__name__)


async def cache_get_or_compute(
    key: str,
    compute_fn: Callable[[], Coroutine[Any, Any, Any]],
    ttl: int,
) -> Any:
    """
    1. 嘗試讀 Redis
    2. Miss → 執行 compute_fn
    3. 寫回 Redis（失敗不影響回傳）
    """
    # 嘗試讀取快取
    try:
        redis = await get_redis()
        cached = await redis.get(key)
        if cached:
            return json.loads(cached)
    except (RedisConnectionError, Exception) as e:
        logger.warning(f"Redis read failed for key={key}: {e}, falling back to DB")

    # 計算結果
    result = await compute_fn()

    # 寫回 Redis
    try:
        redis = await get_redis()
        await redis.setex(key, ttl, json.dumps(result, default=str))
    except (RedisConnectionError, Exception) as e:
        logger.warning(f"Redis write failed for key={key}: {e}")

    return result


async def cache_delete(*keys: str) -> None:
    """刪除一或多個快取 key"""
    try:
        redis = await get_redis()
        if keys:
            await redis.delete(*keys)
    except (RedisConnectionError, Exception) as e:
        logger.warning(f"Redis delete failed: {e}")
