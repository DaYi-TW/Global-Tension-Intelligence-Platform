# 03 — 緊張度評分引擎規格

## 3.1 設計原則

- **完全確定性**：相同輸入 → 相同輸出，無隨機性
- **可解釋性**：每個最終分數都可分解回原始事件與因子
- **可版本化**：評分規則變更時升版號，支援歷史分數並存與全量重算
- **AI 不介入**：LLM 產出僅作為語意標籤輔助，絕不影響數字分數

---

## 3.2 評分層級

```
事件層  Event Score
    ↓  聚合
國家層  Country Tension Score（0–100）
    ↓  聚合
區域層  Regional Tension Score（0–100）
    ↓  加權
全球層  World Tension Score（0–100）
```

---

## 3.3 事件分數公式

```
Event Score =
    Base Severity
  × Scope Weight
  × Geo Sensitivity
  × Actor Importance
  × Source Confidence
  × Time Decay
```

### Base Severity（事件本身嚴重度）

由事件類型查規則表，範圍 0.0–1.0：

| event_type | base_severity | risk_or_relief |
|---|---|---|
| `nuclear_threat` | 0.95 | risk |
| `declaration_of_war` | 0.92 | risk |
| `military_strike` | 0.88 | risk |
| `military_invasion` | 0.85 | risk |
| `nuclear_test` | 0.90 | risk |
| `ceasefire_violation` | 0.72 | risk |
| `cyberattack_critical` | 0.70 | risk |
| `economic_sanctions` | 0.65 | risk |
| `diplomatic_expulsion` | 0.60 | risk |
| `military_exercise` | 0.55 | risk |
| `military_clash` | 0.75 | risk |
| `explosion` | 0.70 | risk |
| `political_coup` | 0.80 | risk |
| `martial_law` | 0.75 | risk |
| `riot` | 0.50 | risk |
| `protest_large` | 0.40 | risk |
| `refugee_crisis` | 0.55 | risk |
| `energy_disruption` | 0.65 | risk |
| `trade_war_escalation` | 0.60 | risk |
| `ceasefire_agreement` | 0.80 | relief |
| `peace_talks_success` | 0.75 | relief |
| `military_withdrawal` | 0.70 | relief |
| `diplomatic_restore` | 0.65 | relief |
| `sanctions_lifted` | 0.60 | relief |
| `peace_talks_start` | 0.50 | relief |
| `military_exercise_halt` | 0.45 | relief |
| `economic_cooperation` | 0.45 | relief |
| `goodwill_statement` | 0.25 | relief |
| `leader_meeting` | 0.30 | relief |

### Scope Weight（影響範圍）

| 範圍 | 判斷條件 | 乘數 |
|---|---|---|
| 單一國家 | country_codes 長度 = 1 | 1.0 |
| 雙邊 | country_codes 長度 = 2 | 1.2 |
| 區域 | country_codes 長度 3–5 或含區域關鍵字 | 1.4 |
| 全球 | country_codes > 5 或 region = "global" | 1.6 |

### Geo Sensitivity（敏感區域乘數）

| 區域 / 地點 | 乘數 |
|---|---|
| 台灣海峽（Taiwan Strait） | 1.8 |
| 朝鮮半島（Korean Peninsula） | 1.7 |
| 南海（South China Sea） | 1.6 |
| 中東（Middle East，含伊以衝突） | 1.6 |
| 霍爾木茲海峽（Strait of Hormuz） | 1.5 |
| 烏克蘭邊境（Ukraine Border） | 1.5 |
| 紅海（Red Sea） | 1.4 |
| 波羅的海（Baltic Sea） | 1.3 |
| 其他區域 | 1.0 |

判斷邏輯：優先檢查 `region_code`，若涉及上表國家組合則套用對應乘數，多個敏感區域取最高值。

### Actor Importance（行為者重要性）

| 行為者類型 | 乘數 |
|---|---|
| 核武大國（USA, RUS, CHN, GBR, FRA, IND, PAK, PRK, ISR） | 1.5 |
| 區域強國（IRN, SAU, TUR, KOR, JPN, DEU, BRA） | 1.3 |
| 國際組織（UN, NATO, EU, ASEAN） | 1.2 |
| 其他國家 | 1.0 |

多個 actor 時取最高乘數。

### Source Confidence（來源可信度）

```
source_confidence = min(1.0, 0.5 + 0.1 × source_count)

修正：
  - ACLED 來源：×1.1（高可信度加成）
  - 單一新聞來源且無結構化事件佐證：×0.8
  - 最終 clip 至 [0.3, 1.0]
```

### Time Decay（時間衰減）

