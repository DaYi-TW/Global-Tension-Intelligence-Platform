/**
 * GDELT 主題代碼 → 人可讀的中文說明
 *
 * GDELT GKG 主題代碼前綴含義：
 * TAX_FNCACT_*   = 職業/角色 (Functional Actor)
 * TAX_ETHNICITY_*= 族裔
 * TAX_POLITICAL_PARTY_* = 政黨
 * TAX_WORLDLANGUAGES_* = 語言族群
 * CRISISLEX_*   = 危機詞彙
 * EPU_*         = 經濟政策不確定性
 * WB_*          = 世界銀行主題
 * ENV_*         = 環境
 * SOC_*         = 社會
 * USPEC_*       = 政治
 * SLFID_*       = 公民自由
 * MEDIA_*       = 媒體
 */

// 精確代碼對應（優先匹配）
const EXACT_MAP = {
  // 武裝衝突 / 安全
  ARMEDCONFLICT:              '武裝衝突',
  KILL:                       '傷亡事件',
  ARREST:                     '逮捕行動',
  CEASEFIRE:                  '停火協議',
  NEGOTIATIONS:               '談判協商',
  UNREST_BELLIGERENT:         '武裝對抗',
  MARITIME_INCIDENT:          '海上事件',
  RELEASE_HOSTAGE:            '人質釋放',
  CRISISLEX_CRISISLEXREC:     '危機事件',
  'CRISISLEX_T11_UPDATESSYMPATHY': '危機更新',
  'CRISISLEX_C07_SAFETY':     '安全威脅',

  // 核武 / 軍事
  ENV_NUCLEARPOWER:           '核能/核武',
  'EPU_CATS_NATIONAL_SECURITY': '國家安全',
  SECURITY_SERVICES:          '安全部隊',

  // 政治 / 政府
  LEADER:                     '領導人事件',
  GENERAL_GOVERNMENT:         '政府事務',
  LEGISLATION:                '立法事務',
  TRIAL:                      '司法審判',
  ELECTION:                   '選舉事務',
  'USPEC_POLITICS_GENERAL1':  '政治事件',
  'EPU_POLICY_POLITICAL':     '政治政策',
  'EPU_POLICY_GOVERNMENT':    '政府政策',
  'EPU_CATS_MIGRATION_FEAR_FEAR': '移民危機',
  'SLFID_CIVIL_LIBERTIES':    '公民自由',
  'TAX_POLITICAL_PARTY_REPUBLICAN': '共和黨',
  'TAX_POLITICAL_PARTY_DEMOCRAT': '民主黨',

  // 經濟 / 貿易
  ECON_STOCKMARKET:           '股市動態',
  'TAX_ECON_PRICE':           '物價波動',
  'EPU_POLICY':               '政策不確定性',
  'WB_678_DIGITAL_GOVERNMENT': '數位政府',
  'WB_2670_JOBS':             '就業問題',
  'WB_695_POVERTY':           '貧困問題',
  'WB_135_TRANSPORT':         '交通運輸',
  'WB_1174_WAREHOUSING_AND_STORAGE': '倉儲物流',
  'WB_793_TRANSPORT_AND_LOGISTICS_SERVICES': '物流服務',
  'WB_137_WATER':             '水資源',
  'WB_1160_SHOCKS_AND_VULNERABILITY': '經濟衝擊',
  'WB_2433_CONFLICT_AND_VIOLENCE': '衝突暴力',
  'WB_2470_PEACE_OPERATIONS_AND_CONFLICT_MANAGEMENT': '和平行動',
  'WB_2478_PEACE_PROCESSES_AND_DIALOGUE': '和平對話',

  // 社會 / 人道
  IMMIGRATION:                '移民議題',
  MEDICAL:                    '醫療衛生',
  GENERAL_HEALTH:             '公共衛生',
  EDUCATION:                  '教育事務',
  'SOC_GENERALCRIME':         '一般犯罪',
  'SOC_POINTSOFINTEREST':     '社會焦點',
  'WB_2433_CONFLICT_AND_VIOLENCE': '衝突暴力',

  // 環境 / 災難
  UNGP_FORESTS_RIVERS_OCEANS: '環境資源',

  // 媒體
  MEDIA_MSM:                  '主流媒體',
}

