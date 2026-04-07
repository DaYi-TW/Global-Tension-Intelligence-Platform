# 09 — 背景排程與 Worker 設計

## 9.1 技術選型

| 工具 | 用途 |
|---|---|
| **Celery** | 分散式任務隊列（執行 pipeline 任務） |
| **Celery Beat** | 排程觸發器（相當於 cron daemon） |
| **Redis** | Message Broker（任務隊列）+ Result Backend |
| **Flower** | Celery Web 監控介面（`localhost:5555`） |

---

## 9.2 任務排程總表

| 任務名稱 | Celery Task | 頻率 | 說明 |
|---|---|---|---|
| `ingest_gdelt` | `pipeline.tasks.ingest_gdelt` | 每 15 分鐘 | 抓取 GDELT 最新資料 |
| `ingest_acled` | `pipeline.tasks.ingest_acled` | 每小時（:05） | 抓取 ACLED 更新 |
| `ingest_news` | `pipeline.tasks.ingest_news` | 每小時（:10） | 補全新聞原文 |
| `normalize_pending` | `pipeline.tasks.normalize_pending` | 每 20 分鐘 | 正規化待處理事件 |
| `ai_enrich_pending` | `pipeline.tasks.ai_enrich_pending` | 每 30 分鐘 | AI 批次分析 |
| `score_and_aggregate` | `pipeline.tasks.score_and_aggregate` | 每小時（:55） | 重算並聚合各層分數 |
| `refresh_cache` | `pipeline.tasks.refresh_cache` | score_and_aggregate 完成後觸發 | 更新 Redis 快取 |
| `daily_summary_gen` | `pipeline.tasks.daily_summary_gen` | 每日 06:00 UTC | 生成 AI 每日摘要 |
| `full_recalculate` | `pipeline.tasks.full_recalculate` | 每週日 02:00 UTC | 全量重算（防止累積誤差） |
| `cleanup_old_cache` | `pipeline.tasks.cleanup_old_cache` | 每日 03:00 UTC | 清理過期快取 key |

---

## 9.3 Celery Beat 設定

```python
# pipeline/celery_config.py
from celery.schedules import crontab

CELERYBEAT_SCHEDULE = {
    "ingest-gdelt": {
        "task": "pipeline.tasks.ingest_gdelt",
        "schedule": 900,   # 每 15 分鐘（秒數）
    },
    "ingest-acled": {
        "task": "pipeline.tasks.ingest_acled",
        "schedule": crontab(minute=5),   # 每小時 :05
    },
    "ingest-news": {
        "task": "pipeline.tasks.ingest_news",
        "schedule": crontab(minute=10),  # 每小時 :10
    },
    "normalize-pending": {
        "task": "pipeline.tasks.normalize_pending",
        "schedule": 1200,  # 每 20 分鐘
    },
    "ai-enrich-pending": {
        "task": "pipeline.tasks.ai_enrich_pending",
        "schedule": 1800,  # 每 30 分鐘
    },
    "score-and-aggregate": {
        "task": "pipeline.tasks.score_and_aggregate",
        "schedule": crontab(minute=55), # 每小時 :55（確保 AI 分析有足夠時間完成）
    },
    "daily-summary": {
        "task": "pipeline.tasks.daily_summary_gen",
        "schedule": crontab(hour=6, minute=0),
    },
    "weekly-full-recalculate": {
        "task": "pipeline.tasks.full_recalculate",
        "schedule": crontab(hour=2, minute=0, day_of_week="sunday"),
    },
    "daily-cleanup": {
        "task": "pipeline.tasks.cleanup_old_cache",
        "schedule": crontab(hour=3, minute=0),
    },
}
```

---

## 9.4 任務依賴關係

> **重要說明**：各任務均由 Celery Beat 以**獨立 cron 排程**觸發，彼此之間無強制 chain 依賴。
> 下圖為**邏輯資料流順序**，不代表任務間有 Celery chain 執行。
> 唯一的例外是 `refresh_cache`，它在 `score_and_aggregate` 完成後以 `.delay()` 觸發。

```
ingest_gdelt ──┐
ingest_acled ──┼──→ normalize_pending（每 20 分鐘，讀 raw_events）
ingest_news  ──┘         │
                         ↓（邏輯順序，非強制 chain）
                  ai_enrich_pending（每 30 分鐘）
                         │
                         ↓（邏輯順序，非強制 chain）
                  score_and_aggregate（每小時 :55）
                  ⚠️ 排在 :55 是為了讓 ai_enrich_pending 有足夠時間完成（最少 25 分鐘窗口）
                  事件若尚未 AI 分析，評分引擎使用 event_dimensions（source='rule'）
                         │
                         ↓（唯一的 .delay() 觸發）
                   refresh_cache
                         │
                (每日 06:00 UTC)↓
                  daily_summary_gen
```

