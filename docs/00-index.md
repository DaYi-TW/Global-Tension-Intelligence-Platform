# Global Tension Intelligence Platform — 文件索引

> 全球局勢緊張度分析平台 技術規格文件集

---

## 文件清單

| 文件 | 說明 |
|---|---|
| [01-architecture-overview.md](./01-architecture-overview.md) | 系統整體架構、設計哲學、模組關係圖 |
| [02-data-pipeline.md](./02-data-pipeline.md) | 資料管線流程、各 Service 規格、Adapter 設計 |
| [03-scoring-engine.md](./03-scoring-engine.md) | 緊張度評分引擎詳細規格、公式、規則表 |
| [04-database-schema.md](./04-database-schema.md) | 完整資料庫 Schema（DDL）與索引設計 |
| [05-api-spec.md](./05-api-spec.md) | 所有 API Endpoint 的 Request / Response 規格 |
| [06-caching-strategy.md](./06-caching-strategy.md) | Redis 快取策略、TTL 設計、失效機制 |
| [07-deployment.md](./07-deployment.md) | Docker Compose 部署架構、環境設定、Nginx 設定 |
| [08-ai-integration.md](./08-ai-integration.md) | AI / LLM 整合規格、Prompt 設計、版本管理 |
| [09-scheduler-worker.md](./09-scheduler-worker.md) | 背景排程設計、Celery 任務清單、錯誤處理 |
| [10-nonfunctional-requirements.md](./10-nonfunctional-requirements.md) | 效能目標、可靠性、可解釋性、評分版本管理 |
| [11-frontend-spec.md](./11-frontend-spec.md) | 前端 UI/UX 規格：HoI4 風格地圖、時間軸、頁面結構、元件設計 |

---

## 開發分期對照

| Phase | 重點 | 對應文件 |
|---|---|---|
| Phase 1 MVP | 資料管線、評分引擎、Dashboard | 01–07 |
| Phase 2 增強版 | 詳情頁、搜尋、多源融合 | 04、05 擴充 |
| Phase 3 進階版 | 情境模擬、金融連動、預警 | 另立規格 |

---

*最後更新：2026-04-07*
