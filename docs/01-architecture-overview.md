# 01 — 系統整體架構

## 1.1 設計哲學

| 原則 | 說明 |
|---|---|
| **確定性優先** | 評分引擎純規則驅動，相同輸入永遠產出相同結果，保障可審計性與可信度 |
| **事件為中心** | 系統一切衍生自 `event`，每個分數都可追溯回原始事件，完整可解釋 |
| **原始資料不可變** | 抓取的 raw payload 永久保留，正規化與評分對副本操作，支援全量重算 |
| **預計算 + 快取架構** | Query API 不做即時運算，所有分數由 Worker 預計算後寫入 DB + Redis |
| **AI 輔助、規則主導** | LLM 僅做摘要與語意補強，數字分數完全由規則引擎控制 |

---

## 1.2 整體架構圖

```
┌─────────────────────────────────────────────────────────────────┐
│                        使用者瀏覽器                                │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS
┌────────────────────────────▼────────────────────────────────────┐
│                     Nginx (Reverse Proxy)                         │
│         /api/*  →  FastAPI        /*  →  React Static Files      │
└────────┬────────────────────────────────────────────────────────┘
         │
┌────────▼────────────────────────────────────────────────────────┐
│                  FastAPI Application Layer                         │
│  ┌────────────────────┐  ┌──────────────────┐  ┌─────────────┐  │
│  │  Query API Router  │  │ Background Worker│  │ Admin Router│  │
│  └──────────┬─────────┘  └────────┬─────────┘  └─────────────┘  │
└─────────────┼───────────────────  ┼────────────────────────────┘
              │                     │
     ┌────────▼────────┐   ┌────────▼──────────────────────────┐
     │  Redis Cache    │   │         Pipeline Services          │
     │                 │   │                                    │
     │  dashboard:*    │   │  1. Data Ingestion Service         │
     │  tension:*      │   │     GDELT / ACLED / News APIs      │
     │  event:*        │   │                                    │
     │  country:*      │   │  2. Event Normalization Service    │
     │  map:heat       │   │     Dedup / Schema mapping         │
     └─────────────────┘   │                                    │
                           │  3. AI Analysis Service            │
     ┌───────────────────┐ │     LLM: summary / classify        │
     │    PostgreSQL      │ │                                    │
     │                   │ │  4. Tension Scoring Engine         │
     │  raw_events        │ │     Rule-based, deterministic      │
     │  events            │ │                                    │
     │  event_countries   │ │  5. Aggregation & Cache Writer    │
     │  event_dimensions  │ │     Country → Region → Global     │
     │  event_ai_analysis │ │                                    │
     │  event_scores      │ └────────────────────────────────────┘
     │  country_tension_* │
     │  region_tension_*  │
     │  global_tension_*  │
     │  news_sources      │
     └───────────────────┘
```

---

## 1.3 模組職責一覽

| 模組 | 技術 | 職責 |
|---|---|---|
| **Frontend** | React + ECharts + Mapbox + Tailwind | Dashboard、地圖、事件列表、國家/區域頁 |
| **Nginx** | Nginx 1.25+ | Reverse proxy、靜態檔案服務、SSL termination |
| **FastAPI** | Python 3.11 + FastAPI | REST API、request validation、回應快取讀取 |
| **Data Ingestion** | Python + httpx | 定時抓取 GDELT、ACLED、NewsAPI |
| **Normalization** | Python | 統一事件格式、去重、國家代碼標準化 |
| **AI Analysis** | Python + LLM SDK | 摘要、利空/利多判斷、維度分類 |
| **Scoring Engine** | Python（純規則） | 事件分數 → 國家 → 區域 → 全球張力分數 |
| **Scheduler** | Celery + Celery Beat | 排程任務、重試、失敗告警 |
| **PostgreSQL** | PostgreSQL 15 | 主要持久化儲存 |
| **Redis** | Redis 7 | API 回應快取 + Celery Message Broker |

---

## 1.4 資料流向總覽

```
外部來源（GDELT / ACLED / NewsAPI）
    ↓  [每 15 分鐘 ~ 每小時]
Data Ingestion Service
    ↓  寫入 raw_events（不可變）
Event Normalization Service
    ↓  寫入 events / event_countries / news_sources
AI Analysis Service
    ↓  寫入 event_ai_analysis / event_dimensions（輔助）
Tension Scoring Engine
    ↓  寫入 event_scores / country_tension_daily / region_tension_daily / global_tension_daily
Cache Writer
    ↓  更新 Redis（dashboard / tension / map key）
Query API
    ↓  Frontend 讀取
```

---

## 1.5 技術選型理由

| 選擇 | 理由 |
|---|---|
| FastAPI | 高效能、原生 async、自動 OpenAPI 文件、Pydantic 驗證 |
| PostgreSQL | JSONB 支援（raw payload）、視窗函數（趨勢計算）、可靠的 ACID |
| Redis | 快取 + Celery broker 一體，降低基礎設施複雜度 |
| Celery | 成熟的 Python 任務隊列，支援重試、排程、監控（Flower） |
| React + ECharts | ECharts 對時序圖/熱力圖的原生支援優秀，適合此場景 |
| Mapbox/Leaflet | 世界地圖熱區視覺化需求 |

---

*文件版本：v1.0 | 2026-04-07*
