# 04 — 資料庫 Schema

## 4.1 設計原則

- `raw_events`：原始資料永久保留，不可覆寫
- `events`：正規化後的事件主檔，為系統核心
- 每日快照表（`country/region/global_tension_daily`）支援趨勢查詢
- 所有分數計算結果附帶 `scoring_version`，支援全量重算與版本並存
- 時間欄位統一使用 `TIMESTAMPTZ`（UTC）
- **國家代碼**：全平台統一使用 **ISO 3166-1 alpha-3**（三位字母）
- **區域代碼**：使用 `02-data-pipeline.md §2.4` 定義的 9 個標準代碼

---

## 4.2 完整 DDL

### raw_events — 原始資料暫存（不可覆寫）

```sql
CREATE TABLE raw_events (
    id              BIGSERIAL PRIMARY KEY,
    source_type     VARCHAR(50)  NOT NULL,        -- 'gdelt' | 'acled' | 'newsapi'
    source_event_id VARCHAR(200) NOT NULL,
    raw_payload     JSONB        NOT NULL,         -- 完整原始資料，永不修改
    fetched_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    normalized      BOOLEAN      NOT NULL DEFAULT FALSE,
    CONSTRAINT uq_raw_events_source UNIQUE (source_type, source_event_id)
);

CREATE INDEX idx_raw_events_pending ON raw_events (normalized, fetched_at)
    WHERE normalized = FALSE;
```

---

### events — 正規化事件主表

```sql
CREATE TABLE events (
    id                BIGSERIAL    PRIMARY KEY,
    event_id          VARCHAR(50)  NOT NULL UNIQUE,   -- evt_20260407_001
    source_type       VARCHAR(50)  NOT NULL,
    source_event_id   VARCHAR(200),
    title             TEXT         NOT NULL,
    content           TEXT,
    event_time        TIMESTAMPTZ  NOT NULL,           -- 統一 UTC，欄位名稱全平台一致
    region_code       VARCHAR(50),                     -- 參見 02-data-pipeline §2.4 區域代碼表
    event_type        VARCHAR(100) NOT NULL,
    primary_dimension VARCHAR(20)  NOT NULL            -- 此事件的主要影響維度
                          CHECK (primary_dimension IN ('military','political','economic','social','cyber')),
    risk_or_relief    VARCHAR(10)  NOT NULL
                          CHECK (risk_or_relief IN ('risk', 'relief', 'neutral')),
    severity          NUMERIC(4,3) NOT NULL
                          CHECK (severity BETWEEN 0 AND 1),
    source_count      INTEGER      NOT NULL DEFAULT 1, -- 跨來源去重後的佐證來源數
    source_confidence NUMERIC(4,3) NOT NULL DEFAULT 0.5
                          CHECK (source_confidence BETWEEN 0 AND 1),
    needs_review      BOOLEAN      NOT NULL DEFAULT FALSE,  -- 國家代碼無法解析等
    ai_analyzed       BOOLEAN      NOT NULL DEFAULT FALSE,
    scoring_version   VARCHAR(20)  DEFAULT 'v1',
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_events_event_time    ON events (event_time DESC);
CREATE INDEX idx_events_region        ON events (region_code);
CREATE INDEX idx_events_type          ON events (event_type);
CREATE INDEX idx_events_risk_relief   ON events (risk_or_relief);
CREATE INDEX idx_events_ai_pending    ON events (ai_analyzed, event_time)
    WHERE ai_analyzed = FALSE;
```

---

### event_countries — 事件涉及國家（多對多）

```sql
-- 每個事件中，一個國家只能有一個角色（UNIQUE 約束保障）
CREATE TABLE event_countries (
    id           BIGSERIAL   PRIMARY KEY,
    event_id     BIGINT      NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    country_code CHAR(3)     NOT NULL,    -- ISO 3166-1 alpha-3，全平台統一標準
    role         VARCHAR(20) NOT NULL
                     CHECK (role IN ('initiator', 'target', 'affected')),
    CONSTRAINT uq_event_countries UNIQUE (event_id, country_code)  -- C-2: 一個國家 = 一個角色
);

CREATE INDEX idx_event_countries_event   ON event_countries (event_id);
CREATE INDEX idx_event_countries_country ON event_countries (country_code);
```