// 前綴對應（prefix matching）
const PREFIX_MAP = [
  { prefix: 'TAX_FNCACT_PRESIDENT',     zh: '總統/領導人' },
  { prefix: 'TAX_FNCACT_POLICE',        zh: '警察部隊' },
  { prefix: 'TAX_FNCACT_MILITARY',      zh: '軍事人員' },
  { prefix: 'TAX_FNCACT_MINISTER',      zh: '政府部長' },
  { prefix: 'TAX_FNCACT_AMBASSADOR',    zh: '外交大使' },
  { prefix: 'TAX_FNCACT_JOURNALIST',    zh: '新聞記者' },
  { prefix: 'TAX_FNCACT_MANUFACTURER',  zh: '製造業' },
  { prefix: 'TAX_FNCACT_DRIVER',        zh: '運輸業' },
  { prefix: 'TAX_FNCACT_ACTOR',         zh: '演藝人員' },
  { prefix: 'TAX_FNCACT_ACTRESS',       zh: '演藝人員' },
  { prefix: 'TAX_FNCACT_CHILD',         zh: '兒童相關' },
  { prefix: 'TAX_FNCACT_REFUGEE',       zh: '難民' },
  { prefix: 'TAX_FNCACT_REBEL',         zh: '武裝叛軍' },
  { prefix: 'TAX_FNCACT',               zh: '相關人士' },
  { prefix: 'TAX_ETHNICITY_RUSSIAN',    zh: '俄羅斯族裔' },
  { prefix: 'TAX_ETHNICITY_ARAB',       zh: '阿拉伯族裔' },
  { prefix: 'TAX_ETHNICITY_IRANIAN',    zh: '伊朗族裔' },
  { prefix: 'TAX_ETHNICITY_CHINESE',    zh: '華裔' },
  { prefix: 'TAX_ETHNICITY_KURD',       zh: '庫德族' },
  { prefix: 'TAX_ETHNICITY',            zh: '族裔事件' },
  { prefix: 'TAX_WORLDLANGUAGES_RUSSIA', zh: '俄語圈' },
  { prefix: 'TAX_WORLDLANGUAGES_ARABIC', zh: '阿拉伯語圈' },
  { prefix: 'TAX_WORLDLANGUAGES',       zh: '語言族群' },
  { prefix: 'TAX_POLITICAL_PARTY',      zh: '政黨事務' },
  { prefix: 'CRISISLEX_T',              zh: '危機事件' },
  { prefix: 'CRISISLEX_C',              zh: '緊急狀況' },
  { prefix: 'EPU_CATS',                 zh: '政策風險' },
  { prefix: 'EPU_POLICY',               zh: '政策議題' },
  { prefix: 'EPU_',                     zh: '經濟不確定' },
  { prefix: 'WB_',                      zh: '發展議題' },
  { prefix: 'ENV_',                     zh: '環境事件' },
  { prefix: 'SOC_',                     zh: '社會事件' },
  { prefix: 'MEDIA_',                   zh: '媒體報導' },
  { prefix: 'SLFID_',                   zh: '公民議題' },
  { prefix: 'USPEC_',                   zh: '政治事件' },
  { prefix: 'UNGP_',                    zh: '聯合國議題' },
]

/**
 * 把單一 GDELT 主題代碼翻譯成中文關鍵字
 */
function translateToken(token) {
  const t = token.trim()
  if (!t || t.length < 2) return null

  // 精確比對
  if (EXACT_MAP[t]) return EXACT_MAP[t]

  // 前綴比對
  for (const { prefix, zh } of PREFIX_MAP) {
    if (t.startsWith(prefix)) return zh
  }

  return null
}

