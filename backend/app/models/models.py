"""
SQLAlchemy Models — 對應 04-database-schema.md 的所有資料表
"""

from datetime import datetime, date
from typing import Optional
from sqlalchemy import (
    BigInteger, Boolean, Column, Date, Float, ForeignKey,
    Integer, Numeric, String, Text, TIMESTAMP, ARRAY,
    UniqueConstraint, Index, CheckConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


class RawEvent(Base):
    """原始資料暫存（不可覆寫）"""
    __tablename__ = "raw_events"

    id              = Column(BigInteger, primary_key=True, autoincrement=True)
    source_type     = Column(String(50), nullable=False)    # 'gdelt' | 'acled' | 'newsapi'
    source_event_id = Column(String(200), nullable=False)
    raw_payload     = Column(JSONB, nullable=False)
    fetched_at      = Column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)
    normalized      = Column(Boolean, nullable=False, default=False)

    __table_args__ = (
        UniqueConstraint("source_type", "source_event_id", name="uq_raw_events_source"),
        Index("idx_raw_events_pending", "normalized", "fetched_at",
              postgresql_where=Column("normalized") == False),
    )


class Event(Base):
    """正規化事件主表"""
    __tablename__ = "events"

    id                = Column(BigInteger, primary_key=True, autoincrement=True)
    event_id          = Column(String(50), nullable=False, unique=True)   # evt_20260407_001
    source_type       = Column(String(50), nullable=False)
    source_event_id   = Column(String(200))
    title             = Column(Text, nullable=False)
    content           = Column(Text)
    event_time        = Column(TIMESTAMP(timezone=True), nullable=False)
    region_code       = Column(String(50))
    event_type        = Column(String(100), nullable=False)
    primary_dimension = Column(String(20), nullable=False)
    risk_or_relief    = Column(String(10), nullable=False)
    severity          = Column(Numeric(4, 3), nullable=False)
    source_count      = Column(Integer, nullable=False, default=1)
    source_confidence = Column(Numeric(4, 3), nullable=False, default=0.5)
    needs_review      = Column(Boolean, nullable=False, default=False)
    ai_analyzed       = Column(Boolean, nullable=False, default=False)
    scoring_version   = Column(String(20), default="v1")
    created_at        = Column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at        = Column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow,
                               onupdate=datetime.utcnow)

    # Relationships
    countries     = relationship("EventCountry", back_populates="event", cascade="all, delete-orphan")
    dimensions    = relationship("EventDimension", back_populates="event", uselist=False,
                                 cascade="all, delete-orphan")
    ai_analysis   = relationship("EventAIAnalysis", back_populates="event", uselist=False,
                                 cascade="all, delete-orphan")
    scores        = relationship("EventScore", back_populates="event", cascade="all, delete-orphan")
    news_sources  = relationship("NewsSource", back_populates="event", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("primary_dimension IN ('military','political','economic','social','cyber')",
                        name="ck_events_primary_dimension"),
        CheckConstraint("risk_or_relief IN ('risk','relief','neutral')",
                        name="ck_events_risk_or_relief"),
        CheckConstraint("severity BETWEEN 0 AND 1", name="ck_events_severity"),
        CheckConstraint("source_confidence BETWEEN 0 AND 1", name="ck_events_source_confidence"),
        Index("idx_events_event_time", "event_time"),
        Index("idx_events_region", "region_code"),
        Index("idx_events_type", "event_type"),
        Index("idx_events_risk_relief", "risk_or_relief"),
        Index("idx_events_ai_pending", "ai_analyzed", "event_time",
              postgresql_where=Column("ai_analyzed") == False),
    )


