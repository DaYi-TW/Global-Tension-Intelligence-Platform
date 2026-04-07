# 02 — 資料管線規格

## 2.0 全平台統一標準

> **重要**：以下標準適用於整個系統，所有 Service 和資料表均須遵守。

| 標準 | 規格 |
|---|---|
| **國家代碼** | **ISO 3166-1 alpha-3**（三位大寫字母，如 `IRN`, `USA`, `CHN`） |
| **區域代碼** | 本文件 §2.4 定義的 9 個標準代碼（如 `middle_east`, `east_asia`） |
| **時間格式** | UTC `TIMESTAMPTZ`，ISO 8601 格式（`2026-04-07T08:00:00Z`） |
| **時間欄位名稱** | `event_time`（全平台一致，不使用 `event_date` 或 `occurred_at`） |
| **時區政策** | 系統內部無本地時間概念，一律使用 UTC。ACLED `event_date`（僅日期）視為 UTC 00:00:00 |

### 國家代碼轉換說明

GDELT 使用 **FIPS 10-4** 代碼，ACLED 使用**國家全名**（非代碼），兩者均須在 Adapter 層轉換為 ISO alpha-3：

- 映射表維護於：`backend/pipeline/normalization/country_code_map.py`
- FIPS → ISO alpha-3（GDELT 用）
- 國家全名 → ISO alpha-3（ACLED 用）
- 若映射失敗：寫入 events 但 country_codes 為空，標記 `needs_review = TRUE`

---

## 2.1 資料來源

| 來源 | 角色 | 更新頻率 | 資料類型 |
|---|---|---|---|
| **GDELT** | 廣域監測、媒體熱度、事件關聯 | 每 15 分鐘 | CSV/JSON 批次下載 |
| **ACLED** | 高可信度衝突、暴力、抗議事件 | 每小時 | REST API（需 Access Key + Email） |
| **NewsAPI / GNews** | 補全新聞原文與來源連結 | 每小時 | REST API（需 API Key） |

---

## 2.2 整體管線流程

```
Step 1  抓取原始資料
        GDELT Adapter / ACLED Adapter / News Adapter
        ↓ 寫入 raw_events（去重：source_type + source_event_id）

Step 2  事件正規化
        Normalization Service 讀取 raw_events WHERE normalized = FALSE
        ↓ 欄位映射、國家代碼標準化（→ ISO alpha-3）、時間格式統一（→ UTC）
        ↓ 寫入 events / event_countries / event_dimensions（source='rule'）/ news_sources
        ↓ 更新 raw_events.normalized = TRUE

        ⚠️ 時序說明：score_and_aggregate 在 :55 執行（見 §09）。
        正規化後若 AI 分析尚未完成，評分引擎使用 event_dimensions（source='rule'）繼續計算。
        AI 維度資料（event_ai_analysis）僅供前端展示，不影響分數。

Step 3  AI 補強分析
        AI Analysis Service 讀取 events WHERE ai_analyzed = FALSE
        ↓ 批次呼叫 LLM（每批最多 20 筆）
        ↓ 只寫入 event_ai_analysis（摘要、impact_direction、展示用 dimensions）
        ↓ 不寫入 event_dimensions（此表由 Step 2 規則引擎負責）

Step 4  評分計算
        Scoring Engine 讀取待計算事件
        ↓ 讀取 event_dimensions（source='rule'）進行維度聚合
        ↓ 計算 Event raw_score → final_score → Country → Region → Global
        ↓ 寫入 event_scores / country_tension_daily / region_tension_daily / global_tension_daily

Step 5  更新快取
        Cache Writer 主動 INVALIDATE 並重建 Redis key
        ↓ dashboard:overview / tension:* / map:heat
```

---

## 2.3 Data Ingestion Service

### 設計原則

- 每個來源一個獨立 **Adapter class**，統一實作介面：
  ```python
  class BaseAdapter:
      def fetch(self) -> List[RawEventDict]: ...
      def get_source_type(self) -> str: ...
  ```
