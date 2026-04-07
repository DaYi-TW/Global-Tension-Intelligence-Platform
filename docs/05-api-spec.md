# 05 — API 規格

## 5.1 通用規範

- Base URL：`/api`
- 資料格式：JSON（`Content-Type: application/json`）
- 時間格式：ISO 8601 UTC（`2026-04-07T08:00:00Z`），欄位名稱統一為 `event_time`
- 分頁：`page`（1-based）+ `limit`（預設 20，最大 100）
- 錯誤格式：`{ "error": "message", "code": "ERROR_CODE" }`
- 快取：所有 GET 皆有對應 Redis key，Cache-Control 由 Nginx 設定
- **國家代碼**：ISO 3166-1 alpha-3（如 `IRN`, `USA`）
- **區域代碼**：`02-data-pipeline.md §2.4` 定義的 9 個標準代碼（如 `middle_east`）
- **final_score**：0–100 正規化值（`normalize_to_100(raw_score)`），不是原始連乘結果

---

## 5.2 Dashboard API

### `GET /api/dashboard/overview`

首頁總覽，所有主要資訊一次取得。

**Response 200：**

```json
{
  "global_tension": {
    "score": 68.5,
    "band": "High",
    "band_zh": "高壓",
    "delta_1d": 7.2,
    "delta_7d": 12.1
  },
  "trend_7d": [
    // sparkline 陣列：固定 7 筆，按日期升序，用於首頁趨勢迷你圖
    { "date": "2026-04-01", "score": 56.3 },
    { "date": "2026-04-02", "score": 58.1 },
    { "date": "2026-04-03", "score": 61.4 },
    { "date": "2026-04-04", "score": 63.0 },
    { "date": "2026-04-05", "score": 64.7 },
    { "date": "2026-04-06", "score": 61.3 },
    { "date": "2026-04-07", "score": 68.5 }
  ],
  "top_risk_events": [
    {
      "event_id": "evt_20260407_001",
      "title": "Missile strike reported in southern Iran",
      "summary_zh": "伊朗南部遭飛彈攻擊，疑似以色列報復行動。",
      "event_type": "military_strike",
      "risk_or_relief": "risk",
      "countries": ["IRN", "ISR"],
      "score_contribution": 18.5,
      "event_time": "2026-04-07T08:00:00Z"
    }
  ],
  "top_relief_events": [
    {
      "event_id": "evt_20260406_022",
      "title": "Sudan ceasefire talks resume in Cairo",
      "summary_zh": "蘇丹停火談判在開羅重啟，雙方達成初步共識。",
      "event_type": "peace_talks_start",
      "risk_or_relief": "relief",
      "countries": ["SDN"],
      "score_contribution": 6.2,
      "event_time": "2026-04-06T14:00:00Z"
    }
  ],
  "region_rankings": [
    { "region_code": "middle_east", "name_zh": "中東", "score": 82.1, "rank": 1, "delta_1d": 4.5 },
    { "region_code": "east_asia",   "name_zh": "東亞", "score": 71.3, "rank": 2, "delta_1d": 2.1 },
    { "region_code": "europe",      "name_zh": "歐洲", "score": 65.8, "rank": 3, "delta_1d": -1.2 }
  ],
  "country_rankings": [
    { "country_code": "IRN", "name_zh": "伊朗",   "score": 87.3, "rank": 1, "delta_1d": 5.2 },
    { "country_code": "PRK", "name_zh": "北韓",   "score": 84.1, "rank": 2, "delta_1d": 0.0 },
    { "country_code": "RUS", "name_zh": "俄羅斯", "score": 78.9, "rank": 3, "delta_1d": -0.8 }
  ],
  "fastest_rising_countries": [
    // Top 5：過去 24 小時漲幅最大（today - yesterday），同分以 today score DESC 排序
    { "country_code": "IRN", "name_zh": "伊朗", "delta_1d": 5.2 }
  ],
  "ai_daily_summary": "今日世界緊張度 68.5，較昨日上升 7.2 點。...",
  // ⚠️ ai_daily_summary 可能為 null（每日 06:00 UTC 前尚未生成）
  // 前端遇到 null 時應顯示「今日摘要生成中，請稍後再試」
  "generated_at": "2026-04-07T06:05:00Z"
}
```

---

## 5.3 Tension Trend API

### `GET /api/tension/global/trend`

**Query Parameters：**

| 參數 | 類型 | 預設 | 說明 |
|---|---|---|---|
| `range` | string | `30d` | `7d` \| `30d` \| `90d` \| `1y` |

