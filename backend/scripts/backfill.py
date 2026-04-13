"""
Historical Backfill Script
==========================
從 GDELT 歷史資料檔案抓取指定日期範圍的資料，並重算各層張力分數。

用法（在 backend 容器或本機虛擬環境內執行）：
    python scripts/backfill.py --from 2026-02-28 --to 2026-04-07

GDELT masterfilelist 格式：每行 "<bytes> <md5> <url>"
歷史 GKG 檔案 URL 格式：
    http://data.gdeltproject.org/gdeltv2/YYYYMMDDHHMMSS.gkg.csv.zip
每 15 分鐘一個檔案，每天最多 96 個檔案。

策略：
    每天只抓 06:00 / 12:00 / 18:00 / 00:00 UTC 共 4 個時間點的 GKG 快照，
    以覆蓋全天主要新聞，同時避免資料量過大。
    若需要更完整資料可調高 SNAPSHOTS_PER_DAY。
"""

import asyncio
import csv
import io
import json
import logging
import os
import sys
import zipfile
from argparse import ArgumentParser
from datetime import date, datetime, timedelta, timezone
from typing import Optional

# GDELT GKG 部分欄位（如 Quotations、Extras）可能超過預設 131072 bytes 限制
csv.field_size_limit(10_000_000)  # 10 MB

import httpx

# ── 把 backend/ 加入 sys.path（在容器裡 WORKDIR=/app，本機直接執行需調整）
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from pipeline.ingestion.base import RawEventDict
from pipeline.ingestion.gdelt_adapter import GKG_COLUMNS, WEB_SOURCE_ID, GDELTAdapter
from pipeline.ingestion.repository import save_raw_events
from pipeline.normalization.service import NormalizationService
from pipeline.scoring.engine import ScoringEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("backfill")

# ── 每天抓幾個時間快照（每個檔案約 2,000 筆 GKG records）
# 4 個快照 × 2,000 筆 ≈ 每天 8,000 筆原始事件，正規化後約 1,000–3,000 筆有效事件
SNAPSHOTS_PER_DAY = 4
SNAPSHOT_HOURS = [0, 6, 12, 18]   # UTC 整點

# GDELT masterfilelist（含所有歷史 GKG 檔案 URL）
MASTER_FILE_URL = "http://data.gdeltproject.org/gdeltv2/masterfilelist.txt"

MAX_RECORDS_PER_FILE = 2000   # 與 GDELTAdapter 一致


# ─── 1. 從 masterfilelist 找指定日期的 GKG URL ────────────────────────────────

async def fetch_master_index(client: httpx.AsyncClient) -> list[str]:
    """下載 masterfilelist.txt，回傳所有 GKG URL（只取 .gkg.csv.zip）"""
    logger.info(f"Downloading GDELT master file list from {MASTER_FILE_URL} ...")
    resp = await client.get(MASTER_FILE_URL, timeout=120)
    resp.raise_for_status()
    urls = []
    for line in resp.text.strip().splitlines():
        parts = line.strip().split(" ")
        if len(parts) >= 3:
            url = parts[2]
            if "gkg" in url.lower() and url.endswith(".gkg.csv.zip"):
                urls.append(url)
    logger.info(f"Master file list: found {len(urls)} GKG files")
    return urls


def filter_urls_for_date(all_urls: list[str], target_date: date) -> list[str]:
    """
    從全部 URL 中篩選 target_date 當天、SNAPSHOT_HOURS 時間點的檔案。
    URL 格式範例：http://data.gdeltproject.org/gdeltv2/20260407060000.gkg.csv.zip
                                                        ^^^^^^^^^^^^
    """
    date_str = target_date.strftime("%Y%m%d")
    matched = []

    for url in all_urls:
        filename = url.split("/")[-1]  # e.g. 20260407060000.gkg.csv.zip
        if not filename.startswith(date_str):
            continue
        # 取時間部分 HHMMSS
        time_part = filename[8:14]  # 字元 8~13
        if len(time_part) < 6:
            continue
        try:
            hour = int(time_part[:2])
        except ValueError:
            continue
        if hour in SNAPSHOT_HOURS:
            matched.append(url)

    return matched


# ─── 2. 下載並解析單個 GKG 檔案 ──────────────────────────────────────────────

