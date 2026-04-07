# 02 — 資料管線規格

## 2.1 資料來源

| 來源 | 角色 | 更新頻率 | 資料類型 |
|---|---|---|---|
| **GDELT** | 廣域監測、媒體熱度、事件關聯 | 每 15 分鐘 | CSV/JSON 批次下載 |
| **ACLED** | 高可信度衝突、暴力、抗議事件 | 每小時 | REST API（需 API Key） |
| **NewsAPI / GNews** | 補全新聞原文與來源連結 | 每小時 | REST API（需 API Key） |

---

## 2.2 整體管線流程

```
Step 1  抓取原始資料
        GDELT Adapter / ACLED Adapter / News Adapter
        ↓ 寫入 raw_events（去重：source_type + source_event_id MD5）

Step 2  事件正規化
        Normalization Service 讀取 raw_events WHERE normalized = FALSE
        ↓ 欄位映射、國家代碼標準化、時間格式統一
        ↓ 寫入 events / event_countries / news_sources
        ↓ 更新 raw_events.normalized = TRUE

Step 3  AI 補強分析
        AI Analysis Service 讀取 events WHERE ai_analyzed = FALSE
        ↓ 批次呼叫 LLM（每批最多 20 筆）
        ↓ 寫入 event_ai_analysis / event_dimensions

Step 4  評分計算
        Scoring Engine 讀取待計算事件
        ↓ 計算 Event Score → Country Tension → Region Tension → Global Tension
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
- 失敗記錄寫入 `ingest_errors` 表，供後續 retry

### GDELT Adapter

```
資料集：GDELT 2.0 GKG（Global Knowledge Graph）
端點：http://data.gdeltproject.org/gdeltv2/lastupdate.txt
頻率：每 15 分鐘更新一次
格式：CSV（壓縮）
關鍵欄位：
  - GKGRECORDID     → source_event_id
  - DATE            → event_time
  - LOCATIONS       → country_codes（需解析 ISO 代碼）
  - THEMES          → event_type（需映射）
  - TONE            → 正負情緒（輔助 risk/relief 判斷）
  - NUMARTICLES     → source_count
  - SOURCEURLS      → news_sources
```

### ACLED Adapter

```
端點：https://api.acleddata.com/acled/read
認證：API Key + Email（Header）
頻率：每小時
格式：JSON
關鍵欄位：
  - event_id_cnty   → source_event_id
  - event_date      → event_time
  - country         → country_codes（需轉 ISO alpha-3）
  - event_type      → event_type（直接映射）
  - fatalities      → 輔助計算 severity
  - actor1, actor2  → actors
  - notes           → content
```

### News Adapter

```
端點：NewsAPI v2 / GNews API
認證：API Key
頻率：每小時
用途：補全事件原文，提供新聞連結
關鍵欄位：
  - url             → source_url
  - title           → title
  - description     → content（補充）
  - publishedAt     → published_at
  - source.name     → source_name
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

### 處理步驟

1. **欄位映射**：各 Adapter 輸出 → Unified Schema
2. **國家代碼標準化**：全名/縮寫 → ISO 3166-1 alpha-3（維護本地映射表）
3. **時間格式統一**：任意格式 → UTC ISO 8601
4. **事件類型映射**：來源分類 → 平台事件類型（見下表）
5. **base_severity 初始化**：依事件類型規則表賦值（詳見評分引擎文件）
6. **跨來源去重合併**：同一事件來自多源時，合併 source_count，取最高 severity

### 事件類型映射表（節錄）

| 原始類型（ACLED/GDELT） | 平台 event_type |
|---|---|
| Battles, Armed clash | `military_clash` |
| Air/drone strike | `military_strike` |
| Shelling/artillery | `military_strike` |
| Explosions/Remote violence | `explosion` |
| Protests | `protest_large` |
| Riots | `riot` |
| Strategic developments / Agreements | `ceasefire_agreement` |
| Strategic developments / Arrests | `political_arrest` |
| WMD / Nuclear threat | `nuclear_threat` |

### 區域代碼定義

| region_code | 涵蓋國家（部分） |
|---|---|
| `east_asia` | CHN, JPN, KOR, PRK, TWN |
| `southeast_asia` | VNM, PHL, IDN, MYS, SGP, THA |
| `middle_east` | IRN, ISR, SAU, IRQ, SYR, YEM, LBN |
| `europe` | RUS, UKR, POL, DEU, FRA, GBR |
| `south_asia` | IND, PAK, AFG, BGD |
| `africa` | ETH, SDN, NGA, COD, MLI |
| `central_asia` | KAZ, UZB, TJK |
| `north_america` | USA, CAN, MEX |
| `latin_america` | BRA, COL, VEN, ARG |

---

## 2.5 錯誤處理策略

| 錯誤類型 | 處理方式 |
|---|---|
| 外部 API 超時（>30s） | Exponential backoff（間隔 5s / 15s / 60s），3 次後記錄失敗 |
| HTTP 4xx（非 429） | 記錄錯誤，不重試，告警 |
| HTTP 429（Rate Limit） | 等待 `Retry-After` Header 指定秒數後重試 |
| 來源格式異常（Schema mismatch） | 跳過該筆，寫入 `ingest_errors`，發出告警 log |
| 國家代碼無法解析 | 寫入 events 但 country_codes 為空，標記 `needs_review = TRUE` |
| DB 寫入衝突（duplicate） | ON CONFLICT DO NOTHING（去重設計） |

---

*文件版本：v1.0 | 2026-04-07*
