# 文件 Review 報告

> 審閱範圍：`01-architecture-overview.md` ～ `11-frontend-spec.md`
> 審閱日期：2026-04-07

---

## 總體評價

文件整體品質良好，資料流設計清晰，評分邏輯在內部有一致性，關注點分離也合理。
共發現 **35 個問題**，其中 7 個 Critical、9 個 Important、12 個 Minor，以及 10 個值得保留的良好設計。

---

## 🔴 Critical（必須在開始寫程式前解決）

---

### C-1 · `event_scores` 缺少明確的外鍵與 UNIQUE 約束
**影響文件：** `04`, `03`, `05`

`event_scores` 雖在評分引擎中是核心表，但 Schema 文件未明確定義 `event_id FK` 與 `UNIQUE(event_id, scoring_version)` 約束。若不同開發者各自假設欄位名（`event_id` vs `source_event_id` vs `events_id`），join 邏輯將靜默出錯。

**修正建議：**
```sql
CREATE TABLE event_scores (
    id                BIGSERIAL    PRIMARY KEY,
    event_id          BIGINT       NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    scoring_version   VARCHAR(20)  NOT NULL,
    base_severity     NUMERIC(5,4),
    scope_weight      NUMERIC(5,4),
    geo_sensitivity   NUMERIC(5,4),
    actor_importance  NUMERIC(5,4),
    source_confidence NUMERIC(5,4),
    time_decay        NUMERIC(5,4),
    raw_score         NUMERIC(10,4) NOT NULL,   -- 未正規化的乘積結果
    final_score       NUMERIC(6,2)  NOT NULL,   -- normalize_to_100 後的結果
    computed_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE(event_id, scoring_version)
);
```

---

### C-2 · `event_countries` 欄位定義缺失
**影響文件：** `04`, `03`

`03` 評分引擎使用 role 權重（initiator=1.0, target=0.9, affected=0.6），但 `04` 從未完整定義 `event_countries` 的欄位。這是聚合管線的核心 join table。

**修正建議：**
```sql
CREATE TABLE event_countries (
    id           BIGSERIAL   PRIMARY KEY,
    event_id     BIGINT      NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    country_code CHAR(3)     NOT NULL,
    role         VARCHAR(20) NOT NULL CHECK (role IN ('initiator', 'target', 'affected')),
    UNIQUE(event_id, country_code)   -- 一個事件中，每個國家只有一個角色
);
```
同時在 `03` 中補充說明：一個事件中，同一國家只能有一個 role。

---

### C-3 · 事件分數無上下界定義，API 回傳值語意不明
**影響文件：** `03`, `05`

評分公式最大理論值為 `1.0 × 1.6 × 1.8 × 1.5 × 1.0 × 1.0 = 4.32`，relief 事件可為負值。`event_scores.final_score` 未定義是「原始乘積」還是「正規化後的 0–100 值」，但 `05` 的 `events/{id}` API 直接回傳 `final_score: 18.5`，前端無法知道這個數字的量綱。

**修正建議：**
- `event_scores` 新增兩個欄位：`raw_score`（原始乘積）與 `final_score`（normalize_to_100 後結果）
- API 的 `scoring_breakdown.final_score` 明確說明單位為「0–100 標準化分數」
- 文件補充：`final_score` 的典型範圍為 2–20，> 15 視為重大事件

---

### C-4 · `event_dimensions` 與 `event_ai_analysis.dimensions` 寫入路徑衝突
**影響文件：** `04`, `08`, `03`

兩份文件都定義了「維度分數」（military, political, economic, social, cyber），但未說明：
1. AI 輸出的 dimensions 是否寫入 `event_dimensions`？
2. `event_dimensions.source = 'hybrid'` 何時發生？
3. 評分引擎讀取哪個來源？

若兩個 Worker 各自寫入不同位置，評分引擎將讀到不一致資料。

**修正建議：** 明確定義寫入規則：
- 正規化完成時 → 規則推斷維度寫入 `event_dimensions`，`source='rule'`
- AI 分析完成時 → AI 維度**僅**寫入 `event_ai_analysis`，**不**覆蓋 `event_dimensions`
- 評分引擎**永遠讀 `event_dimensions`（source='rule'）**，AI 維度僅用於前端展示
- 刪除 `source='hybrid'`，或定義為「rule 補 AI 確認後的合併結果」

---

### C-5 · `/api/events/timeline` 路由與 `/api/events/{id}` 衝突
**影響文件：** `05`

`/api/events/timeline` 會被 FastAPI 的路由系統當作 `event_id = "timeline"` 匹配，導致靜默錯誤（回傳 404 而非資料）。