- 抓取前先計算 `source_event_id` 的 hash，與 DB 比對去重
- 原始 JSON payload 完整保留於 `raw_payload` 欄位（永不覆寫）
- 單一來源失敗以 try/except 隔離，不影響其他來源
- 失敗記錄寫入 `ingest_errors` 表，供後續 retry（見 §2.6）

### GDELT Adapter

```
資料集：GDELT 2.0 GKG（Global Knowledge Graph）
端點：http://data.gdeltproject.org/gdeltv2/lastupdate.txt
頻率：每 15 分鐘更新一次
格式：CSV（壓縮，Tab 分隔）

關鍵欄位對應：
  GKGRECORDID  → source_event_id
  DATE         → event_time
               ⚠️ DATE 為 15 位整數（YYYYMMDDHHMMSS，UTC）
               解析方式：datetime.strptime(str(record['DATE']), '%Y%m%d%H%M%S').replace(tzinfo=timezone.utc)
               注意：GDELT 每 15 分鐘產生一個檔案，DATE 精度為檔案批次時間，非精確事件時間
  LOCATIONS    → country_codes（FIPS 格式，需透過 country_code_map.py 轉 ISO alpha-3）
  THEMES       → event_type（需映射至平台 event_type）
  TONE         → 正負情緒（輔助 risk/relief 判斷，負值代表風險傾向）
  NUMARTICLES  → source_count（初始值）
  SOURCEURLS   → news_sources（分號分隔的 URL 列表）
```

### ACLED Adapter

```
端點：https://api.acleddata.com/acled/read
認證：ACLED_ACCESS_KEY + ACLED_EMAIL（Query Params）
頻率：每小時
格式：JSON

關鍵欄位對應：
  event_id_cnty → source_event_id
  event_date    → event_time
                ⚠️ event_date 為日期字串（YYYY-MM-DD），無時間部分
                視為 UTC 00:00:00：date.fromisoformat(record['event_date']) + timezone.utc
  country       → country_codes（國家全名，需透過 country_code_map.py 轉 ISO alpha-3）
  event_type    → event_type（直接映射至平台 event_type，見 §2.4 映射表）
  fatalities    → 輔助計算 severity（傷亡數越高，severity 越高）
  actor1, actor2 → actors
  notes         → content
```

### News Adapter

```
端點：NewsAPI v2 / GNews API
認證：NEWSAPI_KEY（Header）
頻率：每小時
用途：補全事件原文，提供新聞連結

關鍵欄位對應：
  url          → source_url
  title        → title
  description  → content（補充）
  publishedAt  → published_at（ISO 8601，轉 UTC）
  source.name  → source_name
```

---

## 2.4 Event Normalization Service

### 統一事件 Schema

```json
{
  "event_id":          "evt_20260407_001",
  "source_type":       "acled",
  "source_event_id":   "IDN20260407...",
  "title":             "Missile strike reported in southern region",
  "content":           "...",
  "event_time":        "2026-04-07T08:00:00Z",
  "region_code":       "middle_east",
  "event_type":        "military_strike",
  "primary_dimension": "military",
  "risk_or_relief":    "risk",
  "severity":          0.88,
  "actors":            ["Iran", "Israel"],
  "country_codes":     [
    { "code": "IRN", "role": "initiator" },
    { "code": "ISR", "role": "target" }
  ],
  "source_count":      12,
  "source_confidence": 0.91
}
```

> 所有 `country_codes[].code` 均為 **ISO 3166-1 alpha-3**。

### 處理步驟

1. **欄位映射**：各 Adapter 輸出 → Unified Schema
2. **國家代碼標準化**：FIPS/全名 → **ISO 3166-1 alpha-3**（透過 `country_code_map.py`）
3. **時間格式統一**：任意格式 → UTC `TIMESTAMPTZ`，欄位名統一為 `event_time`
4. **事件類型映射**：來源分類 → 平台 `event_type`（見下表）
5. **primary_dimension 推斷**：依 `event_type` 查規則表（見 `03-scoring-engine §3.3`）
6. **base_severity 初始化**：依 `event_type` 查規則表，寫入 `events.severity`
7. **跨來源去重合併**：去重 key 為 `(title_hash + event_date + primary_country_code)`，同一事件合併 `source_count`，取最高 `severity`
8. **event_dimensions 建立**（source='rule'）：依 `primary_dimension` 對應欄位設為 `severity`，其餘維度按比例推斷

