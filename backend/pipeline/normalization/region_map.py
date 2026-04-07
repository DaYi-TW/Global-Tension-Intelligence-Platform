"""
區域代碼推斷
依國家代碼（ISO alpha-3）推斷所屬區域
對應 docs/02-data-pipeline.md §2.4 區域代碼表
"""

# ── 9 個標準區域代碼（全平台唯一定義）─────────────────────────────────────
REGION_CODES = [
    "east_asia", "southeast_asia", "middle_east", "europe",
    "south_asia", "africa", "central_asia", "north_america", "latin_america",
]

# ISO alpha-3 → region_code
COUNTRY_TO_REGION: dict[str, str] = {
    # east_asia
    "CHN": "east_asia", "JPN": "east_asia", "KOR": "east_asia",
    "PRK": "east_asia", "TWN": "east_asia", "MNG": "east_asia",
    # southeast_asia
    "VNM": "southeast_asia", "PHL": "southeast_asia", "IDN": "southeast_asia",
    "MYS": "southeast_asia", "SGP": "southeast_asia", "THA": "southeast_asia",
    "MMR": "southeast_asia", "KHM": "southeast_asia", "LAO": "southeast_asia",
    "BRN": "southeast_asia", "TLS": "southeast_asia",
    # middle_east
    "IRN": "middle_east", "ISR": "middle_east", "SAU": "middle_east",
    "IRQ": "middle_east", "SYR": "middle_east", "YEM": "middle_east",
    "LBN": "middle_east", "JOR": "middle_east", "KWT": "middle_east",
    "ARE": "middle_east", "QAT": "middle_east", "BHR": "middle_east",
    "OMN": "middle_east", "PSE": "middle_east",
    # europe
    "RUS": "europe", "UKR": "europe", "POL": "europe", "DEU": "europe",
    "FRA": "europe", "GBR": "europe", "ITA": "europe", "ESP": "europe",
    "NLD": "europe", "BEL": "europe", "SWE": "europe", "NOR": "europe",
    "FIN": "europe", "DNK": "europe", "CHE": "europe", "AUT": "europe",
    "PRT": "europe", "GRC": "europe", "HUN": "europe", "CZE": "europe",
    "ROU": "europe", "BGR": "europe", "HRV": "europe", "SVK": "europe",
    "SVN": "europe", "EST": "europe", "LVA": "europe", "LTU": "europe",
    "SRB": "europe", "BIH": "europe", "ALB": "europe", "MDA": "europe",
    "BLR": "europe", "XKX": "europe",
    # south_asia
    "IND": "south_asia", "PAK": "south_asia", "AFG": "south_asia",
    "BGD": "south_asia", "LKA": "south_asia", "NPL": "south_asia",
    "BTN": "south_asia", "MDV": "south_asia",
    # africa
    "ETH": "africa", "SDN": "africa", "NGA": "africa", "COD": "africa",
    "MLI": "africa", "SSD": "africa", "SOM": "africa", "KEN": "africa",
    "TZA": "africa", "UGA": "africa", "RWA": "africa", "MOZ": "africa",
    "ZAF": "africa", "ZMB": "africa", "ZWE": "africa", "AGO": "africa",
    "CMR": "africa", "GHA": "africa", "SEN": "africa", "CIV": "africa",
    "BFA": "africa", "NER": "africa", "TCD": "africa", "CAF": "africa",
    "COG": "africa", "MDG": "africa", "MWI": "africa", "TGO": "africa",
    "BEN": "africa", "GIN": "africa", "SLE": "africa", "LBR": "africa",
    "MRT": "africa", "DZA": "africa", "LBY": "africa", "EGY": "africa",
    "TUN": "africa", "MAR": "africa", "ERI": "africa", "DJI": "africa",
    "BDI": "africa",
    # central_asia
    "KAZ": "central_asia", "UZB": "central_asia", "TJK": "central_asia",
    "KGZ": "central_asia", "TKM": "central_asia",
    # north_america
    "USA": "north_america", "CAN": "north_america", "MEX": "north_america",
    # latin_america
    "BRA": "latin_america", "COL": "latin_america", "VEN": "latin_america",
    "ARG": "latin_america", "CHL": "latin_america", "PER": "latin_america",
    "ECU": "latin_america", "BOL": "latin_america", "PRY": "latin_america",
    "URY": "latin_america", "GTM": "latin_america", "HND": "latin_america",
    "SLV": "latin_america", "NIC": "latin_america", "CRI": "latin_america",
    "PAN": "latin_america", "CUB": "latin_america", "HTI": "latin_america",
    "DOM": "latin_america",
}


def get_region_for_country(iso3: str) -> str | None:
    """依 ISO alpha-3 取得區域代碼，未知回傳 None"""
    return COUNTRY_TO_REGION.get(iso3)


def get_primary_region(country_codes: list[str]) -> str | None:
    """
    從多個國家代碼推斷主要區域
    策略：取最多國家所在的區域；同數時取第一個找到的
    """
    if not country_codes:
        return None
    from collections import Counter
    region_counts = Counter(
        r for c in country_codes
        if (r := get_region_for_country(c)) is not None
    )
    if not region_counts:
        return None
    return region_counts.most_common(1)[0][0]