class EventCountry(Base):
    """事件涉及國家（多對多）"""
    __tablename__ = "event_countries"

    id           = Column(BigInteger, primary_key=True, autoincrement=True)
    event_id     = Column(BigInteger, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    country_code = Column(String(3), nullable=False)    # ISO 3166-1 alpha-3
    role         = Column(String(20), nullable=False)   # initiator | target | affected

    event = relationship("Event", back_populates="countries")

    __table_args__ = (
        UniqueConstraint("event_id", "country_code", name="uq_event_countries"),
        CheckConstraint("role IN ('initiator','target','affected')", name="ck_ec_role"),
        Index("idx_event_countries_event", "event_id"),
        Index("idx_event_countries_country", "country_code"),
    )


class EventDimension(Base):
    """事件各維度影響分數（僅規則引擎寫入，source 永遠為 'rule'）"""
    __tablename__ = "event_dimensions"

    id              = Column(BigInteger, primary_key=True, autoincrement=True)
    event_id        = Column(BigInteger, ForeignKey("events.id", ondelete="CASCADE"),
                             nullable=False, unique=True)
    military_score  = Column(Numeric(5, 4), nullable=False, default=0)
    political_score = Column(Numeric(5, 4), nullable=False, default=0)
    economic_score  = Column(Numeric(5, 4), nullable=False, default=0)
    social_score    = Column(Numeric(5, 4), nullable=False, default=0)
    cyber_score     = Column(Numeric(5, 4), nullable=False, default=0)
    source          = Column(String(20), nullable=False, default="rule")
    computed_at     = Column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)

    event = relationship("Event", back_populates="dimensions")

    __table_args__ = (
        CheckConstraint("source IN ('rule')", name="ck_ed_source"),
    )


class EventAIAnalysis(Base):
    """LLM 分析結果（僅展示用，不影響評分）"""
    __tablename__ = "event_ai_analysis"

    id               = Column(BigInteger, primary_key=True, autoincrement=True)
    event_id         = Column(BigInteger, ForeignKey("events.id", ondelete="CASCADE"),
                              nullable=False, unique=True)
    summary_zh       = Column(Text)
    summary_en       = Column(Text)
    impact_direction = Column(String(10))
    dimensions       = Column(JSONB)        # AI 維度，僅展示用
    confidence       = Column(Numeric(4, 3))
    explanation      = Column(Text)
    related_tags     = Column(ARRAY(Text))
    model_version    = Column(String(50))
    prompt_version   = Column(String(20))
    raw_response     = Column(JSONB)
    created_at       = Column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)

    event = relationship("Event", back_populates="ai_analysis")

    __table_args__ = (
        CheckConstraint("impact_direction IN ('risk','relief','neutral')",
                        name="ck_eaia_impact"),
    )


class EventScore(Base):
    """事件計算分數明細（支援重算）"""
    __tablename__ = "event_scores"

    id                = Column(BigInteger, primary_key=True, autoincrement=True)
    event_id          = Column(BigInteger, ForeignKey("events.id", ondelete="CASCADE"),
                               nullable=False)
    scoring_version   = Column(String(20), nullable=False)
    base_severity     = Column(Numeric(5, 4))
    scope_weight      = Column(Numeric(5, 4))
    geo_sensitivity   = Column(Numeric(5, 4))
    actor_importance  = Column(Numeric(5, 4))
    source_confidence = Column(Numeric(5, 4))
    time_decay        = Column(Numeric(5, 4))
    raw_score         = Column(Numeric(10, 6), nullable=False)   # 所有因子連乘，未正規化
    final_score       = Column(Numeric(6, 2), nullable=False)    # normalize_to_100(raw_score), 0–100
    computed_at       = Column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)

    event = relationship("Event", back_populates="scores")

    __table_args__ = (
        UniqueConstraint("event_id", "scoring_version", name="uq_event_scores_version"),
        Index("idx_event_scores_event", "event_id"),
        Index("idx_event_scores_version", "scoring_version", "computed_at"),
    )


class CountryTensionDaily(Base):
    """每日國家緊張度快照"""
    __tablename__ = "country_tension_daily"

    id              = Column(BigInteger, primary_key=True, autoincrement=True)
    country_code    = Column(String(3), nullable=False)    # ISO 3166-1 alpha-3
    date            = Column(Date, nullable=False)
    risk_score      = Column(Numeric(8, 2), nullable=False, default=0)
    relief_score    = Column(Numeric(8, 2), nullable=False, default=0)
    net_tension     = Column(Numeric(5, 2), nullable=False)
    military_score  = Column(Numeric(5, 2), nullable=False, default=0)
    political_score = Column(Numeric(5, 2), nullable=False, default=0)
    economic_score  = Column(Numeric(5, 2), nullable=False, default=0)
    social_score    = Column(Numeric(5, 2), nullable=False, default=0)
    cyber_score     = Column(Numeric(5, 2), nullable=False, default=0)
    event_count     = Column(Integer, nullable=False, default=0)
    scoring_version = Column(String(20), nullable=False, default="v1")
    computed_at     = Column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("country_code", "date", "scoring_version", name="uq_ctd"),
        CheckConstraint("net_tension BETWEEN 0 AND 100", name="ck_ctd_net_tension"),
        Index("idx_ctd_date", "date"),
        Index("idx_ctd_country_date", "country_code", "date"),
        Index("idx_ctd_net_tension", "date", "net_tension"),
    )