### source_count 說明

`events.source_count` 為去重合併後佐證來源的總數，在 Step 7 合併時遞增。
這是 `source_confidence` 公式的輸入值（見 `03-scoring-engine §3.3`）。

### 事件類型映射表（節錄）

| 原始類型（ACLED/GDELT） | 平台 event_type | primary_dimension |
|---|---|---|
| Battles, Armed clash | `military_clash` | military |
| Air/drone strike | `military_strike` | military |
| Shelling/artillery | `military_strike` | military |
| Explosions/Remote violence | `explosion` | military |
| Protests | `protest_large` | social |
| Riots | `riot` | social |
| Strategic developments / Agreements | `ceasefire_agreement` | military |
| Strategic developments / Arrests | `political_arrest` | political |
| WMD / Nuclear threat | `nuclear_threat` | military |

### 區域代碼定義（全平台正式規範）

> 以下為全平台唯一有效的 9 個區域代碼。所有資料表和 API 使用**完全相同的字串**。

| region_code | 涵蓋國家（部分，ISO alpha-3） |
|---|---|
| `east_asia` | CHN, JPN, KOR, PRK, TWN |
| `southeast_asia` | VNM, PHL, IDN, MYS, SGP, THA |
| `middle_east` | IRN, ISR, SAU, IRQ, SYR, YEM, LBN |
| `europe` | RUS, UKR, POL, DEU, FRA, GBR |
| `south_asia` | IND, PAK, AFG, BGD |
| `africa` | ETH, SDN, NGA, COD, MLI |
| `central_asia` | KAZ, UZB, TJK |
| `north_america` | USA, CAN, MEX |
| `latin_america` | BRA, COL, VEN, ARG, CHL, PER |

> 注意：Geo Sensitivity 熱點（台灣海峽、霍爾木茲海峽等）為評分用的**子地理標記**，與以上頂層區域代碼為不同概念（見 `03-scoring-engine §3.3`）。

---

## 2.5 錯誤處理策略

| 錯誤類型 | 處理方式 |
|---|---|
| 外部 API 超時（>30s） | Exponential backoff（間隔 5s / 15s / 60s），3 次後記錄失敗 |
| HTTP 4xx（非 429） | 記錄錯誤，不重試，告警 |
| HTTP 429（Rate Limit） | 等待 `Retry-After` Header 指定秒數後重試 |
| 來源格式異常（Schema mismatch） | 跳過該筆，寫入 `ingest_errors`（error_type='schema_mismatch'），發出告警 log |
| 國家代碼無法解析 | 寫入 events 但 country_codes 為空，標記 `needs_review = TRUE` |
| DB 寫入衝突（duplicate） | ON CONFLICT DO NOTHING（去重設計） |

---

## 2.6 錯誤回復流程（ingest_errors）

`ingest_errors` 表記錄所有抓取與正規化錯誤，以下為處理流程：

| 錯誤類型 | 重試策略 |
|---|---|
| `timeout` / `http_5xx` | 下次排程自動重試（Celery retry_backoff） |
| `schema_mismatch` | 不自動重試；需更新 Adapter 映射後，由人工觸發 `POST /admin/retry-ingest-error/{id}` |
| `http_4xx`（非 429） | 不重試；需人工確認 API Key 或權限問題 |

**告警閾值**：連續失敗 ≥ 3 次且間隔 > 1 小時，發出 CRITICAL log 告警（可串接 Webhook/Email）。

**重試成功**：`resolved = TRUE`，`retry_count += 1`，`last_retry_at` 更新為當前時間。

**人工審閱**：透過 `GET /admin/ingest-errors` 查看所有 `resolved = FALSE` 的錯誤列表。

> 注意：`full_recalculate` 任務只重算已正規化的事件，不重試 `ingest_errors` 中的錯誤。

---

*文件版本：v1.1 | 2026-04-07（修正 C-6,C-7,I-8,I-11,I-12,I-13,M-4）*
