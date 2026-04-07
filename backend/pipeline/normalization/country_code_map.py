"""
國家代碼映射表
- FIPS 10-4 → ISO 3166-1 alpha-3（GDELT 用）
- 國家全名  → ISO 3166-1 alpha-3（ACLED 用）

全平台統一使用 ISO alpha-3（三位大寫字母）
"""

# ── FIPS 10-4 → ISO alpha-3 ────────────────────────────────────────────────
# GDELT 使用 FIPS 10-4 代碼，需轉換
FIPS_TO_ISO3: dict[str, str] = {
    "AF": "AFG", "AL": "ALB", "AG": "DZA", "AN": "AND", "AO": "AGO",
    "AC": "ATG", "AR": "ARG", "AM": "ARM", "AS": "AUS", "AU": "AUT",
    "AJ": "AZE", "BF": "BHS", "BA": "BHR", "BG": "BGD", "BB": "BRB",
    "BO": "BLR", "BE": "BEL", "BH": "BLZ", "BN": "BEN", "BT": "BTN",
    "BL": "BOL", "BK": "BIH", "BC": "BWA", "BR": "BRA", "BX": "BRN",
    "BU": "BGR", "UV": "BFA", "BM": "MMR", "BY": "BDI", "CV": "CPV",
    "CB": "KHM", "CM": "CMR", "CA": "CAN", "CT": "CAF", "CD": "TCD",
    "CI": "CHL", "CH": "CHN", "CO": "COL", "CN": "COM", "CF": "COG",
    "CG": "COD", "CS": "CRI", "IV": "CIV", "HR": "HRV", "CU": "CUB",
    "CY": "CYP", "EZ": "CZE", "DA": "DNK", "DJ": "DJI", "DO": "DOM",
    "EC": "ECU", "EG": "EGY", "ES": "SLV", "EK": "GNQ", "ER": "ERI",
    "EN": "EST", "ET": "ETH", "FJ": "FJI", "FI": "FIN", "FR": "FRA",
    "GB": "GAB", "GA": "GMB", "GG": "GEO", "GM": "DEU", "GH": "GHA",
    "GR": "GRC", "GT": "GTM", "PU": "GNB", "GV": "GIN", "GY": "GUY",
    "HA": "HTI", "HO": "HND", "HU": "HUN", "IC": "ISL", "IN": "IND",
    "ID": "IDN", "IR": "IRN", "IZ": "IRQ", "EI": "IRL", "IS": "ISR",
    "IT": "ITA", "JM": "JAM", "JA": "JPN", "JO": "JOR", "KZ": "KAZ",
    "KE": "KEN", "KN": "PRK", "KS": "KOR", "KU": "KWT", "KG": "KGZ",
    "LA": "LAO", "LG": "LVA", "LE": "LBN", "LT": "LSO", "LI": "LBR",
    "LY": "LBY", "LS": "LIE", "LH": "LTU", "LU": "LUX", "MK": "MDG",
    "MI": "MWI", "MY": "MYS", "MV": "MDV", "ML": "MLI", "MT": "MLT",
    "MR": "MRT", "MP": "MUS", "MX": "MEX", "MD": "MDA", "MN": "MNG",
    "MO": "MAR", "MZ": "MOZ", "WA": "NAM", "NP": "NPL", "NL": "NLD",
    "NZ": "NZL", "NU": "NIC", "NG": "NER", "NI": "NGA", "NO": "NOR",
    "MU": "OMN", "PK": "PAK", "PM": "PAN", "PP": "PNG", "PA": "PRY",
    "PE": "PER", "RP": "PHL", "PL": "POL", "PO": "PRT", "QA": "QAT",
    "RO": "ROU", "RS": "RUS", "RW": "RWA", "SC": "STP", "SA": "SAU",
    "SG": "SEN", "RB": "SRB", "SL": "SLE", "SN": "SGP", "LO": "SVK",
    "SI": "SVN", "BP": "SLB", "SO": "SOM", "SF": "ZAF", "SP": "ESP",
    "CE": "LKA", "SU": "SDN", "SR": "SUR", "WZ": "SWZ", "SW": "SWE",
    "SZ": "CHE", "SY": "SYR", "TW": "TWN", "TI": "TJK", "TZ": "TZA",
    "TH": "THA", "TO": "TLS", "TG": "TGO", "TN": "TON", "TD": "TTO",
    "TS": "TUN", "TU": "TUR", "TX": "TKM", "UG": "UGA", "UP": "UKR",
    "AE": "ARE", "UK": "GBR", "US": "USA", "UY": "URY", "UZ": "UZB",
    "VE": "VEN", "VM": "VNM", "YM": "YEM", "ZA": "ZMB", "ZI": "ZWE",
    # 多字元 FIPS（組織或特殊代碼）
    "EUN": "EUN",  # European Union (非 ISO，保留原樣)
    "UNK": "UNK",  # Unknown
}

