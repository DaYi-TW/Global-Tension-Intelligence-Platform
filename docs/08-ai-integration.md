# 08 — AI 整合規格

## 8.1 設計原則

- **AI 只做語意輔助**，不影響任何數字分數計算
- **評分引擎是真相來源**，AI 輸出是補充標籤
- AI 分析失敗不阻斷流程，使用 fallback 預設值
- 記錄 `model_version` 與 `prompt_version`，支援效果追蹤與版本回滾

---

## 8.2 AI 使用場景

| 場景 | 輸入 | 輸出 | 表格 |
|---|---|---|---|
| 事件摘要與分類 | 事件標題、內容、國家 | summary_zh, impact_direction, dimensions, confidence, explanation | `event_ai_analysis` |
| 每日全球摘要 | 當日 top events + 全球分數變化 | ai_summary 文字段落 | `global_tension_daily.ai_summary` |
| 區域/國家摘要 | 區域/國家近期事件 | 文字摘要 | 動態生成，不持久化 |

---

## 8.3 事件分析 Prompt 規格

### System Prompt（版本 v1.0）

```
你是一位地緣政治分析師。請分析以下事件並以 JSON 格式輸出分析結果。

規則：
1. summary_zh：100 字以內的繁體中文摘要，說明事件本質與直接影響
2. impact_direction：判斷事件是否升高（risk）或降低（relief）全球局勢緊張度，若無明確方向則為 neutral
3. dimensions：各維度對事件的相關性（0.0 到 1.0），不代表嚴重度，代表「此維度有多相關」
4. confidence：你對本次判斷的信心程度（0.0 到 1.0）
5. explanation：50 字以內說明為何如此分類

請只輸出 JSON，不要加任何說明文字。
```

### User Prompt 模板

```
事件標題：{title}
涉及國家：{country_names}
事件類型（初步）：{event_type}
原始描述：{content}
新聞來源數量：{source_count}
發生時間：{event_time}
```

### 預期 JSON 輸出格式

```json
{
  "summary_zh": "以色列對伊朗南部石油設施發動空襲，造成部分設施損毀，引發中東局勢急劇升溫。",
  "impact_direction": "risk",
  "dimensions": {
    "military":  0.92,
    "political": 0.65,
    "economic":  0.55,
    "social":    0.15,
    "cyber":     0.05
  },
  "confidence": 0.88,
  "explanation": "直接軍事攻擊核心設施，涉及中東兩大對立強國，軍事與政治衝擊最為顯著。"
}
```

---

## 8.4 AI 呼叫流程

```python
async def analyze_event(event: Event) -> AIAnalysisResult:
    prompt = build_event_prompt(event)

    try:
        response = await llm_client.complete(
            system=SYSTEM_PROMPT_V1,
            user=prompt,
            max_tokens=500,
            temperature=0.1     # 低溫度確保穩定性
        )
        result = parse_and_validate(response)

    except LLMAPIError as e:
        logger.error(f"LLM API error for event {event.event_id}: {e}")
        result = get_fallback_analysis(event)   # 規則 fallback

    except JSONParseError:
        logger.warning(f"LLM output not valid JSON for {event.event_id}, using fallback")
        result = get_fallback_analysis(event)

    return result
```

### Fallback 規則（AI 失敗時）

```python
def get_fallback_analysis(event: Event) -> AIAnalysisResult:
    """當 AI 無法分析時，使用基本規則填充"""
    return AIAnalysisResult(
        summary_zh=None,                    # 不顯示摘要
        impact_direction=event.risk_or_relief,  # 沿用正規化時的判斷
        dimensions=get_rule_based_dimensions(event.event_type),
        confidence=0.3,                     # 低信心值，前端可顯示警示
        explanation="[AI 分析暫時不可用，使用規則推斷]",
        model_version="fallback",
        prompt_version="v0"
    )
```

---

## 8.5 每日摘要 Prompt（版本 v1.0）

### 觸發時機
每日 06:00 UTC，由 Celery beat 觸發。

### Prompt 模板

```
今日（{date}）世界局勢資料：

全球緊張度：{global_score}（較昨日 {delta:+.1f}）
軍事：{military} | 政治：{political} | 經濟：{economic} | 社會：{social} | 網路：{cyber}

今日主要利空事件：
{top_risk_events_list}

今日主要利多事件：
{top_relief_events_list}

請用 150 字以內的繁體中文，撰寫今日世界局勢日報摘要。
格式：「今日世界緊張度 XX，較昨日[上升/下降] X 點。主因為...。緩和因素包括...。整體走向...。」
請只輸出摘要文字，不要加標題或說明。
```

---

## 8.6 批次處理設計

```python
BATCH_SIZE = 20         # 每批最多 20 筆
RATE_LIMIT_DELAY = 1.0  # 批次間等待秒數

async def batch_analyze_events(event_ids: List[int]):
    events = await db.get_events_by_ids(event_ids)
    batches = [events[i:i+BATCH_SIZE] for i in range(0, len(events), BATCH_SIZE)]

    for batch in batches:
        tasks = [analyze_event(e) for e in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for event, result in zip(batch, results):
            if isinstance(result, Exception):
                logger.error(f"Failed to analyze {event.event_id}: {result}")
                await db.save_ai_analysis(event.id, get_fallback_analysis(event))
            else:
                await db.save_ai_analysis(event.id, result)
                await db.mark_ai_analyzed(event.id)

        await asyncio.sleep(RATE_LIMIT_DELAY)  # 避免 rate limit
```

---

## 8.7 Schema 驗證

```python
from pydantic import BaseModel, Field, validator

class AIAnalysisOutput(BaseModel):
    summary_zh:       str | None = None
    impact_direction: str        = Field(..., pattern="^(risk|relief|neutral)$")
    dimensions: dict  = Field(...)
    confidence:       float      = Field(..., ge=0.0, le=1.0)
    explanation:      str | None = None

    @validator("dimensions")
    def validate_dimensions(cls, v):
        required = {"military", "political", "economic", "social", "cyber"}
        if not required.issubset(v.keys()):
            raise ValueError("Missing dimension keys")
        for key, val in v.items():
            if not (0.0 <= val <= 1.0):
                raise ValueError(f"Dimension {key} out of range")
        return v
```

---

## 8.8 版本管理

| 版本 | 變更內容 | 日期 |
|---|---|---|
| `v1.0` | 初版 Prompt，事件分類 + 摘要 | 2026-04-07 |

升級版本時，新 Prompt 以新版號寫入 DB，不影響歷史資料。
可透過 Admin API 觸發批次重新分析指定日期範圍的事件。

---

*文件版本：v1.0 | 2026-04-07*