class RegionTensionDaily(Base):
    """每日區域緊張度快照"""
    __tablename__ = "region_tension_daily"

    id                = Column(BigInteger, primary_key=True, autoincrement=True)
    region_code       = Column(String(50), nullable=False)
    date              = Column(Date, nullable=False)
    risk_score        = Column(Numeric(8, 2), nullable=False, default=0)
    relief_score      = Column(Numeric(8, 2), nullable=False, default=0)
    net_tension       = Column(Numeric(5, 2), nullable=False)
    military_score    = Column(Numeric(5, 2), nullable=False, default=0)
    political_score   = Column(Numeric(5, 2), nullable=False, default=0)
    economic_score    = Column(Numeric(5, 2), nullable=False, default=0)
    social_score      = Column(Numeric(5, 2), nullable=False, default=0)
    cyber_score       = Column(Numeric(5, 2), nullable=False, default=0)
    top_country_codes = Column(ARRAY(Text), nullable=False, default=list)
    event_count       = Column(Integer, nullable=False, default=0)
    scoring_version   = Column(String(20), nullable=False, default="v1")

    __table_args__ = (
        UniqueConstraint("region_code", "date", "scoring_version", name="uq_rtd"),
        CheckConstraint("net_tension BETWEEN 0 AND 100", name="ck_rtd_net_tension"),
        Index("idx_rtd_date", "date"),
        Index("idx_rtd_region_date", "region_code", "date"),
    )


class GlobalTensionDaily(Base):
    """每日全球緊張度快照"""
    __tablename__ = "global_tension_daily"

    id                   = Column(BigInteger, primary_key=True, autoincrement=True)
    date                 = Column(Date, nullable=False)
    risk_score           = Column(Numeric(8, 2), nullable=False, default=0)
    relief_score         = Column(Numeric(8, 2), nullable=False, default=0)
    net_tension          = Column(Numeric(5, 2), nullable=False)
    military_score       = Column(Numeric(5, 2), nullable=False, default=0)
    political_score      = Column(Numeric(5, 2), nullable=False, default=0)
    economic_score       = Column(Numeric(5, 2), nullable=False, default=0)
    social_score         = Column(Numeric(5, 2), nullable=False, default=0)
    cyber_score          = Column(Numeric(5, 2), nullable=False, default=0)
    top_risk_event_ids   = Column(ARRAY(BigInteger), nullable=False, default=list)
    top_relief_event_ids = Column(ARRAY(BigInteger), nullable=False, default=list)
    ai_summary           = Column(Text)     # AI 每日摘要，可為 null
    scoring_version      = Column(String(20), nullable=False, default="v1")
    computed_at          = Column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("date", "scoring_version", name="uq_gtd"),
        CheckConstraint("net_tension BETWEEN 0 AND 100", name="ck_gtd_net_tension"),
        Index("idx_gtd_date", "date"),
    )


class NewsSource(Base):
    """新聞來源（事件詳情頁展示用）"""
    __tablename__ = "news_sources"

    id                = Column(BigInteger, primary_key=True, autoincrement=True)
    event_id          = Column(BigInteger, ForeignKey("events.id", ondelete="CASCADE"),
                               nullable=False)
    source_name       = Column(String(200))
    source_url        = Column(Text)
    title             = Column(Text)
    published_at      = Column(TIMESTAMP(timezone=True))
    language          = Column(String(2))
    credibility_score = Column(Numeric(4, 3), default=0.5)

    event = relationship("Event", back_populates="news_sources")

    __table_args__ = (
        Index("idx_news_sources_event", "event_id"),
    )


class IngestError(Base):
    """資料抓取錯誤記錄"""
    __tablename__ = "ingest_errors"

    id           = Column(BigInteger, primary_key=True, autoincrement=True)
    source_type  = Column(String(50), nullable=False)
    error_type   = Column(String(100), nullable=False)   # timeout | http_4xx | schema_mismatch | rate_limit
    error_detail = Column(Text)
    raw_data     = Column(JSONB)
    retry_count  = Column(Integer, nullable=False, default=0)
    last_retry_at = Column(TIMESTAMP(timezone=True))
    occurred_at  = Column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)
    resolved     = Column(Boolean, nullable=False, default=False)

    __table_args__ = (
        Index("idx_ingest_errors_unresolved", "occurred_at",
              postgresql_where=Column("resolved") == False),
    )