# ── 國家全名 → ISO alpha-3 ──────────────────────────────────────────────────
# ACLED 使用英文全名，需轉換
NAME_TO_ISO3: dict[str, str] = {
    "Afghanistan": "AFG", "Albania": "ALB", "Algeria": "DZA",
    "Angola": "AGO", "Argentina": "ARG", "Armenia": "ARM",
    "Australia": "AUS", "Austria": "AUT", "Azerbaijan": "AZE",
    "Bahrain": "BHR", "Bangladesh": "BGD", "Belarus": "BLR",
    "Belgium": "BEL", "Belize": "BLZ", "Benin": "BEN",
    "Bolivia": "BOL", "Bosnia and Herzegovina": "BIH",
    "Botswana": "BWA", "Brazil": "BRA", "Brunei": "BRN",
    "Bulgaria": "BGR", "Burkina Faso": "BFA", "Burundi": "BDI",
    "Cambodia": "KHM", "Cameroon": "CMR", "Canada": "CAN",
    "Central African Republic": "CAF", "Chad": "TCD",
    "Chile": "CHL", "China": "CHN", "Colombia": "COL",
    "Democratic Republic of Congo": "COD",
    "Republic of Congo": "COG", "Costa Rica": "CRI",
    "Ivory Coast": "CIV", "Cote d'Ivoire": "CIV",
    "Croatia": "HRV", "Cuba": "CUB", "Cyprus": "CYP",
    "Czech Republic": "CZE", "Czechia": "CZE",
    "Denmark": "DNK", "Djibouti": "DJI",
    "Dominican Republic": "DOM", "Ecuador": "ECU",
    "Egypt": "EGY", "El Salvador": "SLV",
    "Eritrea": "ERI", "Estonia": "EST", "Ethiopia": "ETH",
    "Finland": "FIN", "France": "FRA", "Gabon": "GAB",
    "Gambia": "GMB", "Georgia": "GEO", "Germany": "DEU",
    "Ghana": "GHA", "Greece": "GRC", "Guatemala": "GTM",
    "Guinea": "GIN", "Guinea-Bissau": "GNB", "Guyana": "GUY",
    "Haiti": "HTI", "Honduras": "HND", "Hungary": "HUN",
    "Iceland": "ISL", "India": "IND", "Indonesia": "IDN",
    "Iran": "IRN", "Iraq": "IRQ", "Ireland": "IRL",
    "Israel": "ISR", "Italy": "ITA", "Jamaica": "JAM",
    "Japan": "JPN", "Jordan": "JOR", "Kazakhstan": "KAZ",
    "Kenya": "KEN", "North Korea": "PRK", "South Korea": "KOR",
    "Kosovo": "XKX", "Kuwait": "KWT", "Kyrgyzstan": "KGZ",
    "Laos": "LAO", "Latvia": "LVA", "Lebanon": "LBN",
    "Lesotho": "LSO", "Liberia": "LBR", "Libya": "LBY",
    "Lithuania": "LTU", "Luxembourg": "LUX", "Madagascar": "MDG",
    "Malawi": "MWI", "Malaysia": "MYS", "Mali": "MLI",
    "Mauritania": "MRT", "Mexico": "MEX", "Moldova": "MDA",
    "Mongolia": "MNG", "Morocco": "MAR", "Mozambique": "MOZ",
    "Myanmar": "MMR", "Burma": "MMR", "Namibia": "NAM",
    "Nepal": "NPL", "Netherlands": "NLD", "New Zealand": "NZL",
    "Nicaragua": "NIC", "Niger": "NER", "Nigeria": "NGA",
    "Norway": "NOR", "Oman": "OMN", "Pakistan": "PAK",
    "Palestine": "PSE", "Palestinian Territories": "PSE",
    "West Bank": "PSE", "Gaza Strip": "PSE",
    "Panama": "PAN", "Papua New Guinea": "PNG",
    "Paraguay": "PRY", "Peru": "PER", "Philippines": "PHL",
    "Poland": "POL", "Portugal": "PRT", "Qatar": "QAT",
    "Romania": "ROU", "Russia": "RUS", "Rwanda": "RWA",
    "Saudi Arabia": "SAU", "Senegal": "SEN", "Serbia": "SRB",
    "Sierra Leone": "SLE", "Singapore": "SGP",
    "Slovakia": "SVK", "Slovenia": "SVN",
    "Solomon Islands": "SLB", "Somalia": "SOM",
    "Somaliland": "SOM",  # 未獲承認，歸入 SOM
    "South Africa": "ZAF", "South Sudan": "SSD",
    "Spain": "ESP", "Sri Lanka": "LKA", "Sudan": "SDN",
    "Suriname": "SUR", "Sweden": "SWE", "Switzerland": "CHE",
    "Syria": "SYR", "Taiwan": "TWN", "Tajikistan": "TJK",
    "Tanzania": "TZA", "Thailand": "THA",
    "Timor-Leste": "TLS", "East Timor": "TLS",
    "Togo": "TGO", "Trinidad and Tobago": "TTO",
    "Tunisia": "TUN", "Turkey": "TUR", "Turkmenistan": "TKM",
    "Uganda": "UGA", "Ukraine": "UKR",
    "United Arab Emirates": "ARE", "United Kingdom": "GBR",
    "United States": "USA", "United States of America": "USA",
    "Uruguay": "URY", "Uzbekistan": "UZB",
    "Venezuela": "VEN", "Vietnam": "VNM", "Viet Nam": "VNM",
    "Yemen": "YEM", "Zambia": "ZMB", "Zimbabwe": "ZWE",
}


def fips_to_iso3(fips_code: str) -> str | None:
    """
    FIPS 10-4 → ISO alpha-3
    回傳 None 表示無法映射（寫入 events 但 needs_review=TRUE）
    """
    if not fips_code:
        return None
    return FIPS_TO_ISO3.get(fips_code.upper())


def name_to_iso3(country_name: str) -> str | None:
    """
    國家全名 → ISO alpha-3
    先嘗試精確比對，再嘗試 lower() 比對
    回傳 None 表示無法映射
    """
    if not country_name:
        return None
    # 精確比對
    result = NAME_TO_ISO3.get(country_name)
    if result:
        return result
    # 前後空白、大小寫容錯
    result = NAME_TO_ISO3.get(country_name.strip())
    if result:
        return result
    # 全小寫比對
    lower_map = {k.lower(): v for k, v in NAME_TO_ISO3.items()}
    return lower_map.get(country_name.strip().lower())
