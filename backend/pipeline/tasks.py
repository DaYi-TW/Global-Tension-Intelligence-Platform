"""
Celery Tasks — 所有 Pipeline 任務定義
對應 docs/09-scheduler-worker.md
"""

import asyncio
import logging

from pipeline.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    """
    在同步 Celery task 中執行 async 函式。
    每次建立全新 event loop，確保 asyncpg 連線不跨 loop。
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
        asyncio.set_event_loop(None)


# ─── 資料抓取 ──────────────────────────────────────────────────────────────

@celery_app.task(
    bind=True,
    name="pipeline.tasks.ingest_gdelt",
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    time_limit=180,
)
def ingest_gdelt(self):
    """抓取 GDELT 最新資料，寫入 raw_events"""
    logger.info("Starting GDELT ingestion")

    async def _run():
        # 每次都建立新 engine，確保不跨 event loop
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
        from app.core.config import get_settings
        from pipeline.ingestion.gdelt_adapter import GDELTAdapter
        from pipeline.ingestion.repository import save_raw_events

        settings = get_settings()
        engine = create_async_engine(settings.database_url)
        SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        try:
            adapter = GDELTAdapter()
            raw_events = await adapter.fetch()

            async with SessionLocal() as session:
                inserted, skipped = await save_raw_events(session, raw_events)
        finally:
            await engine.dispose()

        logger.info(f"GDELT ingest done: inserted={inserted}, skipped={skipped}")
        return {"inserted": inserted, "skipped": skipped}

    return _run_async(_run())


@celery_app.task(
    bind=True,
    name="pipeline.tasks.ingest_acled",
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    time_limit=120,
)
def ingest_acled(self):
    """抓取 ACLED 更新，寫入 raw_events"""
    logger.info("Starting ACLED ingestion")
    # TODO: 實作 ACLEDAdapter
    raise NotImplementedError("ACLED adapter not yet implemented")


@celery_app.task(
    bind=True,
    name="pipeline.tasks.ingest_news",
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    time_limit=120,
)
def ingest_news(self):
    """補全新聞原文，寫入 news_sources"""
    logger.info("Starting news ingestion")
    # TODO: 實作 NewsAdapter
    raise NotImplementedError("News adapter not yet implemented")


# ─── 資料處理 ──────────────────────────────────────────────────────────────

@celery_app.task(
    bind=True,
    name="pipeline.tasks.normalize_pending",
    max_retries=3,
    default_retry_delay=60,
    time_limit=300,
)
def normalize_pending(self):
    """正規化待處理事件（每次最多 500 筆）"""
    logger.info("Starting normalization of pending raw_events")

    async def _run():
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
        from app.core.config import get_settings
        from pipeline.normalization.service import NormalizationService

        settings = get_settings()
        engine = create_async_engine(settings.database_url)
        SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        try:
            async with SessionLocal() as session:
                service = NormalizationService(session)
                result = await service.run()
        finally:
            await engine.dispose()

        logger.info(f"Normalization done: {result}")
        return result

    return _run_async(_run())


@celery_app.task(
    bind=True,
    name="pipeline.tasks.ai_enrich_pending",
    max_retries=2,
    default_retry_delay=120,
    time_limit=600,
)
def ai_enrich_pending(self):
    """AI 批次分析（每次最多 200 筆，批次大小 20）"""
    logger.info("Starting AI enrichment of pending events")
    # TODO: 實作 AIAnalysisService
    raise NotImplementedError("AI analysis service not yet implemented")


# ─── 評分計算 ──────────────────────────────────────────────────────────────

@celery_app.task(
    bind=True,
    name="pipeline.tasks.score_and_aggregate",
    max_retries=3,
    default_retry_delay=60,
    time_limit=300,
)
def score_and_aggregate(self):
    """重算並聚合各層分數，完成後觸發 refresh_cache"""
    logger.info("Starting score_and_aggregate")
    # TODO: 實作 ScoringEngine
    raise NotImplementedError("Scoring engine not yet implemented")
    # 完成後觸發快取更新：
    # refresh_cache.delay()


@celery_app.task(
    bind=True,
    name="pipeline.tasks.refresh_cache",
    max_retries=3,
    default_retry_delay=30,
    time_limit=120,
)
def refresh_cache(self):
    """更新 Redis 快取（由 score_and_aggregate 完成後觸發）"""
    logger.info("Starting cache refresh")
    # TODO: 實作 CacheWriter
    raise NotImplementedError("Cache writer not yet implemented")


# ─── 維護任務 ──────────────────────────────────────────────────────────────

@celery_app.task(
    bind=True,
    name="pipeline.tasks.daily_summary_gen",
    max_retries=2,
    default_retry_delay=300,
    time_limit=300,
)
def daily_summary_gen(self):
    """生成 AI 每日摘要（每日 06:00 UTC）"""
    logger.info("Starting daily summary generation")
    # TODO: 實作 DailySummaryService
    raise NotImplementedError("Daily summary service not yet implemented")


@celery_app.task(
    bind=True,
    name="pipeline.tasks.full_recalculate",
    max_retries=0,   # 不自動重試，需人工介入
    time_limit=3600,
)
def full_recalculate(self):
    """全量重算（每週日 02:00 UTC），完成後觸發 refresh_cache"""
    logger.info("Starting full recalculation")
    # TODO: 實作全量重算邏輯
    raise NotImplementedError("Full recalculate not yet implemented")


@celery_app.task(
    bind=True,
    name="pipeline.tasks.cleanup_old_cache",
    max_retries=2,
    default_retry_delay=60,
    time_limit=600,
)
def cleanup_old_cache(self):
    """清理過期快取 key 與舊資料（每日 03:00 UTC）"""
    logger.info("Starting old cache cleanup")
    # TODO: 實作清理邏輯
    raise NotImplementedError("Cleanup task not yet implemented")