**修正建議：** 重命名為 `/api/events-timeline` 或 `/api/timeline/events`。同時在 `05` 加入 Note：「若維持此命名，FastAPI 中必須將 `timeline` 路由定義在 `{event_id}` 路由之前。」

---

### C-6 · 國家代碼標準未統一（alpha-2 vs alpha-3 vs FIPS）
**影響文件：** `02`, `04`, `05`, `11`

GDELT 使用 FIPS 10-4 代碼、ACLED 使用國家全名（非代碼）、Mapbox GeoJSON 用 alpha-3。`04` 的 `country_code CHAR(3)` 暗示 alpha-3，但 `02` 從未明確說明轉換邏輯。若不同 Worker 使用不同標準，`event_countries` JOIN `country_tension_daily` 將靜默產生空結果。

**修正建議：** 在 `02` 正規化章節明確聲明：「所有國家代碼統一為 **ISO 3166-1 alpha-3**。GDELT FIPS 代碼透過本地映射表轉換；ACLED 國家全名透過本地映射表轉換。映射表維護於 `backend/pipeline/normalization/country_codes.py`。」

---

### C-7 · Pipeline 時序設計存在評分時 AI 資料尚未就緒的問題
**影響文件：** `09`, `02`

現有排程：
- `:05` ingest_acled
- `:20` normalize_pending（最早）
- `:30` ai_enrich_pending
- `:45` score_and_aggregate

在最差情況下，`:05` 抓取的資料在 `:20` 正規化，`:30` 開始 AI 分析，但 `:45` 評分時 AI 分析可能尚未完成（批次 100 筆需時 ~50s+）。同時，`09` 文件一邊描述固定 cron 排程，一邊描述「ingest → normalize → ai_enrich → score」的 chain 依賴，兩種模型並存卻未說明哪個為主。

**修正建議（二擇一）：**
1. **Cron 模型**：將 `score_and_aggregate` 移至 `:55`，給 AI 充足時間；並說明評分時 AI 未完成的事件使用規則推斷維度
2. **Chain 模型**：移除固定時間 cron，改用 Celery `chain(ingest.si() | normalize.si() | ai_enrich.si() | score.si())`，確保順序執行

---

## 🟡 Important（整合測試前解決）

---

### I-1 · relief 事件的負數 base_severity 與分開計算的邏輯矛盾
**影響文件：** `03`

`03` 的 base_severity 表列出 relief 事件有負值（如 `ceasefire_agreement = -0.75`），但評分公式是連乘，其他因子全為正數。若 base_severity 為負，最終分數為負值，但 Net Tension 公式 `= Risk − 0.7 × Relief` 暗示兩者是分開的正數池。語意矛盾將導致不同開發者實作出完全不同的邏輯。

**修正建議：** 明確說明：「所有事件的 base_severity 均為正值。risk_or_relief 欄位決定事件分類。Event Score 永遠為正數。國家聚合時，risk 事件的分數加總為 `risk_total`，relief 事件加總為 `relief_total`，最終 `net = risk_total − 0.7 × relief_total`。」並從 base_severity 表移除所有負號。

---

### I-2 · event_type → 維度的對應未定義
**影響文件：** `03`, `04`

`03` 列出 25+ 種 event_type，但沒有定義每種 event_type 主要屬於哪個維度（military / political / economic / social / cyber）。這是 `event_dimensions` 規則推斷的依據，若未定義，規則引擎無法實作。

**修正建議：** 在 `03` 的 base_severity 表新增 `primary_dimension` 欄：

| event_type | base_severity | risk_or_relief | primary_dimension |
|---|---|---|---|
| nuclear_threat | 0.95 | risk | military |
| economic_sanctions | 0.65 | risk | economic |
| ceasefire_agreement | 0.80 | relief | military |
| cyberattack_critical | 0.70 | risk | cyber |
| … | … | … | … |

---

### I-3 · AI 維度分數不應影響評分，但文件未明確禁止
**影響文件：** `08`, `03`

設計原則是「規則引擎主導，AI 補充」，但 `08` 輸出的 `dimensions` 與 `03` 評分使用的維度分數格式相同，文件未明確說明 AI 維度永遠只用於展示。若有開發者認為 AI 維度品質更好而改用，將破壞系統確定性。

**修正建議：** 在 `03` 和 `08` 都加一行明確聲明：「AI 輸出的 dimensions 僅存入 `event_ai_analysis`，**不**寫入 `event_dimensions`，**不**用於評分計算。評分引擎只讀 `event_dimensions` 表（source='rule'）。」

---

