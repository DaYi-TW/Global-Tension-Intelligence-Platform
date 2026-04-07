"""
Normalization Service
讀取 raw_events WHERE normalized=FALSE，
正規化後寫入 events / event_countries / event_dimensions
對應 docs/02-data-pipeline.md §2.4
"""

import hashlib
import json
import logging
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Event, EventCountry, EventDimension, RawEvent
from pipeline.normalization.country_code_map import fips_to_iso3
from pipeline.normalization.event_type_map import (
    gdelt_themes_to_event_type,
    get_event_type_rule,
    infer_dimensions,
)
from pipeline.normalization.region_map import get_primary_region

logger = logging.getLogger(__name__)

BATCH_LIMIT = 500  # 每次最多處理 500 筆


class NormalizationService:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def run(self) -> dict:
        """執行一批正規化，回傳統計資訊"""
        raw_events = await self._fetch_pending()
        if not raw_events:
            logger.info("Normalization: no pending raw_events")
            return {"processed": 0, "inserted": 0, "skipped": 0}

        logger.info(f"Normalization: processing {len(raw_events)} raw_events")
        inserted = skipped = 0

        for raw in raw_events:
            try:
                ok = await self._process_one(raw)
                if ok:
                    inserted += 1
                else:
                    skipped += 1
                # 無論是否成功，都標記為已正規化（避免反覆重試格式問題）
                await self._mark_normalized(raw.id)
            except Exception as e:
                logger.error(f"Normalization error for raw_event {raw.id}: {e}")
                skipped += 1

        await self.session.commit()
        logger.info(f"Normalization: inserted={inserted}, skipped={skipped}")
        return {"processed": len(raw_events), "inserted": inserted, "skipped": skipped}

    async def _fetch_pending(self) -> list[RawEvent]:
        result = await self.session.execute(
            select(RawEvent)
            .where(RawEvent.normalized == False)  # noqa: E712
            .order_by(RawEvent.fetched_at)
            .limit(BATCH_LIMIT)
        )
        return list(result.scalars().all())

    async def _process_one(self, raw: RawEvent) -> bool:
        """處理單筆 raw_event，回傳是否成功寫入 events"""
        payload = raw.raw_payload
        if isinstance(payload, str):
            payload = json.loads(payload)

        if raw.source_type == "gdelt":
            return await self._process_gdelt(raw, payload)
        else:
            logger.warning(f"Unknown source_type: {raw.source_type}")
            return False

    async def _process_gdelt(self, raw: RawEvent, payload: dict) -> bool:
        # ── 時間解析 ──────────────────────────────────────────────
        event_time_str = payload.get("event_time")
        if not event_time_str:
            return False
        event_time = datetime.fromisoformat(event_time_str)

        # ── 國家代碼轉換（FIPS → ISO alpha-3）────────────────────
        fips_codes = payload.get("country_fips_codes", [])
        iso3_codes = []
        for fips in fips_codes:
            iso3 = fips_to_iso3(fips)
            if iso3:
                iso3_codes.append(iso3)

        needs_review = len(iso3_codes) == 0 and len(fips_codes) > 0

        # ── 事件類型推斷 ──────────────────────────────────────────
        themes = payload.get("themes", [])
        event_type = gdelt_themes_to_event_type(themes)
        rule = get_event_type_rule(event_type)

        # ── 區域推斷 ──────────────────────────────────────────────
        region_code = get_primary_region(iso3_codes)

        # ── source_confidence 計算 ────────────────────────────────
        source_count = payload.get("source_count", 1)
        source_confidence = min(1.0, 0.5 + 0.1 * source_count)
        # GDELT 單一來源加成係數較低（比 ACLED 可信度低）
        source_confidence = round(max(0.3, source_confidence * 0.9), 3)

        # ── 生成 event_id ──────────────────────────────────────────
        date_str = event_time.strftime("%Y%m%d")
        # 用 source_event_id hash 確保跨來源可去重
        hash_suffix = hashlib.md5(raw.source_event_id.encode()).hexdigest()[:8]
        event_id = f"evt_{date_str}_{hash_suffix}"

        # ── 標題（GDELT 無獨立標題，用主題組合）──────────────────
        top_themes = themes[:3] if themes else ["Unknown event"]
        title = f"[GDELT] {', '.join(top_themes)}"
        if iso3_codes:
            title += f" — {', '.join(iso3_codes[:3])}"
        title = title[:500]  # 截斷

        source_url = payload.get("source_url", "")
        source_name = payload.get("source_name", "")

        # ── 寫入 events（ON CONFLICT DO NOTHING）─────────────────
        stmt = text("""
            INSERT INTO events (
                event_id, source_type, source_event_id,
                title, content, event_time,
                region_code, event_type, primary_dimension,
                risk_or_relief, severity, source_count, source_confidence,
                needs_review, ai_analyzed, scoring_version
            ) VALUES (
                :event_id, :source_type, :source_event_id,
                :title, :content, :event_time,
                :region_code, :event_type, :primary_dimension,
                :risk_or_relief, :severity, :source_count, :source_confidence,
                :needs_review, FALSE, 'v1.0'
            )
            ON CONFLICT (event_id) DO NOTHING
            RETURNING id
        """)
        result = await self.session.execute(stmt, {
            "event_id":          event_id,
            "source_type":       raw.source_type,
            "source_event_id":   raw.source_event_id,
            "title":             title,
            "content":           source_url,
            "event_time":        event_time,
            "region_code":       region_code,
            "event_type":        event_type,
            "primary_dimension": rule.primary_dimension,
            "risk_or_relief":    rule.risk_or_relief,
            "severity":          rule.base_severity,
            "source_count":      source_count,
            "source_confidence": source_confidence,
            "needs_review":      needs_review,
        })
        row = result.fetchone()
        if not row:
            # ON CONFLICT DO NOTHING → 已存在，跳過
            return False

        event_db_id = row[0]

        # ── 寫入 event_countries ──────────────────────────────────
        if iso3_codes:
            # 第一個國家為主要國家（initiator），其他為 affected
            roles = ["initiator"] + ["affected"] * (len(iso3_codes) - 1)
            for iso3, role in zip(iso3_codes, roles):
                await self.session.execute(text("""
                    INSERT INTO event_countries (event_id, country_code, role)
                    VALUES (:event_id, :country_code, :role)
                    ON CONFLICT (event_id, country_code) DO NOTHING
                """), {"event_id": event_db_id, "country_code": iso3, "role": role})

        # ── 寫入 event_dimensions（source='rule'）────────────────
        dims = infer_dimensions(rule.primary_dimension, rule.base_severity)
        await self.session.execute(text("""
            INSERT INTO event_dimensions (
                event_id, military_score, political_score,
                economic_score, social_score, cyber_score, source
            ) VALUES (
                :event_id, :military, :political,
                :economic, :social, :cyber, 'rule'
            )
            ON CONFLICT (event_id) DO NOTHING
        """), {
            "event_id": event_db_id,
            "military": dims["military"],
            "political": dims["political"],
            "economic": dims["economic"],
            "social": dims["social"],
            "cyber": dims["cyber"],
        })

        # ── 寫入 news_sources（若有 URL）─────────────────────────
        if source_url:
            await self.session.execute(text("""
                INSERT INTO news_sources (event_id, source_name, source_url)
                VALUES (:event_id, :source_name, :source_url)
            """), {
                "event_id":    event_db_id,
                "source_name": source_name,
                "source_url":  source_url,
            })

        return True

    async def _mark_normalized(self, raw_id: int):
        await self.session.execute(
            text("UPDATE raw_events SET normalized = TRUE WHERE id = :id"),
            {"id": raw_id}
        )
