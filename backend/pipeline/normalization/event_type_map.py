"""
事件類型映射表與維度推斷
對應 docs/02-data-pipeline.md §2.4 與 docs/03-scoring-engine.md §3.3
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class EventTypeRule:
    event_type:        str
    primary_dimension: str
    base_severity:     float
    risk_or_relief:    str   # 'risk' | 'relief' | 'neutral'


# ── 完整事件類型規則表（對應 03-scoring-engine §3.3）────────────────────────
EVENT_TYPE_RULES: dict[str, EventTypeRule] = {
    "nuclear_threat":       EventTypeRule("nuclear_threat",       "military",  0.95, "risk"),
    "nuclear_test":         EventTypeRule("nuclear_test",         "military",  0.90, "risk"),
    "declaration_of_war":   EventTypeRule("declaration_of_war",   "military",  0.92, "risk"),
    "military_invasion":    EventTypeRule("military_invasion",    "military",  0.85, "risk"),
    "military_strike":      EventTypeRule("military_strike",      "military",  0.88, "risk"),
    "military_clash":       EventTypeRule("military_clash",       "military",  0.75, "risk"),
    "ceasefire_violation":  EventTypeRule("ceasefire_violation",  "military",  0.72, "risk"),
    "military_exercise":    EventTypeRule("military_exercise",    "military",  0.55, "risk"),
    "explosion":            EventTypeRule("explosion",            "military",  0.70, "risk"),
    "political_coup":       EventTypeRule("political_coup",       "political", 0.80, "risk"),
    "martial_law":          EventTypeRule("martial_law",          "political", 0.75, "risk"),
    "diplomatic_expulsion": EventTypeRule("diplomatic_expulsion", "political", 0.60, "risk"),
    "political_arrest":     EventTypeRule("political_arrest",     "political", 0.55, "risk"),
    "cyberattack_critical": EventTypeRule("cyberattack_critical", "cyber",     0.70, "risk"),
    "economic_sanctions":   EventTypeRule("economic_sanctions",   "economic",  0.65, "risk"),
    "energy_disruption":    EventTypeRule("energy_disruption",    "economic",  0.65, "risk"),
    "trade_war_escalation": EventTypeRule("trade_war_escalation", "economic",  0.60, "risk"),
    "refugee_crisis":       EventTypeRule("refugee_crisis",       "social",    0.55, "risk"),
    "riot":                 EventTypeRule("riot",                 "social",    0.50, "risk"),
    "protest_large":        EventTypeRule("protest_large",        "social",    0.40, "risk"),
    # relief events
    "ceasefire_agreement":   EventTypeRule("ceasefire_agreement",   "military",  0.80, "relief"),
    "peace_talks_success":   EventTypeRule("peace_talks_success",   "political", 0.75, "relief"),
    "military_withdrawal":   EventTypeRule("military_withdrawal",   "military",  0.70, "relief"),
    "diplomatic_restore":    EventTypeRule("diplomatic_restore",    "political", 0.65, "relief"),
    "sanctions_lifted":      EventTypeRule("sanctions_lifted",      "economic",  0.60, "relief"),
    "peace_talks_start":     EventTypeRule("peace_talks_start",     "political", 0.50, "relief"),
    "military_exercise_halt":EventTypeRule("military_exercise_halt","military",  0.45, "relief"),
    "economic_cooperation":  EventTypeRule("economic_cooperation",  "economic",  0.45, "relief"),
    "leader_meeting":        EventTypeRule("leader_meeting",        "political", 0.30, "relief"),
    "goodwill_statement":    EventTypeRule("goodwill_statement",    "political", 0.25, "relief"),
}

# ── GDELT Themes → platform event_type 映射 ─────────────────────────────────
# GDELT Themes 為分號分隔的字串，優先匹配最嚴重的主題
# 順序重要：越前面優先級越高（越嚴重）
GDELT_THEME_TO_EVENT_TYPE: list[tuple[str, str]] = [
    # 核武 / 大規模殺傷性武器
    ("WMD_NUCLEAR",        "nuclear_threat"),
    ("NUCLEAR",            "nuclear_threat"),
    ("WMD",                "nuclear_threat"),
    # 宣戰 / 入侵
    ("WAR",                "declaration_of_war"),
    ("INVASION",           "military_invasion"),
    # 軍事打擊
    ("STRIKE",             "military_strike"),
    ("AIRSTRIKE",          "military_strike"),
    ("MISSILE",            "military_strike"),
    ("BOMBING",            "military_strike"),
    # 軍事衝突
    ("MILITARY",           "military_clash"),
    ("ARMED_CONFLICT",     "military_clash"),
    ("BATTLE",             "military_clash"),
    # 爆炸 / 遠程暴力
    ("EXPLOSION",          "explosion"),
    ("IED",                "explosion"),
    # 政變 / 戒嚴
    ("COUP",               "political_coup"),
    ("MARTIAL_LAW",        "martial_law"),
    # 停火協議
    ("CEASEFIRE",          "ceasefire_agreement"),
    ("PEACE_TALKS",        "peace_talks_start"),
    ("PEACE_AGREEMENT",    "peace_talks_success"),
    # 軍事撤離
    ("WITHDRAWAL",         "military_withdrawal"),
    ("MILITARY_EXERCISE",  "military_exercise"),
    # 外交
    ("DIPLOMATIC",         "diplomatic_expulsion"),
    ("SANCTIONS",          "economic_sanctions"),
    ("SANCTION",           "economic_sanctions"),
    # 網路攻擊
    ("CYBER",              "cyberattack_critical"),
    ("HACK",               "cyberattack_critical"),
    # 能源
    ("ENERGY",             "energy_disruption"),
    ("OIL",                "energy_disruption"),
    # 社會
    ("PROTEST",            "protest_large"),
    ("RIOT",               "riot"),
    ("REFUGEE",            "refugee_crisis"),
    # 貿易
    ("TRADE_WAR",          "trade_war_escalation"),
    ("TRADE",              "trade_war_escalation"),
]


def gdelt_themes_to_event_type(themes: list[str]) -> str:
    """
    將 GDELT themes 列表映射到平台 event_type
    優先匹配優先級最高（最嚴重）的主題
    """
    themes_upper = [t.upper() for t in themes]
    for keyword, event_type in GDELT_THEME_TO_EVENT_TYPE:
        for theme in themes_upper:
            if keyword in theme:
                return event_type
    return "military_clash"  # 無法匹配時給予預設值


def get_event_type_rule(event_type: str) -> EventTypeRule:
    """取得事件類型規則，未知類型 fallback 到 military_clash"""
    return EVENT_TYPE_RULES.get(event_type, EVENT_TYPE_RULES["military_clash"])


def infer_dimensions(primary_dimension: str, severity: float) -> dict[str, float]:
    """
    依 primary_dimension 推斷各維度分數（source='rule'）
    主維度設為 severity，其他維度按比例推斷
    對應 02-data-pipeline §2.4 Step 8
    """
    # 次要維度分配（簡化比例）
    secondary_ratios = {
        "military":  {"political": 0.3, "economic": 0.2, "social": 0.1, "cyber": 0.05},
        "political": {"military": 0.2, "economic": 0.25, "social": 0.15, "cyber": 0.05},
        "economic":  {"political": 0.3, "military": 0.1, "social": 0.2, "cyber": 0.05},
        "social":    {"political": 0.25, "economic": 0.15, "military": 0.1, "cyber": 0.02},
        "cyber":     {"military": 0.2, "political": 0.2, "economic": 0.15, "social": 0.05},
    }

    dims = {"military": 0.0, "political": 0.0, "economic": 0.0,
            "social": 0.0, "cyber": 0.0}
    dims[primary_dimension] = severity

    ratios = secondary_ratios.get(primary_dimension, {})
    for dim, ratio in ratios.items():
        dims[dim] = round(severity * ratio, 4)

    return dims
