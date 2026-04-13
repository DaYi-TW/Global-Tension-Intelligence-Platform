"""
Scoring Engine
讀取已正規化事件，計算各層分數並寫入快照表
對應 docs/03-scoring-engine.md
"""

import logging
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from pipeline.scoring.formulas import (
    ROLE_WEIGHTS,
    WORLD_TENSION_WEIGHTS,
    get_actor_importance,
    get_geo_sensitivity,
    get_scope_weight,
    normalize_to_100,
    time_decay,
)

logger = logging.getLogger(__name__)

# 評分視窗：過去 30 天
SCORING_WINDOW_DAYS = 30


class ScoringEngine:

    def __init__(self, session: AsyncSession, scoring_version: str = "v1.0"):
        self.session = session
        self.scoring_version = scoring_version
        self.now = datetime.now(timezone.utc)
        self.target_date = self.now.date()

    async def run(self) -> dict:
        """執行完整評分流程，回傳統計"""
        logger.info(f"ScoringEngine: start for date={self.target_date}, "
                    f"version={self.scoring_version}")

        # Step 1: 計算事件分數
        event_count = await self._score_events()

        # Step 2: 計算國家張力
        country_count = await self._aggregate_countries()

        # Step 3: 計算區域張力
        region_count = await self._aggregate_regions()

        # Step 4: 計算全球張力
        await self._aggregate_global()

        await self.session.commit()

        result = {
            "target_date":     str(self.target_date),
            "scoring_version": self.scoring_version,
            "events_scored":   event_count,
            "countries":       country_count,
            "regions":         region_count,
        }
        logger.info(f"ScoringEngine: done {result}")
        return result

    # ─── Step 1: Event Scores ───────────────────────────────────────────────

    async def _score_events(self) -> int:
        """計算過去 30 天所有事件的 raw_score 和 final_score"""
        since = self.now - timedelta(days=SCORING_WINDOW_DAYS)

        # 取出需要評分的事件（含國家資訊）
        rows = await self.session.execute(text("""
            SELECT
                e.id,
                e.event_id,
                e.event_time,
                e.event_type,
                e.primary_dimension,
                e.risk_or_relief,
                e.severity,
                e.source_confidence,
                e.source_count,
                e.region_code,
                COALESCE(
                    array_agg(ec.country_code ORDER BY ec.role) FILTER (WHERE ec.country_code IS NOT NULL),
                    '{}'
                ) AS country_codes
            FROM events e
            LEFT JOIN event_countries ec ON ec.event_id = e.id
            WHERE e.event_time >= :since
              AND e.needs_review = FALSE
            GROUP BY e.id
            ORDER BY e.event_time DESC
        """), {"since": since})

        events = rows.fetchall()
        if not events:
            logger.info("ScoringEngine: no events in window")
            return 0

        scored = 0
        for ev in events:
            await self._score_one_event(ev)
            scored += 1

        logger.info(f"ScoringEngine: scored {scored} events")
        return scored

    async def _score_one_event(self, ev) -> None:
        country_codes = list(ev.country_codes) if ev.country_codes else []
        event_time = ev.event_time
        if isinstance(event_time, str):
            event_time = datetime.fromisoformat(event_time)
        if event_time.tzinfo is None:
            event_time = event_time.replace(tzinfo=timezone.utc)

        # 計算各因子
        base_severity    = float(ev.severity)
        scope_w          = get_scope_weight(len(country_codes))
        geo_sens         = get_geo_sensitivity(country_codes, ev.region_code)
        actor_imp        = get_actor_importance(country_codes)
        src_conf         = float(ev.source_confidence)
        t_decay          = time_decay(event_time, ev.risk_or_relief, self.now)

        raw_score   = base_severity * scope_w * geo_sens * actor_imp * src_conf * t_decay
        final_score = normalize_to_100(raw_score)

        # UPSERT event_scores
        await self.session.execute(text("""
            INSERT INTO event_scores (
                event_id, scoring_version,
                base_severity, scope_weight, geo_sensitivity,
                actor_importance, source_confidence, time_decay,
                raw_score, final_score, computed_at
            ) VALUES (
                :event_id, :scoring_version,
                :base_severity, :scope_weight, :geo_sensitivity,
                :actor_importance, :source_confidence, :time_decay,
                :raw_score, :final_score, NOW()
            )
            ON CONFLICT (event_id, scoring_version)
            DO UPDATE SET
                base_severity    = EXCLUDED.base_severity,
                scope_weight     = EXCLUDED.scope_weight,
                geo_sensitivity  = EXCLUDED.geo_sensitivity,
                actor_importance = EXCLUDED.actor_importance,
                source_confidence= EXCLUDED.source_confidence,
                time_decay       = EXCLUDED.time_decay,
                raw_score        = EXCLUDED.raw_score,
                final_score      = EXCLUDED.final_score,
                computed_at      = NOW()
        """), {
            "event_id":         ev.id,
            "scoring_version":  self.scoring_version,
            "base_severity":    round(base_severity, 4),
            "scope_weight":     round(scope_w, 4),
            "geo_sensitivity":  round(geo_sens, 4),
            "actor_importance": round(actor_imp, 4),
            "source_confidence":round(src_conf, 4),
            "time_decay":       round(t_decay, 4),
            "raw_score":        round(raw_score, 6),
            "final_score":      final_score,
        })

    # ─── Step 2: Country Tension ────────────────────────────────────────────

    async def _aggregate_countries(self) -> int:
        """聚合所有有事件的國家張力分數"""
        since = self.now - timedelta(days=SCORING_WINDOW_DAYS)

        # 取出每個國家的相關事件與分數
        rows = await self.session.execute(text("""
            SELECT
                ec.country_code,
                ec.role,
                e.risk_or_relief,
                e.primary_dimension,
                es.final_score,
                ed.military_score,
                ed.political_score,
                ed.economic_score,
                ed.social_score,
                ed.cyber_score
            FROM event_countries ec
            JOIN events e ON e.id = ec.event_id
            JOIN event_scores es ON es.event_id = e.id
                AND es.scoring_version = :version
            LEFT JOIN event_dimensions ed ON ed.event_id = e.id
            WHERE e.event_time >= :since
              AND e.needs_review = FALSE
        """), {"since": since, "version": self.scoring_version})

        # 按國家聚合
        country_data: dict[str, dict] = defaultdict(lambda: {
            "risk_total":    0.0,
            "relief_total":  0.0,
            "risk_count":    0,
            "relief_count":  0,
            "dim_scores":    defaultdict(float),
            "event_count":   0,
        })

        for row in rows.fetchall():
            code = row.country_code
            role_w = ROLE_WEIGHTS.get(row.role, 0.6)
            final = float(row.final_score)
            weighted = final * role_w

            d = country_data[code]
            d["event_count"] += 1

            if row.risk_or_relief == "risk":
                d["risk_total"] += weighted
                d["risk_count"] += 1
                # 累積維度分數
                for dim in ["military", "political", "economic", "social", "cyber"]:
                    dim_val = getattr(row, f"{dim}_score", 0) or 0
                    d["dim_scores"][dim] += weighted * float(dim_val)
            else:
                d["relief_total"] += weighted
                d["relief_count"] += 1

        if not country_data:
            return 0

        # 寫入 country_tension_daily
        for country_code, d in country_data.items():
            risk_count   = d["risk_count"]
            relief_count = d["relief_count"]

            # 改用加權平均：平均每筆事件的嚴重度，消除事件數量膨脹效應
            risk_avg   = d["risk_total"]   / risk_count   if risk_count   > 0 else 0.0
            relief_avg = d["relief_total"] / relief_count if relief_count > 0 else 0.0
            net_raw    = risk_avg - 0.7 * relief_avg
            net_tension = normalize_to_100(max(0.0, net_raw), scale=5.0)

            # 維度分數同樣取平均
            dim_scores = d["dim_scores"]
            dims = {
                dim: normalize_to_100(
                    dim_scores.get(dim, 0.0) / risk_count if risk_count > 0 else 0.0,
                    scale=5.0
                )
                for dim in ["military", "political", "economic", "social", "cyber"]
            }

            await self.session.execute(text("""
                INSERT INTO country_tension_daily (
                    country_code, date,
                    risk_score, relief_score, net_tension,
                    military_score, political_score, economic_score,
                    social_score, cyber_score,
                    event_count, scoring_version, computed_at
                ) VALUES (
                    :country_code, :date,
                    :risk_score, :relief_score, :net_tension,
                    :military, :political, :economic, :social, :cyber,
                    :event_count, :scoring_version, NOW()
                )
                ON CONFLICT (country_code, date, scoring_version)
                DO UPDATE SET
                    risk_score      = EXCLUDED.risk_score,
                    relief_score    = EXCLUDED.relief_score,
                    net_tension     = EXCLUDED.net_tension,
                    military_score  = EXCLUDED.military_score,
                    political_score = EXCLUDED.political_score,
                    economic_score  = EXCLUDED.economic_score,
                    social_score    = EXCLUDED.social_score,
                    cyber_score     = EXCLUDED.cyber_score,
                    event_count     = EXCLUDED.event_count,
                    computed_at     = NOW()
            """), {
                "country_code":    country_code,
                "date":            self.target_date,
                "risk_score":      round(d["risk_total"], 2),
                "relief_score":    round(d["relief_total"], 2),
                "net_tension":     net_tension,
                "military":        dims["military"],
                "political":       dims["political"],
                "economic":        dims["economic"],
                "social":          dims["social"],
                "cyber":           dims["cyber"],
                "event_count":     d["event_count"],
                "scoring_version": self.scoring_version,
            })

        logger.info(f"ScoringEngine: aggregated {len(country_data)} countries")
        return len(country_data)

    # ─── Step 3: Region Tension ─────────────────────────────────────────────

    async def _aggregate_regions(self) -> int:
        """等權平均各區域內國家分數"""
        from pipeline.normalization.region_map import COUNTRY_TO_REGION, REGION_CODES

        rows = await self.session.execute(text("""
            SELECT country_code, net_tension,
                   military_score, political_score, economic_score,
                   social_score, cyber_score, event_count
            FROM country_tension_daily
            WHERE date = :date AND scoring_version = :version
        """), {"date": self.target_date, "version": self.scoring_version})

        # 按區域分組
        region_data: dict[str, list] = defaultdict(list)
        for row in rows.fetchall():
            region = COUNTRY_TO_REGION.get(row.country_code)
            if region:
                region_data[region].append(row)

        if not region_data:
            return 0

        for region_code, countries in region_data.items():
            n = len(countries)
            avg = lambda field: round(sum(float(getattr(r, field)) for r in countries) / n, 2)

            net_tension     = avg("net_tension")
            military_score  = avg("military_score")
            political_score = avg("political_score")
            economic_score  = avg("economic_score")
            social_score    = avg("social_score")
            cyber_score     = avg("cyber_score")
            event_count     = sum(r.event_count for r in countries)

            # 前 3 高張力國家
            top3 = sorted(countries, key=lambda r: float(r.net_tension), reverse=True)[:3]
            top_codes = [r.country_code for r in top3]

            await self.session.execute(text("""
                INSERT INTO region_tension_daily (
                    region_code, date,
                    risk_score, relief_score, net_tension,
                    military_score, political_score, economic_score,
                    social_score, cyber_score,
                    top_country_codes, event_count, scoring_version
                ) VALUES (
                    :region_code, :date,
                    0, 0, :net_tension,
                    :military, :political, :economic, :social, :cyber,
                    :top_codes, :event_count, :scoring_version
                )
                ON CONFLICT (region_code, date, scoring_version)
                DO UPDATE SET
                    net_tension     = EXCLUDED.net_tension,
                    military_score  = EXCLUDED.military_score,
                    political_score = EXCLUDED.political_score,
                    economic_score  = EXCLUDED.economic_score,
                    social_score    = EXCLUDED.social_score,
                    cyber_score     = EXCLUDED.cyber_score,
                    top_country_codes = EXCLUDED.top_country_codes,
                    event_count     = EXCLUDED.event_count
            """), {
                "region_code":     region_code,
                "date":            self.target_date,
                "net_tension":     net_tension,
                "military":        military_score,
                "political":       political_score,
                "economic":        economic_score,
                "social":          social_score,
                "cyber":           cyber_score,
                "top_codes":       top_codes,
                "event_count":     event_count,
                "scoring_version": self.scoring_version,
            })

        logger.info(f"ScoringEngine: aggregated {len(region_data)} regions")
        return len(region_data)

    # ─── Step 4: Global Tension ─────────────────────────────────────────────

    async def _aggregate_global(self) -> None:
        """加權合算全球張力"""
        rows = await self.session.execute(text("""
            SELECT military_score, political_score, economic_score,
                   social_score, cyber_score
            FROM region_tension_daily
            WHERE date = :date AND scoring_version = :version
        """), {"date": self.target_date, "version": self.scoring_version})

        all_regions = rows.fetchall()
        if not all_regions:
            return

        n = len(all_regions)
        avg = lambda field: sum(float(getattr(r, field)) for r in all_regions) / n

        military_avg  = avg("military_score")
        political_avg = avg("political_score")
        economic_avg  = avg("economic_score")
        social_avg    = avg("social_score")
        cyber_avg     = avg("cyber_score")

        net_tension = round(
            WORLD_TENSION_WEIGHTS["military"]  * military_avg
            + WORLD_TENSION_WEIGHTS["political"] * political_avg
            + WORLD_TENSION_WEIGHTS["economic"]  * economic_avg
            + WORLD_TENSION_WEIGHTS["social"]    * social_avg
            + WORLD_TENSION_WEIGHTS["cyber"]     * cyber_avg,
            2
        )
        # 全球分數已經是 0-100 的平均，直接 clamp 即可
        net_tension = max(0.0, min(100.0, net_tension))

        # 取 top risk/relief 事件 ID
        top_risk = await self.session.execute(text("""
            SELECT e.id FROM events e
            JOIN event_scores es ON es.event_id = e.id
                AND es.scoring_version = :version
            WHERE e.risk_or_relief = 'risk'
              AND e.event_time >= NOW() - INTERVAL '30 days'
            ORDER BY es.final_score DESC LIMIT 5
        """), {"version": self.scoring_version})
        top_risk_ids = [r[0] for r in top_risk.fetchall()]

        top_relief = await self.session.execute(text("""
            SELECT e.id FROM events e
            JOIN event_scores es ON es.event_id = e.id
                AND es.scoring_version = :version
            WHERE e.risk_or_relief = 'relief'
              AND e.event_time >= NOW() - INTERVAL '30 days'
            ORDER BY es.final_score DESC LIMIT 5
        """), {"version": self.scoring_version})
        top_relief_ids = [r[0] for r in top_relief.fetchall()]

        await self.session.execute(text("""
            INSERT INTO global_tension_daily (
                date, net_tension,
                military_score, political_score, economic_score,
                social_score, cyber_score,
                top_risk_event_ids, top_relief_event_ids,
                scoring_version, computed_at
            ) VALUES (
                :date, :net_tension,
                :military, :political, :economic, :social, :cyber,
                :top_risk_ids, :top_relief_ids,
                :scoring_version, NOW()
            )
            ON CONFLICT (date, scoring_version)
            DO UPDATE SET
                net_tension     = EXCLUDED.net_tension,
                military_score  = EXCLUDED.military_score,
                political_score = EXCLUDED.political_score,
                economic_score  = EXCLUDED.economic_score,
                social_score    = EXCLUDED.social_score,
                cyber_score     = EXCLUDED.cyber_score,
                top_risk_event_ids   = EXCLUDED.top_risk_event_ids,
                top_relief_event_ids = EXCLUDED.top_relief_event_ids,
                computed_at     = NOW()
        """), {
            "date":            self.target_date,
            "net_tension":     net_tension,
            "military":        round(military_avg, 2),
            "political":       round(political_avg, 2),
            "economic":        round(economic_avg, 2),
            "social":          round(social_avg, 2),
            "cyber":           round(cyber_avg, 2),
            "top_risk_ids":    top_risk_ids,
            "top_relief_ids":  top_relief_ids,
            "scoring_version": self.scoring_version,
        })

        logger.info(f"ScoringEngine: global net_tension={net_tension}")