async def fetch_gkg_file(client: httpx.AsyncClient, url: str) -> list[RawEventDict]:
    """下載指定 URL 的 GKG 壓縮檔，解析並回傳 RawEventDict 列表"""
    logger.info(f"  Fetching {url} ...")
    try:
        resp = await client.get(url, timeout=httpx.Timeout(30.0, read=120.0))
        resp.raise_for_status()
    except Exception as e:
        logger.warning(f"  Failed to download {url}: {e}")
        return []

    try:
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            csv_bytes = zf.read(zf.namelist()[0])
    except Exception as e:
        logger.warning(f"  Failed to unzip {url}: {e}")
        return []

    adapter = GDELTAdapter()
    records = []
    reader = csv.DictReader(
        io.StringIO(csv_bytes.decode("utf-8", errors="replace")),
        fieldnames=GKG_COLUMNS,
        delimiter="\t",
    )
    count = 0
    try:
        for row in reader:
            try:
                if count >= MAX_RECORDS_PER_FILE:
                    break
                if row.get("SourceCollectionIdentifier") != WEB_SOURCE_ID:
                    continue
                raw = adapter._parse_row(row)
                if raw:
                    records.append(raw)
                    count += 1
            except Exception:
                continue
    except csv.Error as e:
        logger.warning(f"  CSV error in {url.split('/')[-1]}: {e} — using {len(records)} records parsed so far")

    logger.info(f"  Parsed {len(records)} records from {url.split('/')[-1]}")
    return records


# ─── 3. 支援 target_date 的 ScoringEngine 擴充 ───────────────────────────────

class HistoricalScoringEngine(ScoringEngine):
    """覆寫 target_date，讓 ScoringEngine 為歷史日期計算快照"""

    def __init__(self, session: AsyncSession, target_date: date, scoring_version: str = "v1.0"):
        super().__init__(session, scoring_version)
        self.target_date = target_date
        # 評分視窗以 target_date 當天結束點為基準
        self.now = datetime.combine(
            target_date + timedelta(days=1), datetime.min.time()
        ).replace(tzinfo=timezone.utc)


# ─── 4. 主流程 ────────────────────────────────────────────────────────────────

async def backfill(from_date: date, to_date: date):
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with httpx.AsyncClient(headers={"User-Agent": "GTIP-Backfill/1.0"}) as client:
        # 下載 master file index 一次
        all_gkg_urls = await fetch_master_index(client)

        # 逐日處理
        current = from_date
        while current <= to_date:
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing date: {current}")
            logger.info(f"{'='*60}")

            # ── Step A: 找到該日的 GKG 檔案 URL
            day_urls = filter_urls_for_date(all_gkg_urls, current)
            if not day_urls:
                logger.warning(f"  No GKG files found for {current}, skipping ingestion")
            else:
                logger.info(f"  Found {len(day_urls)} GKG snapshot(s) for {current}")

                # ── Step B: 下載並儲存 raw_events
                total_inserted = total_skipped = 0
                for url in day_urls:
                    raw_events = await fetch_gkg_file(client, url)
                    if raw_events:
                        async with SessionLocal() as session:
                            ins, skp = await save_raw_events(session, raw_events)
                            total_inserted += ins
                            total_skipped += skp

                logger.info(f"  Ingestion done: inserted={total_inserted}, skipped(dup)={total_skipped}")

            # ── Step C: 正規化 pending raw_events（可能跨多批）
            logger.info(f"  Running normalization ...")
            norm_total = {"processed": 0, "inserted": 0, "skipped": 0}
            for _ in range(20):  # 最多跑 20 批（每批 500 筆，足夠處理 10,000 筆）
                async with SessionLocal() as session:
                    svc = NormalizationService(session)
                    result = await svc.run()
                norm_total["processed"] += result["processed"]
                norm_total["inserted"]  += result["inserted"]
                norm_total["skipped"]   += result["skipped"]
                if result["processed"] == 0:
                    break  # 沒有更多 pending 了
            logger.info(f"  Normalization total: {norm_total}")

            # ── Step D: 評分並聚合（用 HistoricalScoringEngine 以正確日期為目標）
            logger.info(f"  Running scoring for {current} ...")
            async with SessionLocal() as session:
                scoring = HistoricalScoringEngine(
                    session,
                    target_date=current,
                    scoring_version=settings.scoring_version,
                )
                score_result = await scoring.run()
            logger.info(f"  Scoring done: {score_result}")

            current += timedelta(days=1)

    await engine.dispose()
    logger.info("\n✅ Backfill complete!")


def parse_args():
    parser = ArgumentParser(description="GTIP Historical Backfill")
    parser.add_argument(
        "--from", dest="from_date", required=True,
        help="Start date (YYYY-MM-DD, inclusive)"
    )
    parser.add_argument(
        "--to", dest="to_date", required=True,
        help="End date (YYYY-MM-DD, inclusive)"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        from_date = date.fromisoformat(args.from_date)
        to_date   = date.fromisoformat(args.to_date)
    except ValueError as e:
        print(f"Invalid date format: {e}")
        sys.exit(1)

    if from_date > to_date:
        print("--from must be <= --to")
        sys.exit(1)

    days = (to_date - from_date).days + 1
    logger.info(f"Starting backfill: {from_date} → {to_date} ({days} days)")
    asyncio.run(backfill(from_date, to_date))