### I-4 · 每日快照表缺少 `scoring_version` 欄位
**影響文件：** `04`, `03`, `09`

`country_tension_daily`、`region_tension_daily`、`global_tension_daily` 的 UNIQUE 約束皆不含版本號。執行 `full_recalculate` 時新版本會覆蓋舊版本，無法並存比較，也無法回滾。

**修正建議：** 三張表均加入 `scoring_version VARCHAR(20) NOT NULL DEFAULT 'v1'`，並將 UNIQUE 約束改為包含版本號：
```sql
UNIQUE(country_code, date, scoring_version)
UNIQUE(region_code, date, scoring_version)
UNIQUE(date, scoring_version)
```
API 預設查詢最新版本，可透過 `?scoring_version=v1.0` 查歷史版本。

---

### I-5 · `/api/map/heat/range` 回應格式未完整定義
**影響文件：** `05`, `11`

文件只說「data keyed by date string」，未定義：
- 每日資料是物件（`{ "IRN": 87.3 }`）還是陣列（`[{ country_code, score }]`）？
- 無事件的國家是否出現（score=0 還是省略）？
- 是否支援多維度同時回傳，或每次只能查一個維度？
- 最大日期範圍限制是多少（文件說「90天」但 API 規格未記錄）？

前端無法確定資料結構就無法實作預載邏輯。

**修正建議：** 明確定義 Response 格式：
```json
{
  "dimension": "overall",
  "from": "2026-03-01",
  "to": "2026-04-07",
  "dates": {
    "2026-03-01": {
      "IRN": 82.1,
      "ISR": 74.5,
      "RUS": 78.9
    }
  }
}
```
說明：只回傳有資料的國家；`dimension` 為必填 query param；最大範圍 90 天。

---

### I-6 · Redis cache key 不含 `scoring_version`，版本切換時會提供舊資料
**影響文件：** `06`, `03`

`full_recalculate` 完成後會 invalidate cache，但若評分版本升級未觸發全量重算（例如只修改設定而未重啟 beat），Redis 中快取的舊版分數會繼續被提供，且沒有機制偵測不一致。

**修正建議：** 選擇其一：
1. 將 `SCORING_VERSION` 加入所有 cache key（`map:heat:v2:{date}:overall`）
2. 在 Redis 中維護一個 `system:scoring_version` sentinel key，每次讀 cache 前先比對版本；版本不符則 miss

---

### I-7 · AI 積壓處理沒有優先順序與流量保護
**影響文件：** `08`, `09`

`ai_enrich_pending` 每次跑最多取 100 筆，但積壓時舊事件會優先（若無 ORDER BY DESC）。此外無最大批次保護，若 LLM API 降速，單次任務可能長時間佔用 Worker。

**修正建議：**
- `ai_enrich_pending` 的 SELECT 加入 `ORDER BY event_time DESC`（優先處理最新事件）
- 每次任務最多處理 200 筆（加入 `LIMIT 200`）
- 若待分析事件 > 500 筆，寫入 WARNING log

---

### I-8 · `ingest_errors` 的後續處理流程未定義
**影響文件：** `04`, `02`, `09`

`ingest_errors` 表記錄了錯誤，但文件沒有說明：錯誤何時重試？何時由人工處理？連續幾次失敗要告警？這個表目前是個「資料黑洞」。

**修正建議：** 在 `09` 新增「錯誤回復」章節：
- `schema_mismatch` 類型：不自動重試，需更新 adapter 後手動觸發
- `timeout/http_5xx` 類型：下次排程自動重試
- 連續失敗 3 次且間隔 > 1 小時：寫入告警（log level CRITICAL 或 Webhook）
- `full_recalculate` 不重試 `ingest_errors`，只重算已正規化的事件

---

### I-9 · `/api/events/timeline` 缺少 query parameters 定義
**影響文件：** `05`, `11`

端點缺少：日期範圍參數、最低分數門檻、最大回傳筆數。若無限制，時間軸初始載入可能回傳數萬筆事件，直接造成前端崩潰。

**修正建議：** 定義必要 query params：

| 參數 | 類型 | 必填 | 預設 |
|---|---|---|---|
| `from` | string (YYYY-MM-DD) | ✅ | — |
| `to` | string (YYYY-MM-DD) | ✅ | — |
| `min_score` | number | ❌ | 10 |
| `limit` | integer | ❌ | 200 |
| `country` | string | ❌ | — |
| `region` | string | ❌ | — |

---

### I-10 · `ai_daily_summary` 在 06:00 UTC 前為 null，前端未定義處理方式
**影響文件：** `05`, `08`

