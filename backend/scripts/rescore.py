"""
Rescore Script
==============
對已有的正規化事件重新執行 scoring，不重抓 GDELT。
用於調整評分公式後重算所有歷史日期。

用法：
    python scripts/rescore.py --from 2026-02-28 --to 2026-04-08
"""

import asyncio
import logging
import os
import sys
from argparse import ArgumentParser
from datetime import date, datetime, timedelta, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from pipeline.scoring.engine import ScoringEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("rescore")


class HistoricalScoringEngine(ScoringEngine):
    def __init__(self, session: AsyncSession, target_date: date, scoring_version: str = "v1.0"):
        super().__init__(session, scoring_version)
        self.target_date = target_date
        self.now = datetime.combine(
            target_date + timedelta(days=1), datetime.min.time()
        ).replace(tzinfo=timezone.utc)


async def rescore(from_date: date, to_date: date):
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    current = from_date
    while current <= to_date:
        logger.info(f"Rescoring {current} ...")
        async with SessionLocal() as session:
            scoring = HistoricalScoringEngine(
                session,
                target_date=current,
                scoring_version=settings.scoring_version,
            )
            result = await scoring.run()
        logger.info(f"  Done: {result}")
        current += timedelta(days=1)

    await engine.dispose()
    logger.info("\n✅ Rescore complete!")


def parse_args():
    parser = ArgumentParser(description="GTIP Rescore")
    parser.add_argument("--from", dest="from_date", required=True)
    parser.add_argument("--to",   dest="to_date",   required=True)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    from_date = date.fromisoformat(args.from_date)
    to_date   = date.fromisoformat(args.to_date)
    days = (to_date - from_date).days + 1
    logger.info(f"Starting rescore: {from_date} → {to_date} ({days} days)")
    asyncio.run(rescore(from_date, to_date))