---

### event_dimensions — 事件各維度影響分數（僅規則引擎寫入）

```sql
-- 重要：此表只由規則引擎（Normalization Service）寫入，source 永遠為 'rule'
-- AI Analysis Service 的維度輸出寫入 event_ai_analysis，不寫入此表
-- 評分引擎只讀此表進行計算
CREATE TABLE event_dimensions (
    id               BIGSERIAL    PRIMARY KEY,
    event_id         BIGINT       NOT NULL UNIQUE REFERENCES events(id) ON DELETE CASCADE,
    military_score   NUMERIC(5,4) NOT NULL DEFAULT 0
                         CHECK (military_score BETWEEN 0 AND 1),
    political_score  NUMERIC(5,4) NOT NULL DEFAULT 0
                         CHECK (political_score BETWEEN 0 AND 1),
    economic_score   NUMERIC(5,4) NOT NULL DEFAULT 0
                         CHECK (economic_score BETWEEN 0 AND 1),
    social_score     NUMERIC(5,4) NOT NULL DEFAULT 0
                         CHECK (social_score BETWEEN 0 AND 1),
    cyber_score      NUMERIC(5,4) NOT NULL DEFAULT 0
                         CHECK (cyber_score BETWEEN 0 AND 1),
    source           VARCHAR(20)  NOT NULL DEFAULT 'rule'
                         CHECK (source IN ('rule')),   -- 只允許 'rule'，AI 維度不在此表
    computed_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
```

---

### event_ai_analysis — LLM 分析結果（僅展示用，不影響評分）

```sql
-- 此表的 dimensions JSON 欄位為 AI 輸出，僅用於前端展示與審計
-- 不參與任何評分計算（scoring engine 不讀此表的維度資料）
CREATE TABLE event_ai_analysis (
    id               BIGSERIAL    PRIMARY KEY,
    event_id         BIGINT       NOT NULL UNIQUE REFERENCES events(id) ON DELETE CASCADE,
    summary_zh       TEXT,                    -- 繁體中文摘要（100 字以內）
    summary_en       TEXT,                    -- 英文摘要
    impact_direction VARCHAR(10)
                         CHECK (impact_direction IN ('risk', 'relief', 'neutral')),
    dimensions       JSONB,                   -- AI 判斷的各維度相關性（0-1），僅展示用
    confidence       NUMERIC(4,3)
                         CHECK (confidence BETWEEN 0 AND 1),
    explanation      TEXT,                    -- AI 對分類的說明
    related_tags     TEXT[],                  -- 標籤陣列（台海、能源、核武 etc.）
    model_version    VARCHAR(50),             -- e.g., 'claude-3-7-sonnet-20250219'
    prompt_version   VARCHAR(20),             -- e.g., 'v1.2'
    raw_response     JSONB,                   -- LLM 原始回應（除錯用）
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
```

---

### event_scores — 事件計算分數明細（支援重算）

```sql
CREATE TABLE event_scores (
    id                BIGSERIAL    PRIMARY KEY,
    event_id          BIGINT       NOT NULL REFERENCES events(id) ON DELETE CASCADE,  -- 明確 FK
    scoring_version   VARCHAR(20)  NOT NULL,
    base_severity     NUMERIC(5,4),
    scope_weight      NUMERIC(5,4),
    geo_sensitivity   NUMERIC(5,4),
    actor_importance  NUMERIC(5,4),
    source_confidence NUMERIC(5,4),
    time_decay        NUMERIC(5,4),
    raw_score         NUMERIC(10,6) NOT NULL,  -- 所有因子連乘的原始結果（未正規化）
    final_score       NUMERIC(6,2)  NOT NULL,  -- normalize_to_100(raw_score)，範圍 0–100
    computed_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_event_scores_version UNIQUE (event_id, scoring_version)
);

CREATE INDEX idx_event_scores_event   ON event_scores (event_id);
CREATE INDEX idx_event_scores_version ON event_scores (scoring_version, computed_at DESC);
```

---

### country_tension_daily — 每日國家緊張度快照

