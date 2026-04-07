"""
GDELT Adapter
- 資料集：GDELT 2.0 GKG（Global Knowledge Graph）
- 端點：http://data.gdeltproject.org/gdeltv2/lastupdate.txt
- 頻率：每 15 分鐘更新一次
- 格式：CSV（壓縮，Tab 分隔）
對應 docs/02-data-pipeline.md §2.3 GDELT Adapter
"""

import csv
import gzip
import io
import logging
import zipfile
from datetime import datetime, timezone

import httpx

from pipeline.ingestion.base import BaseAdapter, RawEventDict

logger = logging.getLogger(__name__)

LASTUPDATE_URL = "http://data.gdeltproject.org/gdeltv2/lastupdate.txt"

# GDELT GKG CSV 欄位名稱（Tab 分隔，共 27 欄）
GKG_COLUMNS = [
    "GKGRECORDID", "DATE", "SourceCollectionIdentifier", "SourceCommonName",
    "DocumentIdentifier", "Counts", "V2Counts", "Themes", "V2Themes",
    "Locations", "V2Locations", "Persons", "V2Persons", "Organizations",
    "V2Organizations", "V2Tone", "Dates", "GCAM", "SharingImage",
    "RelatedImages", "SocialImageEmbeds", "SocialVideoEmbeds", "Quotations",
    "AllNames", "Amounts", "TranslationInfo", "Extras",
]

# 只抓 WEB 來源（SourceCollectionIdentifier=1）降低雜訊
WEB_SOURCE_ID = "1"

# 每次最多處理幾筆（避免單次任務過長）
MAX_RECORDS_PER_RUN = 2000


class GDELTAdapter(BaseAdapter):

    def get_source_type(self) -> str:
        return "gdelt"

    async def fetch(self) -> list[RawEventDict]:
        """
        1. 讀取 lastupdate.txt 取得最新 GKG 檔案 URL
        2. 下載並解壓縮 CSV
        3. 解析欄位，回傳 RawEventDict 列表
        """
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, read=90.0)) as client:
            # Step 1: 取得最新更新清單
            gkg_url = await self._get_latest_gkg_url(client)
            if not gkg_url:
                logger.warning("GDELT: could not find GKG URL in lastupdate.txt")
                return []

            logger.info(f"GDELT: fetching {gkg_url}")

            # Step 2: 下載壓縮檔（ZIP 格式）
            resp = await client.get(gkg_url)
            resp.raise_for_status()

        # Step 3: 解壓縮（GDELT 使用 ZIP，非 gzip）
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            csv_filename = zf.namelist()[0]
            csv_bytes = zf.read(csv_filename)

        # Step 3: 解析 CSV
        records = []
        reader = csv.DictReader(
            io.StringIO(csv_bytes.decode("utf-8", errors="replace")),
            fieldnames=GKG_COLUMNS,
            delimiter="\t",
        )

        count = 0
        for row in reader:
            if count >= MAX_RECORDS_PER_RUN:
                break
            # 只處理 WEB 來源
            if row.get("SourceCollectionIdentifier") != WEB_SOURCE_ID:
                continue

            raw = self._parse_row(row)
            if raw:
                records.append(raw)
                count += 1

        logger.info(f"GDELT: parsed {len(records)} records")
        return records

    async def _get_latest_gkg_url(self, client: httpx.AsyncClient) -> str | None:
        """解析 lastupdate.txt，回傳 GKG CSV 的下載 URL"""
        resp = await client.get(LASTUPDATE_URL)
        resp.raise_for_status()

        # lastupdate.txt 格式：每行 "<bytes> <md5> <url>"
        # 包含 export, mentions, gkg 三種檔案，找 gkg
        for line in resp.text.strip().splitlines():
            parts = line.strip().split(" ")
            if len(parts) >= 3:
                url = parts[2]
                if "gkg" in url.lower() and url.endswith(".csv.zip"):
                    return url
        return None

    def _parse_row(self, row: dict) -> RawEventDict | None:
        """將一列 GKG CSV 轉換為 RawEventDict"""
        record_id = row.get("GKGRECORDID", "").strip()
        if not record_id:
            return None

        date_str = row.get("DATE", "").strip()
        event_time = self._parse_gdelt_date(date_str)
        if not event_time:
            return None

        # 解析地點（LOCATIONS 欄，分號分隔，每個地點格式複雜）
        locations_raw = row.get("Locations", "") or ""
        country_fips_codes = self._extract_country_fips(locations_raw)

        # 解析主題
        themes_raw = row.get("Themes", "") or ""
        themes = [t.strip() for t in themes_raw.split(";") if t.strip()]

        # 解析語氣（V2Tone：逗號分隔，第一個值為整體語氣）
        tone_raw = row.get("V2Tone", "") or ""
        tone = self._parse_tone(tone_raw)

        # 來源 URL（DocumentIdentifier）
        source_url = row.get("DocumentIdentifier", "").strip()

        # 來源名稱（SourceCommonName）
        source_name = row.get("SourceCommonName", "").strip()

        # 文章數（Counts 欄，較不可靠；用 AllNames 長度估算）
        # 簡化：預設 1，後續正規化時合併同類事件累積
        source_count = 1

        payload = {
            "record_id":          record_id,
            "event_time":         event_time.isoformat(),
            "date_raw":           date_str,
            "themes":             themes,
            "country_fips_codes": country_fips_codes,
            "tone":               tone,
            "source_url":         source_url,
            "source_name":        source_name,
            "source_count":       source_count,
            "locations_raw":      locations_raw[:500],  # 截斷避免過大
        }

        return RawEventDict(
            source_type="gdelt",
            source_event_id=record_id,
            raw_payload=payload,
        )

    @staticmethod
    def _parse_gdelt_date(date_str: str) -> datetime | None:
        """
        GDELT DATE 為 15 位整數：YYYYMMDDHHMMSS（UTC）
        範例：20260407080000
        """
        if not date_str or len(date_str) < 14:
            return None
        try:
            dt = datetime.strptime(date_str[:14], "%Y%m%d%H%M%S")
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return None

    @staticmethod
    def _extract_country_fips(locations_raw: str) -> list[str]:
        """
        GDELT Locations 欄格式：
        多個地點以分號分隔，每個地點以 # 分隔各子欄位
        子欄位索引 2（0-based）為 CountryCode（FIPS）
        範例：1#Iran#IR#35.6892#51.3890#/m/03shp;3#Tehran#IR#...
        """
        if not locations_raw:
            return []
        codes = set()
        for loc in locations_raw.split(";"):
            parts = loc.split("#")
            if len(parts) >= 3:
                fips = parts[2].strip().upper()
                if fips and len(fips) == 2:
                    codes.add(fips)
        return list(codes)

    @staticmethod
    def _parse_tone(tone_raw: str) -> float | None:
        """
        V2Tone 第一個逗號分隔值為整體語氣分數（負值=負面/風險）
        """
        if not tone_raw:
            return None
        try:
            return float(tone_raw.split(",")[0])
        except (ValueError, IndexError):
            return None