**Response 200：**

```json
{
  "range": "30d",
  "data": [
    {
      "date": "2026-03-08",
      "score": 55.2,
      "military": 62.1,
      "political": 48.3,
      "economic": 51.0,
      "social": 38.5,
      "cyber": 29.1
    }
  ]
}
```

---

## 5.4 Region Ranking API

### `GET /api/tension/regions`

**Query Parameters：**

| 參數 | 類型 | 預設 | 說明 |
|---|---|---|---|
| `date` | string | 今日 | 指定日期 `YYYY-MM-DD` |

**Response 200：**

```json
{
  "date": "2026-04-07",
  "regions": [
    {
      "region_code": "middle_east",
      "name_zh": "中東",
      "name_en": "Middle East",
      "score": 82.1,
      "band": "Crisis",
      "band_zh": "危機",
      "delta_1d": 4.5,
      "delta_7d": 11.2,
      "top_country_codes": ["IRN", "ISR", "YEM"],
      "top_event_title": "Missile strike reported in southern Iran"
    }
  ]
}
```

---

## 5.5 Country Ranking API

### `GET /api/tension/countries`

**Query Parameters：**

| 參數 | 類型 | 預設 | 說明 |
|---|---|---|---|
| `region` | string | 無 | 篩選特定區域 |
| `order_by` | string | `score` | `score` \| `delta_1d` \| `delta_7d` |
| `date` | string | 今日 | `YYYY-MM-DD` |
| `limit` | integer | 20 | 最多 100 |

**Response 200：**

```json
{
  "date": "2026-04-07",
  "countries": [
    {
      "country_code": "IRN",
      "name_zh": "伊朗",
      "name_en": "Iran",
      "region_code": "middle_east",
      "score": 87.3,
      "band": "Crisis",
      "band_zh": "危機",
      "delta_1d": 5.2,
      "delta_7d": 14.1,
      "military": 90.2,
      "political": 78.5,
      "economic": 71.3,
      "social": 55.1,
      "cyber": 42.0
    }
  ]
}
```

---

## 5.6 Events API

### `GET /api/events`

**Query Parameters：**

| 參數 | 類型 | 說明 |
|---|---|---|
| `country` | string | ISO alpha-3 國家代碼 |
| `region` | string | 區域代碼 |
| `type` | string | event_type 值 |
| `risk_or_relief` | string | `risk` \| `relief` \| `neutral` |
| `date_from` | string | `YYYY-MM-DD` |
| `date_to` | string | `YYYY-MM-DD` |
| `keyword` | string | 全文搜尋（標題 + 摘要） |
| `page` | integer | 分頁（預設 1） |
| `limit` | integer | 每頁筆數（預設 20，最大 100） |

**Response 200：**

```json
{
  "total": 245,
  "page": 1,
  "limit": 20,
  "items": [
    {
      "event_id": "evt_20260407_001",
      "title": "Missile strike reported in southern Iran",
      "summary_zh": "伊朗南部遭飛彈攻擊，疑似以色列報復行動。",
      "event_time": "2026-04-07T08:00:00Z",
      "event_type": "military_strike",
      "risk_or_relief": "risk",
      "severity": 0.88,
      "countries": [
        { "code": "IRN", "role": "target" },
        { "code": "ISR", "role": "initiator" }
      ],
      "final_score": 18.5,
      "source_count": 12,
      "source_confidence": 0.91
    }
  ]
}
```

---

## 5.7 Event Detail API

### `GET /api/events/{event_id}`

**Response 200：**