```sql
CREATE TABLE country_tension_daily (
    id               BIGSERIAL    PRIMARY KEY,
    country_code     CHAR(3)      NOT NULL,    -- ISO 3166-1 alpha-3
    date             DATE         NOT NULL,
    risk_score       NUMERIC(8,2) NOT NULL DEFAULT 0,
    relief_score     NUMERIC(8,2) NOT NULL DEFAULT 0,
    net_tension      NUMERIC(5,2) NOT NULL
                         CHECK (net_tension BETWEEN 0 AND 100),
    military_score   NUMERIC(5,2) NOT NULL DEFAULT 0,
    political_score  NUMERIC(5,2) NOT NULL DEFAULT 0,
    economic_score   NUMERIC(5,2) NOT NULL DEFAULT 0,
    social_score     NUMERIC(5,2) NOT NULL DEFAULT 0,
    cyber_score      NUMERIC(5,2) NOT NULL DEFAULT 0,
    event_count      INTEGER      NOT NULL DEFAULT 0,
    scoring_version  VARCHAR(20)  NOT NULL DEFAULT 'v1',
    computed_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_ctd UNIQUE (country_code, date, scoring_version)  -- I-4: 含版本號
);

CREATE INDEX idx_ctd_date         ON country_tension_daily (date DESC);
CREATE INDEX idx_ctd_country_date ON country_tension_daily (country_code, date DESC);
CREATE INDEX idx_ctd_net_tension  ON country_tension_daily (date DESC, net_tension DESC);
```

---

### region_tension_daily — 每日區域緊張度快照

```sql
CREATE TABLE region_tension_daily (
    id                BIGSERIAL    PRIMARY KEY,
    region_code       VARCHAR(50)  NOT NULL,    -- 參見 02-data-pipeline §2.4 區域代碼表
    date              DATE         NOT NULL,
    risk_score        NUMERIC(8,2) NOT NULL DEFAULT 0,
    relief_score      NUMERIC(8,2) NOT NULL DEFAULT 0,
    net_tension       NUMERIC(5,2) NOT NULL
                          CHECK (net_tension BETWEEN 0 AND 100),
    military_score    NUMERIC(5,2) NOT NULL DEFAULT 0,
    political_score   NUMERIC(5,2) NOT NULL DEFAULT 0,
    economic_score    NUMERIC(5,2) NOT NULL DEFAULT 0,
    social_score      NUMERIC(5,2) NOT NULL DEFAULT 0,
    cyber_score       NUMERIC(5,2) NOT NULL DEFAULT 0,
    top_country_codes TEXT[]       NOT NULL DEFAULT '{}',   -- 前 3 高張力國家（ISO alpha-3）
    event_count       INTEGER      NOT NULL DEFAULT 0,
    scoring_version   VARCHAR(20)  NOT NULL DEFAULT 'v1',
    CONSTRAINT uq_rtd UNIQUE (region_code, date, scoring_version)  -- I-4: 含版本號
);

CREATE INDEX idx_rtd_date        ON region_tension_daily (date DESC);
CREATE INDEX idx_rtd_region_date ON region_tension_daily (region_code, date DESC);
```

---

### global_tension_daily — 每日全球緊張度快照

```sql
CREATE TABLE global_tension_daily (
    id                    BIGSERIAL    PRIMARY KEY,
    date                  DATE         NOT NULL,
    risk_score            NUMERIC(8,2) NOT NULL DEFAULT 0,
    relief_score          NUMERIC(8,2) NOT NULL DEFAULT 0,
    net_tension           NUMERIC(5,2) NOT NULL
                              CHECK (net_tension BETWEEN 0 AND 100),
    military_score        NUMERIC(5,2) NOT NULL DEFAULT 0,
    political_score       NUMERIC(5,2) NOT NULL DEFAULT 0,
    economic_score        NUMERIC(5,2) NOT NULL DEFAULT 0,
    social_score          NUMERIC(5,2) NOT NULL DEFAULT 0,
    cyber_score           NUMERIC(5,2) NOT NULL DEFAULT 0,
    top_risk_event_ids    BIGINT[]     NOT NULL DEFAULT '{}',
    top_relief_event_ids  BIGINT[]     NOT NULL DEFAULT '{}',
    ai_summary            TEXT,                              -- AI 每日摘要文字（可為 null）
    scoring_version       VARCHAR(20)  NOT NULL DEFAULT 'v1',
    computed_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_gtd UNIQUE (date, scoring_version)       -- I-4: 含版本號
);

CREATE INDEX idx_gtd_date ON global_tension_daily (date DESC);
```