`daily_summary_gen` 在每日 06:00 UTC 執行，在此之前 `dashboard/overview` 的 `ai_daily_summary` 欄位為 null。前端若未處理 null 會閃爍或崩潰。

**修正建議：** 在 `05` 明確標注 `ai_daily_summary: string | null`，並說明前端遇到 null 時顯示「今日摘要生成中，請稍後再試」。在 `08` 補充 rule-based fallback summary 的格式（例如：「今日 X 個風險事件，Y 個緩和事件，緊張度 Z。」）。

---

### I-11 · `source_count` 欄位存放位置未定義
**影響文件：** `03`, `02`

`source_confidence = min(1.0, 0.5 + 0.1 × source_count)` 中的 `source_count` 是跨來源去重後的聚合值，但去重邏輯（何謂「同一事件」）和 `source_count` 的存放欄位都未說明。

**修正建議：**
1. 定義去重 key：`(region_code, event_type, event_time ± 6小時)` 視為同一事件
2. `events` 表的 `source_count` 欄位（已有）在去重合併時遞增
3. 明確說明：`events.source_count` 是評分引擎讀取的欄位，代表交叉佐證的來源數量

---

### I-12 · 區域代碼格式在各文件不一致
**影響文件：** `02`, `04`, `05`

`02` 定義了 9 個 underscore 格式的區域代碼（`east_asia`, `middle_east` 等）。`03` 的地理敏感度表使用自然語言（"Taiwan Strait", "Korean Peninsula"）。`05` 的 `/api/regions/{code}` 未說明接受哪種格式。

**修正建議：** 在 `02` 建立區域代碼正式定義表，其他文件引用此定義。地理敏感熱點（台海等）為「子地理標記」，與 9 個頂層區域代碼為不同概念，應在文件中明確區分。

---

### I-13 · GDELT `DATE` 欄位解析方式未記錄
**影響文件：** `02`

GDELT GKG 2.0 的 `DATE` 欄位為 15 位整數（`YYYYMMDDHHMMSS` 格式），並非標準時間字串。文件列出此欄位但未說明如何解析。

**修正建議：** 在 GDELT Adapter 規格加入：「`DATE` 為整數，使用 `datetime.strptime(str(record['DATE']), '%Y%m%d%H%M%S')` 解析為 UTC datetime。」

---

### I-14 · `full_recalculate` 任務的執行範圍未定義
**影響文件：** `09`, `03`

每週日 02:00 的全量重算任務未定義：回溯幾天？若版本未變是否仍執行？執行期間 cache 如何處理？大量資料下此任務可能跑數小時，文件對此無任何說明。

**修正建議：**
- 預設回溯範圍：`RECALCULATE_LOOKBACK_DAYS`（預設 90，可由環境變數設定）
- 若 DB 中記錄的 `scoring_version` 與環境變數相同，跳過執行（加入 idempotency check）
- 執行期間不 invalidate cache，直到任務完成後再統一更新

---

### I-15 · Zustand store 缺少載入狀態與預載追蹤
**影響文件：** `11`

現有 store 定義缺少：`isLoading`（預載進度）、`preloadedDateRange`（已預載的範圍，避免重複請求）、`error`（API 錯誤狀態）、`selectedRegion`（區域面板）。沒有這些狀態，時間軸的預載邏輯無處追蹤進度。

**修正建議：** 擴充 Zustand store：
```typescript
interface GlobalStore {
  // 現有欄位...
  isMapLoading: boolean
  preloadedRange: { from: string; to: string } | null
  mapLoadError: string | null
  selectedRegion: string | null   // ISO region code
  // Actions
  setPreloadedRange: (range: { from: string; to: string }) => void
  setMapLoadError: (err: string | null) => void
}
```

---

### I-16 · Admin API 無任何認證保護
**影響文件：** `05`, `07`, `10`

`POST /admin/recalculate` 可觸發全量重算（耗費大量資源），目前完全公開無保護。

**修正建議：** 在 `07` 的 Nginx config 加入：
```nginx
location /admin/ {
    allow 10.0.0.0/8;
    allow 172.16.0.0/12;
    deny all;
    # 或使用 API Key Header
    # if ($http_x_admin_key != "your_key") { return 403; }
    proxy_pass http://api_backend;
}
```
在 `05` 中標注：「`/admin/*` 端點需要 `X-Admin-Key` Header 或限制來源 IP，不對外公開。」

---

## 🟢 Minor（實作前可處理）

