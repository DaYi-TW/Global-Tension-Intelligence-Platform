# 06 — 快取策略

## 6.1 設計原則

- Query API **不做即時運算**，所有資料從 Redis 讀取；Redis miss 才 fallback 至 PostgreSQL
- Worker 完成分數更新後**主動 INVALIDATE** 相關 key（不等 TTL 自然過期）
- Redis 不可用時，API **自動降級**至直接查詢 PostgreSQL（功能不中斷，僅效能下降）

---

## 6.2 Redis Key 設計

### Key 命名規則

```
{namespace}:{識別子}:{細項}
```

### 完整 Key 清單

| Redis Key | TTL | 更新時機 | 說明 |
|---|---|---|---|
| `dashboard:overview` | 15 分鐘 | 每次 score_and_aggregate 完成 | 首頁總覽 |
| `tension:global:trend:{range}` | 1 小時 | 每次 score_and_aggregate 完成 | 全球趨勢，range = 7d\|30d\|90d\|1y |
| `tension:regions:{date}` | 1 小時 | 每次 score_and_aggregate 完成 | 區域排行 |
| `tension:countries:{region}:{date}` | 1 小時 | 每次 score_and_aggregate 完成 | 國家排行（按區域） |
| `map:heat:{date}:{dimension}` | 15 分鐘 | 每次 score_and_aggregate 完成 | 地圖熱點 |
| `event:{event_id}` | 24 小時 | 事件建立或 AI 分析完成時 | 事件詳情 |
| `country:{country_code}:{trend_range}` | 1 小時 | 每次 score_and_aggregate 完成 | 國家詳情 |
| `region:{region_code}` | 1 小時 | 每次 score_and_aggregate 完成 | 區域詳情 |
| `events:list:{hash(query_params)}` | 5 分鐘 | 不主動清除（短 TTL） | 事件列表查詢結果 |

---

## 6.3 快取讀寫流程

```python
async def get_dashboard_overview():
    # 1. 嘗試讀取 Redis
    cached = await redis.get("dashboard:overview")
    if cached:
        return json.loads(cached)

    # 2. Redis Miss → 查詢 PostgreSQL
    data = await db.query_dashboard_overview()

    # 3. 寫回 Redis
    await redis.setex("dashboard:overview", 900, json.dumps(data))

    return data
```

---

## 6.4 主動失效（Cache Invalidation）

Worker 完成 `score_and_aggregate` 任務後，呼叫 Cache Writer：

```python
async def invalidate_and_refresh_cache(target_date: date):
    keys_to_delete = [
        "dashboard:overview",
        f"tension:regions:{target_date}",
        f"map:heat:{target_date}:overall",
        f"map:heat:{target_date}:military",
        # ... 其他維度
    ]

    # 刪除舊 key
    await redis.delete(*keys_to_delete)

    # 趨勢 key（範圍型）
    for range_key in ["7d", "30d", "90d", "1y"]:
        await redis.delete(f"tension:global:trend:{range_key}")

    # 主動預熱最常用的 key
    await preheat_dashboard_cache()
    await preheat_trend_cache("30d")
    await preheat_map_heat_cache(target_date)
```

---

## 6.5 Redis 不可用降級策略

```python
class CacheWithFallback:
    async def get_or_compute(self, key: str, compute_fn, ttl: int):
        try:
            cached = await redis.get(key)
            if cached:
                return json.loads(cached)
        except RedisConnectionError:
            logger.warning(f"Redis unavailable, falling back to DB for key={key}")
            # 直接執行計算函數，不使用快取
            return await compute_fn()

        result = await compute_fn()
        try:
            await redis.setex(key, ttl, json.dumps(result))
        except RedisConnectionError:
            pass  # 寫入失敗不影響回傳
        return result
```

---

## 6.6 快取暖機（Preheat）策略

系統啟動時與每次重算完成後，預先填充最常訪問的 key：

```
優先順序：
1. dashboard:overview
2. tension:global:trend:30d
3. tension:regions:{today}
4. map:heat:{today}:overall
5. tension:countries:*:{today}（所有區域）
```

---

## 6.7 事件列表快取特殊處理

事件列表查詢條件組合多，使用短 TTL（5 分鐘）搭配查詢參數 hash：

```python
import hashlib, json

def make_events_cache_key(query_params: dict) -> str:
    sorted_params = json.dumps(query_params, sort_keys=True)
    h = hashlib.md5(sorted_params.encode()).hexdigest()[:12]
    return f"events:list:{h}"
```

---

*文件版本：v1.0 | 2026-04-07*
