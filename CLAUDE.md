# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Global Tension Intelligence Platform（全球局勢緊張度分析平台）** — a platform that ingests global conflict/news events and converts them into quantifiable, visualizable, explainable tension scores at the country, regional, and global level. The core concept is a 0–100 "world tension score" inspired by strategy game tension mechanics, but applied to real geopolitical analysis.

This repository currently contains `proposal.md` (the full product/system proposal in Traditional Chinese). Implementation has not yet started.

---

## Planned Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React or Vue + ECharts + Mapbox/Leaflet + Tailwind/Bootstrap |
| Backend API | Python / FastAPI |
| Gateway | Nginx |
| Primary DB | PostgreSQL |
| Cache | Redis |
| Search (optional) | Elasticsearch / OpenSearch |
| AI/LLM | For summarization and classification assistance |

---

## System Architecture

```
Frontend (React/Vue)
    ↓
Nginx (API Gateway / Reverse Proxy)
    ↓
FastAPI Backend
    ↓
├── Data Ingestion Service      ← fetches from GDELT, ACLED, news APIs
├── Event Normalization Service ← unifies source formats into standard schema
├── AI Analysis Service         ← LLM summaries, classification, impact analysis
├── Tension Scoring Engine      ← rule-based scoring (NOT LLM-driven)
├── Query API Service           ← serves dashboard, events, country, region data
└── Scheduler / Worker          ← background: fetch → normalize → score → cache
```

**Key architectural principle**: Scores are driven by a **deterministic rule engine**, not by LLM. AI is a supplementary layer for summarization and semantic enrichment only.

---

## Data Pipeline Flow

1. **Ingest** — scheduled fetch from GDELT (broad monitoring), ACLED (high-confidence conflict), news APIs (full text)
2. **Normalize** — transform to unified event schema (see below)
3. **AI Enrichment** — LLM produces `summary_zh`, `impact_direction`, `dimensions`, `confidence`, `explanation`
4. **Score** — rule engine computes Event Score → Country Tension → Regional Tension → Global Tension
5. **Persist** — write to PostgreSQL; update Redis cache
6. **Serve** — Frontend reads from Query API

### Normalized Event Schema

```json
{
  "event_id": "evt_20260407_001",
  "title": "...",
  "event_time": "2026-04-07T08:00:00Z",
  "country_codes": ["IRN", "ISR"],
  "region": "Middle East",
  "event_type": "military_strike",
  "risk_or_relief": "risk",
  "severity": 0.88,
  "actors": ["Iran", "Israel"],
  "source_count": 12,
  "source_confidence": 0.91
}
```

---

## Scoring Model

### Net Tension Formula

```
Net Tension = Risk Score - 0.7 × Relief Score
```

The 0.7 discount on relief reflects that bad news amplifies faster than good news in reality.

### Event Score Formula

```
Event Score = Base Severity × Scope Weight × Geo Sensitivity × Actor Importance × Source Confidence × Time Decay
```

- **Geo Sensitivity** multiplier applies to: Taiwan Strait, South China Sea, Ukraine border, Middle East, Strait of Hormuz, Red Sea, Korean Peninsula
- **Time Decay**: risk events decay over 7–14 days; relief events decay in 2–3 days

### World Tension Dimension Weights

```
World Tension = 0.35×Military + 0.20×Political + 0.15×Social + 0.20×Economic + 0.10×Cyber
```

### Tension Score Bands

| Range | Label |
|---|---|
| 0–19 | 平穩 (Stable) |
| 20–39 | 關注 (Watch) |
| 40–59 | 升溫 (Elevated) |
| 60–79 | 高壓 (High) |
| 80–100 | 危機 (Crisis) |

---

## Database Schema (Core Tables)

- **`events`** — normalized event master record
- **`event_countries`** — many-to-many: event ↔ country with role (initiator/target/affected)
- **`event_dimensions`** — per-event scores: military, political, economic, social, cyber
- **`event_ai_analysis`** — LLM output: summary_zh, summary_en, impact_direction, confidence, explanation
- **`country_tension_daily`** — daily snapshot per country with all sub-dimension scores
- **`region_tension_daily`** — daily snapshot per region
- **`global_tension_daily`** — daily global snapshot with summary
- **`news_sources`** — raw news links associated with events

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/dashboard/overview` | Homepage data: global tension, 7-day trend, top countries/regions, daily summary |
| GET | `/api/tension/global/trend?range=30d` | Global tension time series |
| GET | `/api/tension/regions` | Region tension rankings |
| GET | `/api/tension/countries` | Country tension rankings (filterable by region, date) |
| GET | `/api/events` | Event list (filter: country, region, type, risk_or_relief, dates, keyword) |
| GET | `/api/events/{event_id}` | Event detail |
| GET | `/api/countries/{country_code}` | Country detail page data |
| GET | `/api/regions/{region_code}` | Region detail page data |
| GET | `/api/map/heat` | Map heatmap data |

---

## Development Phases

- **Phase 1 (MVP)**: Data ingestion → normalization → scoring engine → Dashboard + map + event list + country/region ranking + AI daily summary
- **Phase 2**: Event detail page, country/region analysis pages, multi-source fusion, search
- **Phase 3**: Scenario simulation, financial market correlation, Taiwan-perspective mode, alerts, user-tracked countries

---

## Non-Functional Requirements

- Dashboard API response target: < 2s; other query pages: < 3s
- Background job failures must be retryable; single data-source failure must not take down the platform
- Scoring engine must support full recalculation (idempotent)
- Every tension score must be traceable to its contributing events (explainability)
- Scoring rules should be versioned