---

## 9.5 任務重試策略

```python
@app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,          # 第一次重試等 60 秒
    autoretry_for=(Exception,),
    retry_backoff=True,              # 指數退避：60s → 120s → 240s
    retry_backoff_max=600,           # 最長等 10 分鐘
    retry_jitter=True                # 加入隨機抖動，避免 thundering herd
)
def ingest_gdelt(self):
    try:
        adapter = GDELTAdapter()
        raw_events = adapter.fetch()
        save_raw_events(raw_events)
    except Exception as exc:
        logger.error(f"GDELT ingest failed: {exc}")
        raise self.retry(exc=exc)
```

---

## 9.6 各任務規格

### `ingest_gdelt`

```
輸入：無（讀 GDELT lastupdate.txt 取最新檔案 URL）
輸出：寫入 raw_events（ON CONFLICT DO NOTHING）
超時：120 秒
重試：3 次，指數退避
失敗記錄：ingest_errors 表
```

### `normalize_pending`

```
輸入：SELECT * FROM raw_events WHERE normalized = FALSE LIMIT 500
輸出：寫入 events / event_countries / news_sources
超時：300 秒
重試：3 次
說明：批次處理，每次最多 500 筆，避免長時間鎖定
```

### `ai_enrich_pending`

```
輸入：SELECT * FROM events WHERE ai_analyzed = FALSE ORDER BY event_time DESC LIMIT 200
      （優先處理最新事件；每次最多 200 筆避免無限佔用 Worker）
輸出：寫入 event_ai_analysis（摘要、展示用維度）
      注意：不寫入 event_dimensions（該表由 Normalization Service 負責）
超時：600 秒（LLM 呼叫較慢）
重試：2 次（LLM 呼叫昂貴，減少重試）
批次大小：20 筆，批次間等待 1 秒
積壓告警：若 SELECT COUNT(*) FROM events WHERE ai_analyzed = FALSE > 1000，
          發出 WARNING log（提示 pipeline 健康問題）
```

### `score_and_aggregate`

```
輸入：過去 30 天內的所有事件
輸出：更新 event_scores / country_tension_daily / region_tension_daily / global_tension_daily
超時：300 秒
重試：3 次
說明：使用 UPSERT（ON CONFLICT DO UPDATE）確保冪等性
```

### `full_recalculate`

```
輸入：RECALCULATE_LOOKBACK_DAYS 環境變數指定的回溯天數（預設 90 天）
      若 DB 中最新 scoring_version 與環境變數相同，跳過執行（冪等保護）
輸出：重建該日期範圍的 event_scores、country_tension_daily、
      region_tension_daily、global_tension_daily（指定 scoring_version）
      舊版本資料不刪除，新舊版本並存
超時：3600 秒（最多 1 小時）
重試：不自動重試（需人工介入確認）
完成後：觸發 refresh_cache
說明：週日 02:00 UTC 執行，此時流量最低；若超過 60 分鐘仍未完成，
      發出 CRITICAL 告警
```

### `cleanup_old_cache`

```
執行內容：
  1. 刪除 Redis 中日期 > 90 天前的歷史 key（SCAN 模式匹配 map:heat:{old_date}:*）
  2. 清理 PostgreSQL：刪除 raw_events 中 fetched_at > 180 天且 normalized=TRUE 的資料
  3. 清理 PostgreSQL：刪除 ingest_errors 中 occurred_at > 30 天且 resolved=TRUE 的資料
注意：不清理 event_scores 和 *_tension_daily（這些是分析資料，長期保留）
```

所有 pipeline 任務設計為**可重複執行**，相同輸入不產生重複資料：

- `raw_events`：`UNIQUE(source_type, source_event_id)` + `ON CONFLICT DO NOTHING`
- `events`：`UNIQUE(event_id)` + `ON CONFLICT DO NOTHING`
- `*_tension_daily`：`UNIQUE(country/region_code, date, scoring_version)` + `ON CONFLICT DO UPDATE`
- `event_scores`：`UNIQUE(event_id, scoring_version)` + `ON CONFLICT DO UPDATE`

---

## 9.8 監控與告警

- **Flower** 提供 Web UI 查看任務執行狀態、失敗列表、Worker 狀態
- 任務失敗超過閾值時（如連續 3 次），寫入 `ingest_errors` 並可整合 Webhook 告警
- 關鍵任務（`score_and_aggregate`）若超過 2 小時未執行，觸發健康檢查告警

---

*文件版本：v1.1 | 2026-04-07（修正 C-7,I-4,I-7,I-8,I-14,M-5）*
