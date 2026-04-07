"""
評分引擎常數與公式
對應 docs/03-scoring-engine.md
"""

import math
from datetime import datetime, timezone


# ── Scope Weight（影響範圍乘數）────────────────────────────────────────────
def get_scope_weight(country_count: int) -> float:
    if country_count <= 1:
        return 1.0
    elif country_count == 2:
        return 1.2
    elif country_count <= 5:
        return 1.4
    else:
        return 1.6


# ── Geo Sensitivity（敏感區域乘數）─────────────────────────────────────────
# 以 ISO alpha-3 國家組合判斷地緣敏感度
# 多個區域適用時取最高值
GEO_SENSITIVITY_RULES: list[tuple[set, float]] = [
    # 台灣海峽：TWN + CHN
    ({"TWN", "CHN"}, 1.8),
    # 朝鮮半島：PRK + KOR
    ({"PRK", "KOR"}, 1.7),
    # 台灣（單獨）
    ({"TWN"}, 1.6),
    # 南海：TWN/VNM/PHL/MYS/BRN + CHN
    ({"VNM", "CHN"}, 1.6),
    ({"PHL", "CHN"}, 1.6),
    # 中東（含伊以衝突）
    ({"IRN", "ISR"}, 1.6),
    ({"IRN", "SAU"}, 1.5),
    # 霍爾木茲海峽：IRN + 波灣國家
    ({"IRN", "ARE"}, 1.5),
    ({"IRN", "KWT"}, 1.5),
    # 烏克蘭邊境
    ({"RUS", "UKR"}, 1.5),
    # 紅海：葉門 + 其他
    ({"YEM"}, 1.4),
    # 波羅的海：俄羅斯 + 波羅的海三國
    ({"RUS", "EST"}, 1.3),
    ({"RUS", "LVA"}, 1.3),
    ({"RUS", "LTU"}, 1.3),
    # 中東通用
    ({"IRN"}, 1.3),
    ({"ISR"}, 1.2),
    ({"IRQ"}, 1.2),
    ({"SYR"}, 1.2),
]

# 區域代碼地緣敏感度（補充）
GEO_SENSITIVITY_BY_REGION: dict[str, float] = {
    "middle_east": 1.4,
    "east_asia":   1.3,
    "europe":      1.2,
}


def get_geo_sensitivity(country_codes: list[str], region_code: str | None) -> float:
    """
    依國家組合計算地緣敏感乘數
    優先精確國家組合比對，再 fallback 到區域
    """
    code_set = set(country_codes)
    max_sensitivity = 1.0

    for required_set, multiplier in GEO_SENSITIVITY_RULES:
        if required_set.issubset(code_set):
            max_sensitivity = max(max_sensitivity, multiplier)

    # 區域 fallback
    if max_sensitivity == 1.0 and region_code:
        max_sensitivity = GEO_SENSITIVITY_BY_REGION.get(region_code, 1.0)

    return max_sensitivity


# ── Actor Importance（行為者重要性乘數）────────────────────────────────────
NUCLEAR_POWERS = {"USA", "RUS", "CHN", "GBR", "FRA", "IND", "PAK", "PRK", "ISR"}
REGIONAL_POWERS = {"IRN", "SAU", "TUR", "KOR", "JPN", "DEU", "BRA"}
INTL_ORGS = {"UNO", "NATO", "EUN", "ASN"}  # 近似代碼


def get_actor_importance(country_codes: list[str]) -> float:
    """取所有 actor 中最高乘數"""
    max_importance = 1.0
    for code in country_codes:
        if code in NUCLEAR_POWERS:
            max_importance = max(max_importance, 1.5)
        elif code in REGIONAL_POWERS:
            max_importance = max(max_importance, 1.3)
        elif code in INTL_ORGS:
            max_importance = max(max_importance, 1.2)
    return max_importance


# ── Time Decay（時間衰減）───────────────────────────────────────────────────
def time_decay(event_time: datetime, risk_or_relief: str,
               current_time: datetime | None = None) -> float:
    """
    指數衰減：risk 半衰期 10 天，relief 半衰期 3 天
    最低保留 1%
    """
    if current_time is None:
        current_time = datetime.now(timezone.utc)

    # 確保時區一致
    if event_time.tzinfo is None:
        event_time = event_time.replace(tzinfo=timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)

    days = (current_time - event_time).total_seconds() / 86400
    days = max(0.0, days)  # 未來事件不衰減

    half_life = 10.0 if risk_or_relief == "risk" else 3.0
    decay = math.exp(-0.693 * days / half_life)
    return max(0.01, decay)


# ── normalize_to_100（tanh 正規化）──────────────────────────────────────────
def normalize_to_100(raw_score: float, scale: float = 20.0) -> float:
    """
    tanh 壓縮至 0–100
    典型效果：raw=20 → 76.2, raw=10 → 46.2, raw=5 → 24.5
    """
    normalized = math.tanh(raw_score / scale) * 100
    return round(max(0.0, min(100.0, normalized)), 2)


# ── Role Weight（事件中的國家角色權重）──────────────────────────────────────
ROLE_WEIGHTS = {
    "initiator": 1.0,
    "target":    0.9,
    "affected":  0.6,
}


# ── World Tension 維度權重 ──────────────────────────────────────────────────
WORLD_TENSION_WEIGHTS = {
    "military":  0.35,
    "political": 0.20,
    "economic":  0.20,
    "social":    0.15,
    "cyber":     0.10,
}


# ── 分數等級定義 ────────────────────────────────────────────────────────────
def get_tension_band(score: float) -> tuple[str, str]:
    """回傳 (英文標籤, 中文標籤)"""
    if score < 20:
        return "Stable",   "平穩"
    elif score < 40:
        return "Watch",    "關注"
    elif score < 60:
        return "Elevated", "升溫"
    elif score < 80:
        return "High",     "高壓"
    else:
        return "Crisis",   "危機"
