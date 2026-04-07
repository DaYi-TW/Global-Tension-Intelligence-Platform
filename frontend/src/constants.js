export const BAND_COLORS = {
  Stable:   '#38a169',
  Watch:    '#68d391',
  Elevated: '#d69e2e',
  High:     '#dd6b20',
  Crisis:   '#e53e3e',
}

export const BAND_BG = {
  Stable:   'bg-stable',
  Watch:    'bg-watch',
  Elevated: 'bg-elevated',
  High:     'bg-high',
  Crisis:   'bg-crisis',
}

export const BAND_TEXT = {
  Stable:   'text-stable',
  Watch:    'text-watch',
  Elevated: 'text-elevated',
  High:     'text-high',
  Crisis:   'text-crisis',
}

// Map fill colors per spec §11.5.2
export const TENSION_COLOR_STOPS = [
  [0,   '#1a3a2a'],
  [20,  '#2d3a1a'],
  [40,  '#4a3a0a'],
  [60,  '#5a2a0a'],
  [80,  '#6a0a0a'],
  [100, '#8a0000'],
]

export const NO_DATA_COLOR = '#1a1a2a'

// Given a score 0-100, return map fill color via linear interpolation
export function scoreToColor(score) {
  if (score == null) return NO_DATA_COLOR
  const stops = TENSION_COLOR_STOPS
  for (let i = 0; i < stops.length - 1; i++) {
    const [s0, c0] = stops[i]
    const [s1, c1] = stops[i + 1]
    if (score <= s1) {
      const t = (score - s0) / (s1 - s0)
      return lerpColor(c0, c1, t)
    }
  }
  return stops[stops.length - 1][1]
}

function hexToRgb(hex) {
  const h = hex.replace('#', '')
  return [
    parseInt(h.substring(0, 2), 16),
    parseInt(h.substring(2, 4), 16),
    parseInt(h.substring(4, 6), 16),
  ]
}

function rgbToHex(r, g, b) {
  return '#' + [r, g, b].map(v => Math.round(v).toString(16).padStart(2, '0')).join('')
}

function lerpColor(c0, c1, t) {
  const [r0, g0, b0] = hexToRgb(c0)
  const [r1, g1, b1] = hexToRgb(c1)
  return rgbToHex(r0 + (r1 - r0) * t, g0 + (g1 - g0) * t, b0 + (b1 - b0) * t)
}

export const DIMENSIONS = [
  { key: 'overall',  label: '總覽' },
  { key: 'military', label: '軍事' },
  { key: 'political',label: '政治' },
  { key: 'economic', label: '經濟' },
  { key: 'social',   label: '社會' },
  { key: 'cyber',    label: '網路' },
]

export const PLAY_SPEEDS = {
  slow:   1000,
  normal: 400,
  fast:   150,
}

export const COUNTRY_NAMES = {
  USA: '美國', CHN: '中國', RUS: '俄羅斯', IRN: '伊朗', ISR: '以色列',
  SAU: '沙烏地阿拉伯', GBR: '英國', FRA: '法國', DEU: '德國', JPN: '日本',
  KOR: '南韓', PRK: '北韓', IND: '印度', PAK: '巴基斯坦', AFG: '阿富汗',
  UKR: '烏克蘭', BLR: '白俄羅斯', POL: '波蘭', TUR: '土耳其', SYR: '敘利亞',
  IRQ: '伊拉克', LBN: '黎巴嫩', YEM: '葉門', LBY: '利比亞', SDN: '蘇丹',
  ETH: '衣索比亞', SOM: '索馬利亞', MMR: '緬甸', PHL: '菲律賓', VNM: '越南',
  TWN: '台灣', HKG: '香港', AUS: '澳洲', CAN: '加拿大', MEX: '墨西哥',
  BRA: '巴西', ARG: '阿根廷', VEN: '委內瑞拉', CHL: '智利', COL: '哥倫比亞',
  EGY: '埃及', NGA: '奈及利亞', ZAF: '南非', KEN: '肯亞', TCD: '查德',
  IDN: '印尼', SGP: '新加坡', MYS: '馬來西亞', THA: '泰國', BGD: '孟加拉',
  KAZ: '哈薩克', AZE: '亞塞拜然', ARM: '亞美尼亞', GEO: '喬治亞',
  BHR: '巴林', QAT: '卡達', KWT: '科威特', OMN: '阿曼', ARE: '阿聯酋',
}

export function getCountryName(code) {
  return COUNTRY_NAMES[code] || code
}