// ISO3 → 中文國家名
const ISO3_ZH = {
  USA: '美國', CHN: '中國', RUS: '俄羅斯', IRN: '伊朗', ISR: '以色列',
  SAU: '沙烏地', GBR: '英國', FRA: '法國', DEU: '德國', JPN: '日本',
  KOR: '南韓', PRK: '北韓', IND: '印度', PAK: '巴基斯坦', AFG: '阿富汗',
  UKR: '烏克蘭', BLR: '白俄羅斯', POL: '波蘭', TUR: '土耳其', SYR: '敘利亞',
  IRQ: '伊拉克', LBN: '黎巴嫩', YEM: '葉門', LBY: '利比亞', SDN: '蘇丹',
  ETH: '衣索比亞', SOM: '索馬利亞', MMR: '緬甸', PHL: '菲律賓', VNM: '越南',
  TWN: '台灣', HKG: '香港', AUS: '澳洲', CAN: '加拿大', MEX: '墨西哥',
  BRA: '巴西', ARG: '阿根廷', VEN: '委內瑞拉', CHL: '智利', IDN: '印尼',
  SGP: '新加坡', MYS: '馬來西亞', THA: '泰國', BGD: '孟加拉',
  EGY: '埃及', NGA: '奈及利亞', ZAF: '南非', KEN: '肯亞',
  BHR: '巴林', QAT: '卡達', KWT: '科威特', ARE: '阿聯酋',
  NZL: '紐西蘭', SWE: '瑞典', FIN: '芬蘭', HUN: '匈牙利',
  NER: '尼日', BEN: '貝南', DJI: '吉布地', CPV: '維德角',
  AZE: '亞塞拜然', GEO: '喬治亞', KAZ: '哈薩克',
  CHE: '瑞士', AUT: '奧地利', ESP: '西班牙', BEL: '比利時',
  BWA: '波札那', GHA: '迦納', BRN: '汶萊', BHS: '巴哈馬',
  DNK: '丹麥', GBR: '英國',
}

/**
 * 解析 GDELT 格式標題，回傳人可讀的中文說明
 *
 * 輸入: "[GDELT] TAX_FNCACT, TAX_FNCACT_MANUFACTURER, TAX_FNCACT_DRIVERS — USA, SGP, CHN"
 * 輸出: { summary: "製造業與運輸業相關事件", countries: "美國、新加坡、中國" }
 */
export function parseGdeltTitle(title) {
  if (!title) return { summary: '事件', countries: '' }

  // 不是 GDELT 格式，直接回傳
  if (!title.startsWith('[GDELT]')) {
    return { summary: title, countries: '' }
  }

  // 移除 [GDELT] 前綴
  const body = title.replace(/^\[GDELT\]\s*/, '').trim()

  // 分離主題代碼與國家代碼（用 — 或 - 分隔）
  const dashIdx = body.search(/\s*[—–-]+\s*[A-Z]{3}/)
  let themePart = body
  let countryPart = ''

  if (dashIdx > -1) {
    themePart = body.slice(0, dashIdx).trim()
    countryPart = body.slice(dashIdx).replace(/^[\s—–-]+/, '').trim()
  }

  // 解析主題代碼
  const tokens = themePart.split(/[,\s]+/).filter(Boolean)

  // 翻譯每個 token，去重
  const translations = []
  const seen = new Set()
  for (const t of tokens) {
    const zh = translateToken(t)
    if (zh && !seen.has(zh)) {
      seen.add(zh)
      translations.push(zh)
    }
  }

  // 組合摘要（最多取前 3 個有意義的詞）
  let summary
  if (translations.length === 0) {
    // 完全無法解析，用 event_type fallback
    summary = '國際事件'
  } else if (translations.length === 1) {
    summary = translations[0] + '相關事件'
  } else if (translations.length === 2) {
    summary = translations[0] + '與' + translations[1]
  } else {
    summary = translations.slice(0, 3).join('、') + '相關'
  }

  // 解析國家代碼 → 中文
  const countryCodes = countryPart
    .split(/[,\s]+/)
    .map(c => c.trim())
    .filter(c => /^[A-Z]{3}$/.test(c))

  const countryNames = countryCodes
    .map(c => ISO3_ZH[c] || c)
    .join('、')

  return { summary, countries: countryNames, rawCodes: countryCodes }
}

/**
 * 直接回傳完整的可讀標題字串
 * "武裝衝突、停火協議相關 — 巴林、以色列、伊朗"
 */
export function humanizeTitle(title, eventType) {
  if (!title) return '未知事件'

  // 非 GDELT 格式（未來 ACLED/NewsAPI 資料）直接回傳
  if (!title.startsWith('[GDELT]')) return title

  const { summary, countries } = parseGdeltTitle(title)

  // 特殊處理 "Unknown event"
  if (title.includes('Unknown event')) {
    return countries ? `局勢事件 — ${countries}` : '局勢事件'
  }

  if (countries) {
    return `${summary} — ${countries}`
  }
  return summary
}
