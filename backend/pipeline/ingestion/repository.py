"""
Raw Events Repository — 負責寫入 raw_events 表
"""

import json
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from pipeline.ingestion.base import RawEventDict

logger = logging.getLogger(__name__)

CHUNK_SIZE = 100  # 每次批次寫入筆數


async def save_raw_events(
    session: AsyncSession,
    raw_events: list[RawEventDict],
) -> tuple[int, int]:
    """
    批次寫入 raw_events，去重策略：ON CONFLICT DO NOTHING
    回傳 (inserted_count, skipped_count)
    """
    if not raw_events:
        return 0, 0

    inserted = 0
    total = len(raw_events)

    # 分批寫入，避免單筆 SQL 過長
    for i in range(0, total, CHUNK_SIZE):
        chunk = raw_events[i:i + CHUNK_SIZE]
        chunk_inserted = await _insert_chunk(session, chunk)
        inserted += chunk_inserted

    skipped = total - inserted
    logger.info(f"raw_events: inserted={inserted}, skipped(dup)={skipped}")
    return inserted, skipped


async def _insert_chunk(session: AsyncSession, chunk: list[RawEventDict]) -> int:
    """單批次寫入，使用逐筆 execute 確保 asyncpg 相容性"""
    inserted = 0
    for raw in chunk:
        payload_json = json.dumps(raw["raw_payload"])
        result = await session.execute(
            text(
                "INSERT INTO raw_events (source_type, source_event_id, raw_payload) "
                "VALUES (:source_type, :source_event_id, CAST(:raw_payload AS jsonb)) "
                "ON CONFLICT (source_type, source_event_id) DO NOTHING"
            ),
            {
                "source_type":     raw["source_type"],
                "source_event_id": raw["source_event_id"],
                "raw_payload":     payload_json,
            }
        )
        if result.rowcount == 1:
            inserted += 1

    await session.commit()
    return inserted
