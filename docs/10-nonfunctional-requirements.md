# 10 — 非功能性需求

## 10.1 效能目標

| API | 目標回應時間 | 備註 |
|---|---|---|
| `GET /api/dashboard/overview` | < 200ms | Redis 命中情況 |
| `GET /api/tension/global/trend` | < 300ms | Redis 命中情況 |
| `GET /api/events` | < 500ms | DB 查詢（有索引） |
| `GET /api/events/{id}` | < 300ms | Redis 命中情況 |
| `GET /api/map/heat` | < 200ms | Redis 命中情況 |
| `GET /api/countries/{code}` | < 500ms | Redis 命中情況 |
| Redis Miss 降級（直查 DB） | < 2s | 可接受的降級效能 |

**整體目標**：90th percentile < 500ms，99th percentile < 2s

---

## 10.2 可靠性

| 場景 | 對策 |
|---|---|
| 外部資料源中斷 | Adapter 層隔離，單一來源失敗不影響整體；保留上次成功資料 |
| AI API 不可用 | Fallback 至規則推斷，標記 `confidence=0.3`；排程重試 |
| Redis 不可用 | API 自動降級至直查 PostgreSQL，功能不中斷 |
| PostgreSQL 異常 | API 回傳 503；Worker 任務進入重試隊列 |
| Worker 崩潰 | Celery 自動重試，Beat 定時補觸發 |
| 評分引擎異常 | 保留上一次有效快照，寫入告警日誌 |
| 單次 DB 寫入失敗 | Transaction rollback + 任務重排入隊列 |

---

## 10.3 可解釋性

每個緊張度分數都必須可追溯：

```
全球緊張度 68.5
└── 中東 82.1（最高貢獻區域）
    └── 伊朗 87.3（最高貢獻國家）
        └── evt_20260407_001（最高貢獻事件，+18.5）
            └── base_severity=0.88 × geo_sensitivity=1.6 × actor_importance=1.5 × ...
```

API 回應中的 `scoring_breakdown` 與 `top_contributing_events` 欄位實現此要求。

---

## 10.4 可維護性

- **模組化**：Ingestion / Normalization / AI / Scoring 各自獨立，可單獨測試與部署
- **版本管理**：評分規則以 `scoring_version` 版本化，支援並存與重算
- **Prompt 版本管理**：AI Prompt 以 `prompt_version` 追蹤，可比較效果差異
- **API 文件**：FastAPI 自動產生 OpenAPI（Swagger UI：`/docs`，ReDoc：`/redoc`）
- **Migration**：Alembic 管理 DB schema 變更，版本可前進/回滾
- **日誌**：結構化 JSON logging，包含 task_id、event_id、duration 等欄位

---

## 10.5 可擴充性

| 擴充方向 | 設計支援 |
|---|---|
| 新增資料來源 | 繼承 `BaseAdapter`，實作 `fetch()` 即可插入 |
| 新增評分維度 | 在 `event_dimensions` 新增欄位，更新 `scoring_version` |
| 多語言支援 | `summary_zh` / `summary_en` 已分離，可再加語言欄位 |
| 新增區域 | 更新 `region_code` 映射表，無需改動核心邏輯 |
| 金融連動模組 | 獨立 Adapter + 新資料表，不影響現有 pipeline |
| 情境模擬 | 新增 simulation API，注入臨時事件不寫入主 DB |
| 全文搜尋 | 整合 Elasticsearch（`events.title` + `summary_zh` 索引） |

---

## 10.6 評分版本管理規範

| 版本號格式 | 適用情境 |
|---|---|
| `v1.0` → `v1.1` | 微調參數（衰減係數、地理乘數）|
| `v1.x` → `v2.0` | 公式結構性變更（新增維度、改變聚合方式）|

版本升級流程：
1. 更新規則設定（config file 或 DB 規則表）
2. 遞增 `SCORING_VERSION` 環境變數
3. 觸發 `full_recalculate` 任務（可指定日期範圍）
4. 新舊版本快照並存於 `event_scores`（`UNIQUE(event_id, scoring_version)`）
5. API 預設回傳最新版本分數

---

## 10.7 測試策略

| 測試類型 | 工具 | 覆蓋範圍 |
|---|---|---|
| 單元測試 | pytest | Scoring Engine（最優先）、Normalization 邏輯 |
| 整合測試 | pytest + testcontainers | Pipeline 端到端流程（含 DB） |
| API 測試 | pytest + httpx | 所有 API Endpoint |
| 評分驗證測試 | 手動建立黃金資料集 | 確保評分規則符合預期 |

評分引擎測試為最高優先級——必須有詳盡的單元測試，確保每個因子的計算結果符合預期。

---

## 10.8 Phase 1 MVP 驗收標準

| 項目 | 標準 |
|---|---|
| 資料抓取 | 可定時抓取並儲存 GDELT + ACLED 事件資料 |
| 事件正規化 | 成功轉換為統一 schema，國家代碼正確 |
| 緊張度計算 | 成功產出世界 / 區域 / 國家緊張度分數 |
| Dashboard API | 回傳正確且完整的 overview 資料 |
| 前端 Dashboard | 顯示世界緊張度、地圖熱區、趨勢圖、主要事件 |
| 事件列表 | 可依條件篩選且分頁正確 |
| AI 摘要 | 能生成每日全球摘要文字 |
| 效能 | Dashboard API < 2s（含 Redis miss 情況） |
| 穩定性 | 7 天連續運行，資料管線無重大中斷 |

---

*文件版本：v1.0 | 2026-04-07*