| ID | 問題 | 建議 |
|---|---|---|
| M-1 | `news_sources` 表用途不明（孤立表） | 說明其用於事件詳情頁展示來源連結，並連接 `source_confidence` 計算 |
| M-2 | `dashboard/overview` 的 `trend_7d` 型別不明 | 定義為 `{ direction, delta, sparkline: number[] }` |
| M-3 | `event_ai_analysis` 缺少 `model_version` 欄位 | 新增 `model_version VARCHAR(50)` 和 `prompt_version VARCHAR(20)` |
| M-4 | 時區政策未統一聲明 | 在 `02` 加入「時區政策」章節：所有時間戳記為 UTC，`date` 欄位代表 UTC 日期 |
| M-5 | `cleanup_old_cache` 任務清理目標不明 | 明確定義：清理 180 天以前的 `raw_events`（已正規化），30 天以前的 `ingest_errors` |
| M-6 | `playSpeed` 有效值未定義 | 定義為 `1 \| 3 \| 7`（每秒跳幾天），搭配 400ms 過渡動畫 |
| M-7 | ACLED 環境變數應為兩個（email + key） | `ACLED_EMAIL` + `ACLED_ACCESS_KEY`（ACLED API 認證需要兩者） |
| M-8 | `fastest_rising_countries` 計算邏輯未定義 | 定義為「過去 24 小時絕對分數漲幅 Top 5，讀取 `country_tension_daily` 今日 vs 昨日」 |
| M-9 | `/api/map/heat` 與 `/api/map/heat/range` 重疊 | 說明差異：`/heat` 回傳即時（15min cache）單日，`/heat/range` 回傳歷史批次（1hr cache） |
| M-10 | `event_time` / `event_date` / `occurred_at` 命名不統一 | 統一為 `event_time TIMESTAMPTZ`（已在 `04` 使用），`02` 和 `05` 對齊此名稱 |
| M-11 | 地圖色階壓縮問題（大多數國家分數集中在 20–60） | 考慮百分位數正規化色階，或在文件加入說明：色階設計為全範圍，實際分布集中在中段 |
| M-12 | 區域分數使用等權平均（Monaco = Germany） | 在 `03` 加入說明：MVP 使用等權平均，Phase 2 可引入 GDP 或人口加權 |

---

## ✅ 良好設計（值得保留）

| ID | 設計 | 說明 |
|---|---|---|
| G-1 | 確定性規則引擎 + AI 僅作補充 | 保障可重現性、可審計性、不受 LLM 幻覺影響 |
| G-2 | Write-Once Raw Layer | 支援 pipeline 重跑，不怕正規化 bug 造成資料遺失 |
| G-3 | `tanh` 正規化 | 優雅處理無上界的原始分數，提供自然的分數分布 |
| G-4 | 評分版本管理概念 | 支援歷史審計與 A/B 測試，設計有遠見 |
| G-5 | `source_confidence` 公式設計 | 起始值 0.5、每來源 +0.1、[0.3, 1.0] clamp，合理且可調 |
| G-6 | risk/relief 不同衰減半衰期 | 危機持續、緩和短暫，符合真實地緣政治行為 |
| G-7 | `ON CONFLICT` 冪等性設計 | Pipeline 可安全重跑，crash/retry 不產生重複資料 |
| G-8 | initiator/target/affected 角色模型 | 捕捉了事件中不同國家的主動程度差異 |
| G-9 | Redis 不可用時降級至 PostgreSQL | 系統優雅降級，不因快取失效而中斷服務 |
| G-10 | 前端 ±30 天預載 + 200ms debounce | 時間軸播放流暢的正確實作方式 |

---

## 優先解決順序

### 立即（開始寫程式前）
1. **C-6** — 確定 alpha-3 國家代碼標準（所有 join 的基礎）
2. **C-2** — 補全 `event_countries` schema
3. **C-1** — 補全 `event_scores` schema，區分 raw_score / final_score
4. **C-4** — 確立 `event_dimensions` 寫入路徑（rule vs AI 分工）
5. **I-1** — 統一 relief 事件分數為正值，語意獨立計算
6. **I-2** — 每個 event_type 標記所屬 primary_dimension

### 整合測試前
7. **C-3** — API 的 final_score 語意明確化
8. **C-5** — 修正 `/api/events/timeline` 路由衝突
9. **C-7** — 確立 cron vs chain 排程模型
10. **I-4** — 每日快照表加入 scoring_version
11. **I-16** — Admin API 加入保護

### 前端開發前
12. **I-5** — 定義 `/api/map/heat/range` 完整 response schema
13. **I-9** — 定義 `/api/events/timeline` query params
14. **I-15** — 擴充 Zustand store 定義

---

*Review 版本：v1.0 | 2026-04-07*