```python
import math

def time_decay(event_time, risk_or_relief, current_time):
    days = (current_time - event_time).total_seconds() / 86400

    if risk_or_relief == "risk":
        half_life = 10.0   # 10 天半衰期（飛彈攻擊等約 7–14 天）
    else:
        half_life = 3.0    # 3 天半衰期（善意表態等 2–3 天）

    decay = math.exp(-0.693 * days / half_life)
    return max(0.01, decay)   # 最低保留 1%，不完全消失
```

特殊規則：
- 停火協議若有後續「fulfillment」事件，則 half_life 延長至 14 天
- 宣戰事件衰減暫停，直到後續緩和事件出現

---

## 3.4 國家張力分數計算

### 聚合邏輯

```python
def compute_country_tension(country_code, target_date):
    # 取得過去 30 天內影響該國的所有有效事件
    events = get_active_events_for_country(country_code, target_date, window_days=30)

    risk_total = 0.0
    relief_total = 0.0
    dim_scores = defaultdict(float)

    for event in events:
        score = compute_event_score(event, current_time=target_date)
        role_weight = {"initiator": 1.0, "target": 0.9, "affected": 0.6}[event.role]
        weighted = score * role_weight

        if event.risk_or_relief == "risk":
            risk_total += weighted
            # 累加維度分數
            for dim in ["military", "political", "economic", "social", "cyber"]:
                dim_scores[dim] += weighted * event.dimensions[dim]
        else:
            relief_total += weighted

    # 淨張力公式
    net_raw = risk_total - 0.7 * relief_total

    # 正規化至 0–100（使用 sigmoid-like 壓縮）
    net_tension = normalize_to_100(net_raw)

    return {
        "risk_score": risk_total,
        "relief_score": relief_total,
        "net_tension": net_tension,
        "dimensions": {dim: normalize_to_100(v) for dim, v in dim_scores.items()}
    }
```

### 正規化函數

```python
def normalize_to_100(raw_score, scale=20.0):
    """
    使用 tanh 壓縮，避免極端事件讓分數無限上升
    scale 為調校參數，可根據歷史資料校正
    """
    import math
    normalized = math.tanh(raw_score / scale) * 100
    return round(max(0.0, min(100.0, normalized)), 2)
```

---

## 3.5 區域張力分數計算

```python
def compute_region_tension(region_code, target_date):
    countries = get_countries_in_region(region_code)
    country_tensions = [get_country_tension(c, target_date) for c in countries]

    # 區域分數 = 區域內國家的加權平均（以人口/GDP 或等權）
    # MVP 階段使用等權平均，後續可引入權重
    scores = [ct.net_tension for ct in country_tensions]
    region_score = sum(scores) / len(scores) if scores else 0

    # 取區域內最高張力國家作為 top_country_codes
    top_countries = sorted(countries, key=lambda c: get_country_tension(c, target_date).net_tension, reverse=True)[:3]

    return {
        "net_tension": round(region_score, 2),
        "top_country_codes": [c.code for c in top_countries]
    }
```

---

## 3.6 全球張力分數計算

```
World Tension =
    0.35 × Military（全球軍事子維度均值）
  + 0.20 × Political（全球政治子維度均值）
  + 0.15 × Social（全球社會子維度均值）
  + 0.20 × Economic（全球經濟子維度均值）
  + 0.10 × Cyber（全球網路子維度均值）
```

各維度值來源：當日 `country_tension_daily` 各欄的加權聚合。

---

## 3.7 分數級距定義

| 分數範圍 | 英文標籤 | 中文標籤 | 說明 |
|---|---|---|---|
| 0–19 | Stable | 平穩 | 全球局勢大致穩定 |
| 20–39 | Watch | 關注 | 有區域摩擦，尚未形成高壓 |
| 40–59 | Elevated | 升溫 | 區域衝突與經濟壓力上升 |
| 60–79 | High | 高壓 | 多區域同時存在軍事與經濟風險 |
| 80–100 | Crisis | 危機 | 可能出現重大跨國衝突或供應鏈衝擊 |

---

## 3.8 評分版本管理

- 每次規則表或公式變動，`scoring_version` 遞增（`v1.0` → `v1.1` → `v2.0`）
- `event_scores` 和每日快照表均記錄 `scoring_version`
- 全量重算指令：`POST /admin/recalculate?version=v1.1&from=2026-01-01`
- 版本升級不刪除舊版分數，保留比較能力

---

## 3.9 可解釋性輸出

每個國家分數的 API 回應包含：

```json
{
  "country_code": "IRN",
  "net_tension": 87.3,
  "top_contributing_events": [
    {
      "event_id": "evt_20260407_001",
      "title": "Missile strike on southern region",
      "score_contribution": 18.5,
      "factors": {
        "base_severity": 0.88,
        "scope_weight": 1.3,
        "geo_sensitivity": 1.6,
        "actor_importance": 1.5,
        "source_confidence": 0.91,
        "time_decay": 1.0
      }
    }
  ],
  "top_relief_events": [...]
}
```

---

*文件版本：v1.0 | 2026-04-07*