---

### news_sources — 新聞來源（事件詳情頁展示用）

```sql
-- 儲存各事件關聯的原始新聞連結，供事件詳情頁展示來源
-- events.source_count 是此表 per-event 列數的非正規化計數（去重合併時累加）
CREATE TABLE news_sources (
    id                BIGSERIAL    PRIMARY KEY,
    event_id          BIGINT       NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    source_name       VARCHAR(200),
    source_url        TEXT,
    title             TEXT,
    published_at      TIMESTAMPTZ,
    language          CHAR(2),
    credibility_score NUMERIC(4,3) DEFAULT 0.5
                          CHECK (credibility_score BETWEEN 0 AND 1)
);

CREATE INDEX idx_news_sources_event ON news_sources (event_id);
```

---

### ingest_errors — 資料抓取錯誤記錄

```sql
CREATE TABLE ingest_errors (
    id              BIGSERIAL    PRIMARY KEY,
    source_type     VARCHAR(50)  NOT NULL,
    error_type      VARCHAR(100) NOT NULL,   -- 'timeout' | 'http_4xx' | 'schema_mismatch' | 'rate_limit'
    error_detail    TEXT,
    raw_data        JSONB,
    retry_count     INTEGER      NOT NULL DEFAULT 0,
    last_retry_at   TIMESTAMPTZ,
    occurred_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    resolved        BOOLEAN      NOT NULL DEFAULT FALSE
);

CREATE INDEX idx_ingest_errors_unresolved ON ingest_errors (occurred_at DESC)
    WHERE resolved = FALSE;
```

---

## 4.3 ER 關係圖（文字版）

```
raw_events (1) ──→ events (1) ──→ event_countries (N)     -- 涉及國家與角色
                            ──→ event_dimensions (1)      -- 規則引擎維度（評分用）
                            ──→ event_ai_analysis (1)     -- AI 摘要與展示用維度（不影響評分）
                            ──→ event_scores (N，各版本一筆)
                            ──→ news_sources (N)

country_tension_daily  ←── 聚合自 event_scores + event_countries（按 scoring_version）
region_tension_daily   ←── 聚合自 country_tension_daily（按 scoring_version）
global_tension_daily   ←── 聚合自 region_tension_daily（按 scoring_version）
```

---

## 4.4 常用查詢範例

### 取得最新全球趨勢（30 天，預設版本）

```sql
SELECT date, net_tension, military_score, political_score, economic_score
FROM global_tension_daily
WHERE date >= CURRENT_DATE - INTERVAL '30 days'
  AND scoring_version = 'v1'
ORDER BY date ASC;
```

### 取得今日國家排行前 20

```sql
SELECT c.country_code, c.net_tension, c.military_score,
       LAG(c.net_tension) OVER (PARTITION BY c.country_code ORDER BY c.date) AS prev_tension
FROM country_tension_daily c
WHERE c.date = CURRENT_DATE
  AND c.scoring_version = 'v1'
ORDER BY c.net_tension DESC
LIMIT 20;
```

### 取得某事件的完整可解釋資料

```sql
SELECT e.event_id, e.title, e.event_type, e.risk_or_relief, e.primary_dimension,
       es.base_severity, es.geo_sensitivity, es.time_decay,
       es.raw_score, es.final_score,    -- raw_score 為連乘原始值，final_score 為 0-100 正規化
       ea.summary_zh, ea.explanation,
       ea.dimensions AS ai_dimensions,  -- 展示用，不用於評分
       array_agg(ec.country_code || ':' || ec.role ORDER BY ec.role) AS countries
FROM events e
JOIN event_scores es ON es.event_id = e.id AND es.scoring_version = 'v1'
LEFT JOIN event_ai_analysis ea ON ea.event_id = e.id
LEFT JOIN event_countries ec ON ec.event_id = e.id
WHERE e.event_id = 'evt_20260407_001'
GROUP BY e.id, es.id, ea.id;
```

---

*文件版本：v1.1 | 2026-04-07（修正 C-1,C-2,C-4,I-2,I-4,I-8,M-1,M-10）*
