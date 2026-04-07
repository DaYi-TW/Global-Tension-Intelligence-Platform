"""
API Response Schemas
對應 docs/05-api-spec.md
"""

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel


# ── 共用 ────────────────────────────────────────────────────────────────────

class TensionBand(BaseModel):
    score: float
    band: str       # "Stable" | "Watch" | "Elevated" | "High" | "Crisis"
    band_zh: str    # "平穩" | "關注" | "升溫" | "高壓" | "危機"


class DimensionScores(BaseModel):
    military: float
    political: float
    economic: float
    social: float
    cyber: float


# ── Dashboard Overview ──────────────────────────────────────────────────────

class FastestRisingCountry(BaseModel):
    country_code: str
    net_tension: float
    delta: float
    band: str
    band_zh: str


class TopCountry(BaseModel):
    country_code: str
    net_tension: float
    band: str
    band_zh: str
    delta: Optional[float] = None


class TopRegion(BaseModel):
    region_code: str
    net_tension: float
    band: str
    band_zh: str
    top_country_codes: list[str]


class DashboardOverviewResponse(BaseModel):
    date: str                               # YYYY-MM-DD
    global_tension: float                   # 0–100
    global_band: str
    global_band_zh: str
    global_delta: Optional[float]           # 較昨日變化，可為 null
    dimensions: DimensionScores
    trend_7d: list[float]                   # 7 個數字，最新在最後
    top_countries: list[TopCountry]         # 前 5 高張力國家
    top_regions: list[TopRegion]            # 全部 9 個區域排行
    fastest_rising_countries: list[FastestRisingCountry]
    ai_daily_summary: Optional[str]         # AI 摘要，可為 null
    scoring_version: str
    last_updated: str                       # ISO 8601


# ── Global Trend ────────────────────────────────────────────────────────────

class TrendPoint(BaseModel):
    date: str
    net_tension: float
    military: float
    political: float
    economic: float
    social: float
    cyber: float


class GlobalTrendResponse(BaseModel):
    range: str                  # "7d" | "30d" | "90d" | "1y"
    data: list[TrendPoint]


# ── Regions ─────────────────────────────────────────────────────────────────

class RegionDetail(BaseModel):
    region_code: str
    net_tension: float
    band: str
    band_zh: str
    military: float
    political: float
    economic: float
    social: float
    cyber: float
    top_country_codes: list[str]
    event_count: int


class RegionsResponse(BaseModel):
    date: str
    scoring_version: str
    regions: list[RegionDetail]


# ── Countries ────────────────────────────────────────────────────────────────

class CountryItem(BaseModel):
    country_code: str
    net_tension: float
    band: str
    band_zh: str
    military: float
    political: float
    economic: float
    social: float
    cyber: float
    event_count: int
    delta: Optional[float] = None


class CountriesResponse(BaseModel):
    date: str
    scoring_version: str
    total: int
    countries: list[CountryItem]


# ── Map Heat ────────────────────────────────────────────────────────────────

class CountryHeat(BaseModel):
    country_code: str
    score: float
    band: str
    band_zh: str


class MapHeatResponse(BaseModel):
    date: str
    dimension: str
    scoring_version: str
    countries: list[CountryHeat]


class MapHeatRangeResponse(BaseModel):
    dimension: str
    dates: dict[str, dict[str, dict]]   # { "YYYY-MM-DD": { "ISO3": { score, band, band_zh } } }