```json
{
  "event_id": "evt_20260407_001",
  "title": "Missile strike reported in southern Iran",
  "content": "Multiple sources confirm a missile attack on...",
  "summary_zh": "伊朗南部遭飛彈攻擊，疑似以色列報復行動，造成基礎設施損毀。",
  "summary_en": "A missile strike on southern Iran was confirmed by multiple sources...",
  "event_time": "2026-04-07T08:00:00Z",
  "event_type": "military_strike",
  "risk_or_relief": "risk",
  "region_code": "middle_east",
  "countries": [
    { "code": "IRN", "name_zh": "伊朗",   "role": "target" },
    { "code": "ISR", "name_zh": "以色列", "role": "initiator" }
  ],
  "dimensions": {
    "military": 0.88,
    "political": 0.45,
    "economic": 0.30,
    "social": 0.10,
    "cyber": 0.05
  },
  "scoring_breakdown": {
    "base_severity": 0.88,
    "scope_weight": 1.3,
    "geo_sensitivity": 1.6,
    "actor_importance": 1.5,
    "source_confidence": 0.91,
    "time_decay": 1.0,
    "raw_score": 3.12,       // 連乘原始值（未正規化）
    "final_score": 18.5      // normalize_to_100(raw_score)，0–100 正規化值
  },
  "ai_explanation": "此事件涉及中東敏感區域的直接軍事攻擊，伊朗與以色列均為區域關鍵行為者，軍事維度影響最為顯著。",
  "news_sources": [
    {
      "source_name": "Reuters",
      "title": "Iran reports missile attack in southern province",
      "url": "https://reuters.com/...",
      "published_at": "2026-04-07T08:30:00Z",
      "language": "en",
      "credibility_score": 0.95
    }
  ],
  "related_events": [
    {
      "event_id": "evt_20260405_018",
      "title": "Israel conducts air drill near Lebanon border",
      "event_time": "2026-04-05T10:00:00Z",
      "event_type": "military_exercise"
    }
  ]
}
```

---

## 5.8 Country Detail API

### `GET /api/countries/{country_code}`

**Query Parameters：**

| 參數 | 類型 | 說明 |
|---|---|---|
| `trend_range` | string | `30d` \| `90d`（預設 `30d`） |

**Response 200：**

```json
{
  "country_code": "IRN",
  "name_zh": "伊朗",
  "name_en": "Iran",
  "region_code": "middle_east",
  "current_tension": {
    "score": 87.3,
    "band": "Crisis",
    "band_zh": "危機",
    "delta_1d": 5.2,
    "as_of": "2026-04-07"
  },
  "dimensions": {
    "military": 90.2,
    "political": 78.5,
    "economic": 71.3,
    "social": 55.1,
    "cyber": 42.0
  },
  "risk_relief_ratio": {
    "risk_score": 95.1,
    "relief_score": 11.2
  },
  "trend_30d": [
    { "date": "2026-03-08", "score": 72.1 }
  ],
  "recent_events": [
    {
      "event_id": "evt_20260407_001",
      "title": "Missile strike reported in southern Iran",
      "event_type": "military_strike",
      "risk_or_relief": "risk",
      "event_time": "2026-04-07T08:00:00Z",
      "score_contribution": 18.5
    }
  ],
  "top_contributing_events": [
    {
      "event_id": "evt_20260407_001",
      "title": "...",
      "score_contribution": 18.5,
      "factors": {
        "base_severity": 0.88,
        "geo_sensitivity": 1.6,
        "time_decay": 1.0
      }
    }
  ]
}
```

---

## 5.9 Region Detail API

### `GET /api/regions/{region_code}`

**Response 200：**

```json
{
  "region_code": "middle_east",
  "name_zh": "中東",
  "current_tension": {
    "score": 82.1,
    "band": "Crisis",
    "delta_1d": 4.5
  },
  "trend_30d": [...],
  "country_rankings": [
    { "country_code": "IRN", "name_zh": "伊朗", "score": 87.3 }
  ],
  "top_risk_events": [...],
  "top_relief_events": [...]
}
```

---

## 5.10 Map Heat API

### `GET /api/map/heat`

> 用途：即時單日地圖染色（含熱點標記），適合「今日視角」。
> 與 `/api/map/heat/range` 的差異：此 endpoint 含 `hotspots` 且有更短的快取 TTL（15 分鐘）。

**Query Parameters：**

| 參數 | 類型 | 說明 |
|---|---|---|
| `date` | string | 指定日期（預設今日） |
| `dimension` | string | `overall`（預設）\| `military` \| `political` \| `economic` \| `social` \| `cyber` |

**Response 200：**

```json
{
  "date": "2026-04-07",
  "dimension": "overall",
  "countries": [
    {
      "country_code": "IRN",
      "lat": 32.4,
      "lng": 53.7,
      "score": 87.3,
      "band": "Crisis",
      "band_zh": "危機"
    }
  ],
  "hotspots": [
    {
      "label": "Strait of Hormuz",
      "label_zh": "霍爾木茲海峽",
      "lat": 26.6,
      "lng": 56.3,
      "intensity": 0.92
    },
    {
      "label": "Taiwan Strait",
      "label_zh": "台灣海峽",
      "lat": 24.5,
      "lng": 119.5,
      "intensity": 0.75
    }
  ],
  "generated_at": "2026-04-07T06:05:00Z"
}
```

---

## 5.11 Map Heat Range API（時間軸批次資料）

