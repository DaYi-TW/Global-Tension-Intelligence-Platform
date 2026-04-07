# 07 — 部署架構

## 7.1 目錄結構

```
global-tension-platform/
├── frontend/               # React 應用
├── backend/
│   ├── app/                # FastAPI 主應用
│   │   ├── api/            # Route handlers
│   │   ├── services/       # 業務邏輯層
│   │   ├── models/         # SQLAlchemy models
│   │   ├── schemas/        # Pydantic schemas
│   │   └── core/           # 設定、DB 連線、Redis
│   ├── pipeline/
│   │   ├── ingestion/      # Data Ingestion Adapters
│   │   ├── normalization/  # Normalization Service
│   │   ├── ai_analysis/    # AI Analysis Service
│   │   ├── scoring/        # Tension Scoring Engine
│   │   └── tasks.py        # Celery task 定義
│   ├── alembic/            # DB migrations
│   └── tests/
├── nginx/
│   └── nginx.conf
├── docker-compose.yml
├── docker-compose.prod.yml
└── .env.example
```

---

## 7.2 Docker Compose（開發環境）

```yaml
# docker-compose.yml
version: "3.9"

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: tension_db
      POSTGRES_USER: tension_user
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"   # 開發環境對外，生產環境移除
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U tension_user -d tension_db"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"   # 開發環境對外
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  api:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
    environment:
      DATABASE_URL: postgresql+asyncpg://tension_user:${POSTGRES_PASSWORD}@postgres:5432/tension_db
      REDIS_URL: redis://redis:6379/0
      CELERY_BROKER_URL: redis://redis:6379/1
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./backend:/app   # 開發熱重載
    ports:
      - "8000:8000"

  worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: celery -A pipeline.celery_app worker --loglevel=info --concurrency=4
    environment:
      DATABASE_URL: postgresql+asyncpg://tension_user:${POSTGRES_PASSWORD}@postgres:5432/tension_db
      REDIS_URL: redis://redis:6379/0
      CELERY_BROKER_URL: redis://redis:6379/1
      GDELT_ENABLED: "true"
      ACLED_API_KEY: ${ACLED_API_KEY}
      ACLED_EMAIL: ${ACLED_EMAIL}
      NEWSAPI_KEY: ${NEWSAPI_KEY}
      LLM_API_KEY: ${LLM_API_KEY}
      LLM_MODEL: ${LLM_MODEL}
    depends_on:
      - postgres
      - redis

  beat:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: celery -A pipeline.celery_app beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
    environment:
      DATABASE_URL: postgresql+asyncpg://tension_user:${POSTGRES_PASSWORD}@postgres:5432/tension_db
      CELERY_BROKER_URL: redis://redis:6379/1
    depends_on:
      - postgres
      - redis

  flower:
    image: mher/flower:2.0
    command: celery flower --broker=redis://redis:6379/1
    ports:
      - "5555:5555"
    depends_on:
      - redis

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"

  nginx:
    image: nginx:1.25-alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
    depends_on:
      - api
      - frontend

volumes:
  postgres_data:
  redis_data:
```

---

## 7.3 Nginx 設定

```nginx
# nginx/nginx.conf
events {
    worker_connections 1024;
}

http {
    # Gzip 壓縮
    gzip on;
    gzip_types application/json text/css application/javascript;

    # API 服務 upstream
    upstream api_backend {
        server api:8000;
    }

    server {
        listen 80;
        server_name localhost;

        # API 路由
        location /api/ {
            proxy_pass http://api_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

            # 快取靜態 API 回應（由 FastAPI 控制 Cache-Control header）
            proxy_cache_bypass $http_pragma;

            # Timeout 設定
            proxy_connect_timeout 10s;
            proxy_read_timeout 30s;
        }

        # Admin API（限內網）
        location /admin/ {
            allow 10.0.0.0/8;
            allow 172.16.0.0/12;
            deny all;
            proxy_pass http://api_backend;
        }

        # 前端靜態檔案
        location / {
            root /usr/share/nginx/html;
            index index.html;
            try_files $uri $uri/ /index.html;  # SPA fallback

            # 靜態資源長快取
            location ~* \.(js|css|png|jpg|ico|woff2)$ {
                expires 1y;
                add_header Cache-Control "public, immutable";
            }
        }
    }
}
```

---

## 7.4 Backend Dockerfile

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

# 安裝 Python 依賴
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 執行 DB migration（生產環境由 entrypoint script 執行）
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 7.5 環境變數（.env.example）

```dotenv
# PostgreSQL
POSTGRES_PASSWORD=your_secure_password

# Redis
REDIS_URL=redis://redis:6379/0

# Celery
CELERY_BROKER_URL=redis://redis:6379/1

# 資料來源
GDELT_ENABLED=true
ACLED_API_KEY=your_acled_key
ACLED_EMAIL=your@email.com
NEWSAPI_KEY=your_newsapi_key

# AI / LLM
LLM_API_KEY=your_llm_key
LLM_MODEL=claude-3-7-sonnet-20250219
LLM_PROMPT_VERSION=v1.0

# 評分引擎
SCORING_VERSION=v1.0
SCORING_SCALE_FACTOR=20.0

# 應用設定
APP_ENV=development    # development | production
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000
```

---

## 7.6 DB Migration 流程

使用 **Alembic** 管理 schema 版本：

```bash
# 初始化（首次）
alembic init alembic

# 建立 migration
alembic revision --autogenerate -m "add event_scores table"

# 套用 migration
alembic upgrade head

# 回滾一版
alembic downgrade -1
```

---

## 7.7 網路安全設計

```
外部可訪問：
  ├── 80/443 → Nginx（HTTP/HTTPS）

僅 Docker 內網：
  ├── api:8000      → 只接受 Nginx proxy 連線
  ├── postgres:5432 → 只接受 api / worker 連線
  └── redis:6379    → 只接受 api / worker / beat 連線

管理介面（限內網 IP）：
  └── flower:5555   → Celery 任務監控
  └── /admin/*      → Admin API
```

---

*文件版本：v1.0 | 2026-04-07*
