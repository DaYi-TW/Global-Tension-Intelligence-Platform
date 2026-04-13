"""
Query Service — 從 PostgreSQL 查詢各種 API 所需資料
"""

import logging
from datetime import date, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from pipeline.scoring.formulas import get_tension_band

logger = logging.getLogger(__name__)

RANGE_DAYS = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}


class QueryService:

    def __init__(self, session: AsyncSession, scoring_version: str = "v1.0"):
        self.session = session
        self.sv = scoring_version

    async def get_dashboard_overview(self, target_date: date | None = None) -> dict:
        from datetime import datetime, timezone
        if target_date is None:
            target_date = datetime.now(timezone.utc).date()

        today_str = str(target_date)
        yesterday_str = str(target_date - timedelta(days=1))

        # ── 今日全球分數 ──────────────────────────────────────────────────
        global_row = await self._fetch_global(today_str)
        if not global_row:
            return {"error": "no data for date", "date": today_str}

        yesterday_row = await self._fetch_global(yesterday_str)
        global_delta = None
        if yesterday_row:
            global_delta = round(
                float(global_row["net_tension"]) - float(yesterday_row["net_tension"]), 2
            )

        band, band_zh = get_tension_band(float(global_row["net_tension"]))

        # ── 7 天趨勢 ─────────────────────────────────────────────────────
        trend_rows = await self.session.execute(text("""
            SELECT date, net_tension
            FROM global_tension_daily
            WHERE date >= :from_date AND date <= :to_date
              AND scoring_version = :sv
            ORDER BY date ASC
        """), {
            "from_date": target_date - timedelta(days=6),
            "to_date": target_date,
            "sv": self.sv,
        })
        trend_data = trend_rows.fetchall()
        trend_7d = [round(float(r.net_tension), 2) for r in trend_data]
        # 補齊 7 個元素（若歷史資料不足）
        while len(trend_7d) < 7:
            trend_7d.insert(0, trend_7d[0] if trend_7d else 0.0)

        # ── 前 5 高張力國家 ────────────────────────────────────────────────
        top_countries_rows = await self.session.execute(text("""
            SELECT c.country_code, c.net_tension,
                   c.net_tension - COALESCE(y.net_tension, c.net_tension) AS delta
            FROM country_tension_daily c
            LEFT JOIN country_tension_daily y
                ON y.country_code = c.country_code
               AND y.date = :yesterday
               AND y.scoring_version = :sv
            WHERE c.date = :today AND c.scoring_version = :sv
            ORDER BY c.net_tension DESC
            LIMIT 5
        """), {"today": target_date, "yesterday": target_date - timedelta(days=1), "sv": self.sv})

        top_countries = []
        for r in top_countries_rows.fetchall():
            b, bz = get_tension_band(float(r.net_tension))
            top_countries.append({
                "country_code": r.country_code,
                "net_tension":  round(float(r.net_tension), 2),
                "band":         b,
                "band_zh":      bz,
                "delta":        round(float(r.delta), 2) if r.delta else None,
            })

        # ── 所有區域排行 ──────────────────────────────────────────────────
        regions_rows = await self.session.execute(text("""
            SELECT region_code, net_tension, top_country_codes
            FROM region_tension_daily
            WHERE date = :today AND scoring_version = :sv
            ORDER BY net_tension DESC
        """), {"today": target_date, "sv": self.sv})

        top_regions = []
        for r in regions_rows.fetchall():
            b, bz = get_tension_band(float(r.net_tension))
            top_regions.append({
                "region_code":       r.region_code,
                "net_tension":       round(float(r.net_tension), 2),
                "band":              b,
                "band_zh":           bz,
                "top_country_codes": list(r.top_country_codes or []),
            })

        # ── 最快上升國家（過去 24h 漲幅最大）───────────────────────────
        fastest_rows = await self.session.execute(text("""
            SELECT c.country_code,
                   c.net_tension,
                   c.net_tension - COALESCE(y.net_tension, 0) AS delta
            FROM country_tension_daily c
            LEFT JOIN country_tension_daily y
                ON y.country_code = c.country_code
               AND y.date = :yesterday
               AND y.scoring_version = :sv
            WHERE c.date = :today AND c.scoring_version = :sv
            ORDER BY delta DESC, c.net_tension DESC
            LIMIT 5
        """), {"today": target_date, "yesterday": target_date - timedelta(days=1), "sv": self.sv})

        fastest_rising = []
        for r in fastest_rows.fetchall():
            b, bz = get_tension_band(float(r.net_tension))
            fastest_rising.append({
                "country_code": r.country_code,
                "net_tension":  round(float(r.net_tension), 2),
                "delta":        round(float(r.delta), 2),
                "band":         b,
                "band_zh":      bz,
            })

        return {
            "date":            today_str,
            "global_tension":  round(float(global_row["net_tension"]), 2),
            "global_band":     band,
            "global_band_zh":  band_zh,
            "global_delta":    global_delta,
            "dimensions": {
                "military":  round(float(global_row["military_score"]), 2),
                "political": round(float(global_row["political_score"]), 2),
                "economic":  round(float(global_row["economic_score"]), 2),
                "social":    round(float(global_row["social_score"]), 2),
                "cyber":     round(float(global_row["cyber_score"]), 2),
            },
            "trend_7d":                   trend_7d,
            "top_countries":              top_countries,
            "top_regions":                top_regions,
            "fastest_rising_countries":   fastest_rising,
            "ai_daily_summary":           global_row.get("ai_summary"),
            "scoring_version":            self.sv,
            "last_updated":               str(global_row.get("computed_at", "")),
        }

    async def get_global_trend(self, range_str: str = "30d") -> dict:
        days = RANGE_DAYS.get(range_str, 30)
        from datetime import datetime, timezone
        today = datetime.now(timezone.utc).date()
        from_date = today - timedelta(days=days - 1)

        rows = await self.session.execute(text("""
            SELECT date, net_tension,
                   military_score, political_score, economic_score,
                   social_score, cyber_score
            FROM global_tension_daily
            WHERE date >= :from_date AND scoring_version = :sv
            ORDER BY date ASC
        """), {"from_date": from_date, "sv": self.sv})

        data = []
        for r in rows.fetchall():
            data.append({
                "date":        str(r.date),
                "net_tension": round(float(r.net_tension), 2),
                "military":    round(float(r.military_score), 2),
                "political":   round(float(r.political_score), 2),
                "economic":    round(float(r.economic_score), 2),
                "social":      round(float(r.social_score), 2),
                "cyber":       round(float(r.cyber_score), 2),
            })

        return {"range": range_str, "data": data}

    async def get_regions(self, target_date: date | None = None) -> dict:
        from datetime import datetime, timezone
        if target_date is None:
            target_date = datetime.now(timezone.utc).date()
        today_str = str(target_date)

        rows = await self.session.execute(text("""
            SELECT region_code, net_tension,
                   military_score, political_score, economic_score,
                   social_score, cyber_score,
                   top_country_codes, event_count
            FROM region_tension_daily
            WHERE date = :today AND scoring_version = :sv
            ORDER BY net_tension DESC
        """), {"today": target_date, "sv": self.sv})

        regions = []
        for r in rows.fetchall():
            b, bz = get_tension_band(float(r.net_tension))
            regions.append({
                "region_code":       r.region_code,
                "net_tension":       round(float(r.net_tension), 2),
                "band":              b,
                "band_zh":           bz,
                "military":          round(float(r.military_score), 2),
                "political":         round(float(r.political_score), 2),
                "economic":          round(float(r.economic_score), 2),
                "social":            round(float(r.social_score), 2),
                "cyber":             round(float(r.cyber_score), 2),
                "top_country_codes": list(r.top_country_codes or []),
                "event_count":       r.event_count,
            })

        return {"date": today_str, "scoring_version": self.sv, "regions": regions}

    async def get_countries(
        self,
        target_date: date | None = None,
        region: str | None = None,
        limit: int = 50,
    ) -> dict:
        from datetime import datetime, timezone
        from pipeline.normalization.region_map import COUNTRY_TO_REGION

        if target_date is None:
            target_date = datetime.now(timezone.utc).date()
        today_str = str(target_date)
        yesterday_str = str(target_date - timedelta(days=1))

        rows = await self.session.execute(text("""
            SELECT c.country_code,
                   c.net_tension,
                   c.military_score, c.political_score, c.economic_score,
                   c.social_score, c.cyber_score, c.event_count,
                   c.net_tension - COALESCE(y.net_tension, c.net_tension) AS delta
            FROM country_tension_daily c
            LEFT JOIN country_tension_daily y
                ON y.country_code = c.country_code
               AND y.date = :yesterday AND y.scoring_version = :sv
            WHERE c.date = :today AND c.scoring_version = :sv
            ORDER BY c.net_tension DESC
            LIMIT :limit
        """), {
            "today":     target_date,
            "yesterday": target_date - timedelta(days=1),
            "sv":        self.sv,
            "limit":     200,   # 先取多一點，再 Python 端過濾 region
        })

        countries = []
        for r in rows.fetchall():
            # region 過濾（Python 端）
            if region and COUNTRY_TO_REGION.get(r.country_code) != region:
                continue
            b, bz = get_tension_band(float(r.net_tension))
            countries.append({
                "country_code": r.country_code,
                "net_tension":  round(float(r.net_tension), 2),
                "band":         b,
                "band_zh":      bz,
                "military":     round(float(r.military_score), 2),
                "political":    round(float(r.political_score), 2),
                "economic":     round(float(r.economic_score), 2),
                "social":       round(float(r.social_score), 2),
                "cyber":        round(float(r.cyber_score), 2),
                "event_count":  r.event_count,
                "delta":        round(float(r.delta), 2) if r.delta else None,
            })
            if len(countries) >= limit:
                break

        return {
            "date":            today_str,
            "scoring_version": self.sv,
            "total":           len(countries),
            "countries":       countries,
        }

    async def get_map_heat(
        self,
        target_date: date | None = None,
        dimension: str = "overall",
    ) -> dict:
        from datetime import datetime, timezone
        if target_date is None:
            target_date = datetime.now(timezone.utc).date()
        today_str = str(target_date)

        # dimension 對應欄位
        dim_col = {
            "overall":  "net_tension",
            "military": "military_score",
            "political":"political_score",
            "economic": "economic_score",
            "social":   "social_score",
            "cyber":    "cyber_score",
        }.get(dimension, "net_tension")

        rows = await self.session.execute(text(f"""
            SELECT country_code, {dim_col} AS score
            FROM country_tension_daily
            WHERE date = :today AND scoring_version = :sv
            ORDER BY score DESC
        """), {"today": target_date, "sv": self.sv})

        countries = []
        for r in rows.fetchall():
            b, bz = get_tension_band(float(r.score))
            countries.append({
                "country_code": r.country_code,
                "score":        round(float(r.score), 2),
                "band":         b,
                "band_zh":      bz,
            })

        return {
            "date":            today_str,
            "dimension":       dimension,
            "scoring_version": self.sv,
            "countries":       countries,
        }

    async def get_map_heat_range(
        self,
        from_date: date,
        to_date: date,
        dimension: str = "overall",
    ) -> dict:
        dim_col = {
            "overall":  "net_tension",
            "military": "military_score",
            "political":"political_score",
            "economic": "economic_score",
            "social":   "social_score",
            "cyber":    "cyber_score",
        }.get(dimension, "net_tension")

        rows = await self.session.execute(text(f"""
            SELECT date, country_code, {dim_col} AS score
            FROM country_tension_daily
            WHERE date >= :from_date AND date <= :to_date
              AND scoring_version = :sv
            ORDER BY date ASC, score DESC
        """), {
            "from_date": from_date,
            "to_date":   to_date,
            "sv":        self.sv,
        })

        dates_dict: dict = {}
        for r in rows.fetchall():
            d = str(r.date)
            if d not in dates_dict:
                dates_dict[d] = {}
            b, bz = get_tension_band(float(r.score))
            dates_dict[d][r.country_code] = {
                "score":   round(float(r.score), 2),
                "band":    b,
                "band_zh": bz,
            }

        return {"dimension": dimension, "dates": dates_dict}

    async def get_events(
        self,
        country: str | None = None,
        region: str | None = None,
        event_type: str | None = None,
        risk_or_relief: str | None = None,
        date: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> dict:
        """事件列表，含評分分解與新聞來源"""
        # 組建動態 WHERE 條件
        conditions = []
        params: dict = {"limit": limit, "offset": offset}

        if country:
            conditions.append("ec.country_code = :country")
            params["country"] = country
        if region:
            conditions.append("e.region_code = :region")
            params["region"] = region
        if event_type:
            conditions.append("e.event_type = :event_type")
            params["event_type"] = event_type
        if risk_or_relief:
            conditions.append("e.risk_or_relief = :risk_or_relief")
            params["risk_or_relief"] = risk_or_relief
        if date:
            conditions.append("DATE(e.event_time) = :date")
            from datetime import date as date_type
            params["date"] = date_type.fromisoformat(date)

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        # 主查詢：events + event_scores + event_countries（聚合）
        events_sql = text(f"""
            SELECT
                e.id,
                e.event_id,
                e.title,
                e.event_type,
                e.risk_or_relief,
                e.severity,
                e.event_time,
                e.region_code,
                e.source_count,
                e.source_confidence,
                es.final_score,
                es.raw_score,
                es.base_severity,
                es.scope_weight,
                es.geo_sensitivity,
                es.actor_importance,
                es.time_decay,
                ed.military_score,
                ed.political_score,
                ed.economic_score,
                ed.social_score,
                ed.cyber_score,
                (
                    SELECT ARRAY_AGG(ec2.country_code ORDER BY ec2.country_code)
                    FROM event_countries ec2
                    WHERE ec2.event_id = e.id
                ) AS country_codes
            FROM events e
            {"JOIN event_countries ec ON e.id = ec.event_id" if country else ""}
            LEFT JOIN event_scores es ON e.id = es.event_id AND es.scoring_version = :sv
            LEFT JOIN event_dimensions ed ON e.id = ed.event_id
            {where_clause}
            {"" if country else ""}
            ORDER BY COALESCE(es.final_score, 0) DESC, e.event_time DESC
            LIMIT :limit OFFSET :offset
        """)
        params["sv"] = self.sv

        rows = await self.session.execute(events_sql, params)
        events_raw = rows.fetchall()

        if not events_raw:
            return {"total": 0, "events": []}

        # 取各 event 的 news sources（批次）
        event_ids = [r.id for r in events_raw]
        news_rows = await self.session.execute(text("""
            SELECT event_id, source_name, source_url, title, published_at, credibility_score
            FROM news_sources
            WHERE event_id = ANY(:ids)
            ORDER BY event_id, credibility_score DESC NULLS LAST
        """), {"ids": event_ids})
        news_by_event: dict = {}
        for n in news_rows.fetchall():
            news_by_event.setdefault(n.event_id, []).append({
                "source_name": n.source_name,
                "url":         n.source_url,
                "title":       n.title,
                "published_at": str(n.published_at) if n.published_at else None,
                "credibility":  round(float(n.credibility_score), 2) if n.credibility_score else None,
            })

        # 組裝回傳
        events_out = []
        for r in events_raw:
            events_out.append({
                "event_id":         r.event_id,
                "title":            r.title,
                "event_type":       r.event_type,
                "risk_or_relief":   r.risk_or_relief,
                "severity":         round(float(r.severity), 3) if r.severity else None,
                "event_time":       str(r.event_time),
                "region_code":      r.region_code,
                "source_count":     r.source_count,
                "source_confidence":round(float(r.source_confidence), 2) if r.source_confidence else None,
                "final_score":      round(float(r.final_score), 2) if r.final_score else None,
                "score_breakdown": {
                    "base_severity":    round(float(r.base_severity), 3) if r.base_severity else None,
                    "scope_weight":     round(float(r.scope_weight), 3) if r.scope_weight else None,
                    "geo_sensitivity":  round(float(r.geo_sensitivity), 3) if r.geo_sensitivity else None,
                    "actor_importance": round(float(r.actor_importance), 3) if r.actor_importance else None,
                    "time_decay":       round(float(r.time_decay), 3) if r.time_decay else None,
                    "raw_score":        round(float(r.raw_score), 4) if r.raw_score else None,
                } if r.final_score else None,
                "dimensions": {
                    "military":  round(float(r.military_score), 2) if r.military_score else None,
                    "political": round(float(r.political_score), 2) if r.political_score else None,
                    "economic":  round(float(r.economic_score), 2) if r.economic_score else None,
                    "social":    round(float(r.social_score), 2) if r.social_score else None,
                    "cyber":     round(float(r.cyber_score), 2) if r.cyber_score else None,
                } if r.military_score else None,
                "countries":   list(r.country_codes) if r.country_codes else [],
                "news_sources": news_by_event.get(r.id, []),
            })

        return {"total": len(events_out), "events": events_out}

    async def get_event_detail(self, event_id: str) -> dict | None:
        """單一事件完整詳情"""
        row = await self.session.execute(text("""
            SELECT
                e.id, e.event_id, e.title, e.content,
                e.event_type, e.risk_or_relief, e.severity,
                e.event_time, e.region_code,
                e.source_count, e.source_confidence,
                es.final_score, es.raw_score,
                es.base_severity, es.scope_weight,
                es.geo_sensitivity, es.actor_importance,
                es.source_confidence AS es_confidence, es.time_decay,
                ed.military_score, ed.political_score,
                ed.economic_score, ed.social_score, ed.cyber_score,
                ea.summary_zh, ea.summary_en, ea.impact_direction,
                ea.confidence AS ai_confidence, ea.explanation
            FROM events e
            LEFT JOIN event_scores es ON e.id = es.event_id AND es.scoring_version = :sv
            LEFT JOIN event_dimensions ed ON e.id = ed.event_id
            LEFT JOIN event_ai_analysis ea ON e.id = ea.event_id
            WHERE e.event_id = :event_id
        """), {"event_id": event_id, "sv": self.sv})
        r = row.fetchone()
        if not r:
            return None

        # Countries
        c_rows = await self.session.execute(text("""
            SELECT country_code, role FROM event_countries WHERE event_id = :id
        """), {"id": r.id})
        countries = [{"country_code": c.country_code, "role": c.role} for c in c_rows.fetchall()]

        # News
        n_rows = await self.session.execute(text("""
            SELECT source_name, source_url, title, published_at, credibility_score
            FROM news_sources WHERE event_id = :id
            ORDER BY credibility_score DESC NULLS LAST
        """), {"id": r.id})
        news = [{
            "source_name": n.source_name,
            "url":         n.source_url,
            "title":       n.title,
            "published_at": str(n.published_at) if n.published_at else None,
            "credibility":  round(float(n.credibility_score), 2) if n.credibility_score else None,
        } for n in n_rows.fetchall()]

        return {
            "event_id":    r.event_id,
            "title":       r.title,
            "content":     r.content,
            "event_type":  r.event_type,
            "risk_or_relief": r.risk_or_relief,
            "severity":    round(float(r.severity), 3) if r.severity else None,
            "event_time":  str(r.event_time),
            "region_code": r.region_code,
            "source_count": r.source_count,
            "source_confidence": round(float(r.source_confidence), 2) if r.source_confidence else None,
            "final_score": round(float(r.final_score), 2) if r.final_score else None,
            "score_breakdown": {
                "base_severity":    round(float(r.base_severity), 3) if r.base_severity else None,
                "scope_weight":     round(float(r.scope_weight), 3) if r.scope_weight else None,
                "geo_sensitivity":  round(float(r.geo_sensitivity), 3) if r.geo_sensitivity else None,
                "actor_importance": round(float(r.actor_importance), 3) if r.actor_importance else None,
                "time_decay":       round(float(r.time_decay), 3) if r.time_decay else None,
                "raw_score":        round(float(r.raw_score), 4) if r.raw_score else None,
            } if r.final_score else None,
            "dimensions": {
                "military":  round(float(r.military_score), 2) if r.military_score else None,
                "political": round(float(r.political_score), 2) if r.political_score else None,
                "economic":  round(float(r.economic_score), 2) if r.economic_score else None,
                "social":    round(float(r.social_score), 2) if r.social_score else None,
                "cyber":     round(float(r.cyber_score), 2) if r.cyber_score else None,
            } if r.military_score else None,
            "ai_analysis": {
                "summary_zh":       r.summary_zh,
                "summary_en":       r.summary_en,
                "impact_direction": r.impact_direction,
                "confidence":       round(float(r.ai_confidence), 2) if r.ai_confidence else None,
                "explanation":      r.explanation,
            } if r.summary_zh else None,
            "countries":    countries,
            "news_sources": news,
        }

    async def get_country_trend(
        self,
        country_code: str,
        range_str: str = "30d",
    ) -> dict:
        """指定國家的歷史張力趨勢"""
        days = RANGE_DAYS.get(range_str, 30)
        from datetime import datetime, timezone
        today = datetime.now(timezone.utc).date()
        from_date = today - timedelta(days=days - 1)

        rows = await self.session.execute(text("""
            SELECT date, net_tension,
                   military_score, political_score, economic_score,
                   social_score, cyber_score, event_count
            FROM country_tension_daily
            WHERE country_code = :code
              AND date >= :from_date
              AND scoring_version = :sv
            ORDER BY date ASC
        """), {"code": country_code, "from_date": from_date, "sv": self.sv})

        data = []
        for r in rows.fetchall():
            data.append({
                "date":        str(r.date),
                "net_tension": round(float(r.net_tension), 2),
                "military":    round(float(r.military_score), 2),
                "political":   round(float(r.political_score), 2),
                "economic":    round(float(r.economic_score), 2),
                "social":      round(float(r.social_score), 2),
                "cyber":       round(float(r.cyber_score), 2),
                "event_count": r.event_count,
            })

        return {
            "country_code": country_code,
            "range":        range_str,
            "data":         data,
        }

    # ── 內部輔助 ─────────────────────────────────────────────────────────────

    async def _fetch_global(self, date_str: str) -> dict | None:
        from datetime import date as date_type
        d = date_type.fromisoformat(date_str)
        row = await self.session.execute(text("""
            SELECT net_tension, military_score, political_score,
                   economic_score, social_score, cyber_score,
                   ai_summary, computed_at
            FROM global_tension_daily
            WHERE date = :date AND scoring_version = :sv
        """), {"date": d, "sv": self.sv})
        r = row.fetchone()
        if not r:
            return None
        return {
            "net_tension":    r.net_tension,
            "military_score": r.military_score,
            "political_score":r.political_score,
            "economic_score": r.economic_score,
            "social_score":   r.social_score,
            "cyber_score":    r.cyber_score,
            "ai_summary":     r.ai_summary,
            "computed_at":    r.computed_at,
        }