### `GET /api/map/heat/range`

> 用途：批次取得日期範圍的地圖染色資料，供前端時間軸播放預載使用。
> 與 `/api/map/heat` 的差異：不含 `hotspots`（靜態資料，從 `/api/map/heat` 取得一次即可）；快取 TTL 1 小時（歷史資料，較少變動）。

**Query Parameters：**

| 參數 | 類型 | 說明 |
|---|---|---|
| `from` | string | ✅ 必填 | 開始日期 `YYYY-MM-DD` |
| `to` | string | ✅ 必填 | 結束日期 `YYYY-MM-DD`（最多跨距 90 天） |
| `dimension` | string | ✅ 必填 | `overall` \| `military` \| `political` \| `economic` \| `social` \| `cyber` |

**Response 200：**

```json
{
  "dimension": "overall",
  "from": "2026-04-06",
  "to": "2026-04-07",
  "dates": {
    "2026-04-06": {
      "IRN": { "score": 82.1, "band": "Crisis", "band_zh": "危機" },
      "ISR": { "score": 74.5, "band": "High",   "band_zh": "高壓" }
    },
    "2026-04-07": {
      "IRN": { "score": 87.3, "band": "Crisis", "band_zh": "危機" }
    }
  }
}
```

> 說明：`dates` 物件 key 為日期字串，value 為當日有資料的國家 map（key = ISO alpha-3）。
> 無資料的國家不出現（分數視為 0）。前端可直接以 `dates[date][countryCode]?.score ?? 0` 取值。

---

## 5.12 Events Timeline API（時間軸刻度標記）

### `GET /api/events-timeline`

> ⚠️ 路由為 `/api/events-timeline`（連字號），不是 `/api/events/timeline`。
> 使用 `/events/timeline` 會與 `/events/{event_id}` 路由衝突（FastAPI 會將 "timeline" 解析為 event_id）。

取得日期範圍內超過閾值的重大事件，用於時間軸上的刻度標記。

**Query Parameters：**

| 參數 | 類型 | 必填 | 預設 | 說明 |
|---|---|---|---|---|
| `from` | string | ✅ | — | 開始日期 `YYYY-MM-DD` |
| `to` | string | ✅ | — | 結束日期 `YYYY-MM-DD` |
| `min_score` | number | ❌ | 10 | 最低 final_score 門檻 |
| `limit` | integer | ❌ | 50 | 最大回傳筆數（上限 200） |
| `risk_or_relief` | string | ❌ | — | `risk` \| `relief`（不填則兩者都回傳） |
| `country` | string | ❌ | — | 篩選特定 ISO alpha-3 國家 |
| `region` | string | ❌ | — | 篩選特定區域代碼 |

**Response 200：**

```json
{
  "events": [
    {
      "event_id": "evt_20260407_001",
      "date": "2026-04-07",
      "event_time": "2026-04-07T08:00:00Z",
      "title": "Missile strike reported in southern Iran",
      "summary_zh": "伊朗南部遭飛彈攻擊。",
      "risk_or_relief": "risk",
      "final_score": 18.5,
      "countries": ["IRN", "ISR"]
    }
  ]
}
```

---

## 5.13 Admin API（內部使用）

> ⚠️ `/admin/*` 端點限制：
> - 僅允許內網 IP 訪問（Nginx 層 IP 白名單）
> - 需提供 `Authorization: Bearer {ADMIN_API_KEY}` Header
> - 未授權的請求回傳 `401 Unauthorized`

### `POST /admin/recalculate`

觸發全量或部分重算。

```json
Request:
{
  "scoring_version": "v1.1",
  "from_date": "2026-01-01",
  "to_date": "2026-04-07"
}

Response:
{ "job_id": "recalc_20260407_001", "status": "queued", "estimated_events": 15230 }
```

### `GET /admin/ingest-errors`

查看待處理的抓取錯誤列表。

---

## 5.14 HTTP 狀態碼規範

| 狀態碼 | 情境 |
|---|---|
| 200 | 成功 |
| 400 | 請求參數錯誤 |
| 401 | Admin API 認證失敗（缺少或無效的 Bearer token） |
| 404 | 找不到資源（event_id / country_code 不存在） |
| 422 | 參數格式驗證失敗（Pydantic） |
| 500 | 伺服器內部錯誤 |
| 503 | 服務暫時不可用（DB/Redis 異常） |

---

*文件版本：v1.1 | 2026-04-07（修正 C-5,C-6,I-5,I-9,I-10,I-16,M-2,M-8,M-9）*
