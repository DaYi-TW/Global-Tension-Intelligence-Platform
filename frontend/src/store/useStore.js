import { create } from 'zustand'

// Today's date as YYYY-MM-DD
const today = new Date().toISOString().split('T')[0]
const thirtyDaysAgo = new Date(Date.now() - 30 * 86400000).toISOString().split('T')[0]

// mapData { ISO3: { score, band, band_zh } } → 加權平均全球分數
function computeAvgScore(mapData) {
  const scores = Object.values(mapData).map(v => v.score).filter(s => s != null && s > 0)
  if (scores.length === 0) return null
  return +(scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(1)
}

function getBand(score) {
  if (score == null) return { band: 'Watch', band_zh: '—' }
  if (score < 20)  return { band: 'Stable',   band_zh: '平穩' }
  if (score < 40)  return { band: 'Watch',    band_zh: '關注' }
  if (score < 60)  return { band: 'Elevated', band_zh: '升溫' }
  if (score < 80)  return { band: 'High',     band_zh: '高壓' }
  return             { band: 'Crisis',   band_zh: '危機' }
}

const useStore = create((set, get) => ({
  // ── 時間軸狀態 ──────────────────────────────────────────────────
  currentDate: today,
  isPlaying: false,
  playSpeed: 'normal',       // 'slow' | 'normal' | 'fast'
  dateRange: { from: thirtyDaysAgo, to: today },

  // ── 地圖狀態 ────────────────────────────────────────────────────
  mapDimension: 'overall',
  selectedCountry: null,
  selectedRegion: null,
  mapData: {},               // Record<ISO3, { score, band, band_zh }>
  preloadedData: {},         // Record<YYYY-MM-DD, Record<ISO3, { score, band, band_zh }>>
  isMapLoading: false,
  preloadedRange: null,

  // ── 即時全球分數（從 mapData 即時計算）─────────────────────────
  liveGlobalScore: null,     // number | null
  liveGlobalBand: 'Watch',
  liveGlobalBandZh: '—',

  // ── UI 狀態 ─────────────────────────────────────────────────────
  sidePanelOpen: false,
  sidePanelCountry: null,
  error: null,

  // ── Dashboard 快取 ──────────────────────────────────────────────
  dashboardData: null,
  globalTrendData: null,

  // ── Actions ─────────────────────────────────────────────────────
  setDate: (date) => {
    const { preloadedData } = get()
    const dayData = preloadedData[date]
    if (dayData) {
      // 建立新 reference 確保 MapView useEffect([mapData]) 一定觸發
      const freshCopy = { ...dayData }
      const score = computeAvgScore(freshCopy)
      const { band, band_zh } = getBand(score)
      set({
        currentDate: date,
        mapData: freshCopy,
        isMapLoading: false,
        liveGlobalScore: score,
        liveGlobalBand: band,
        liveGlobalBandZh: band_zh,
      })
    } else {
      set({ currentDate: date })
    }
  },

  setMapData: (date, data) => {
    const score = computeAvgScore(data)
    const { band, band_zh } = getBand(score)
    set((state) => ({
      mapData: data,
      preloadedData: { ...state.preloadedData, [date]: data },
      liveGlobalScore: score,
      liveGlobalBand: band,
      liveGlobalBandZh: band_zh,
    }))
  },

  setPreloadedBatch: (batchDates) => {
    set((state) => {
      const newPreloaded = { ...state.preloadedData, ...batchDates }
      // 如果當前日期在新批次裡，立即更新 mapData
      const todayData = batchDates[state.currentDate]
      if (todayData) {
        const freshCopy = { ...todayData }
        const score = computeAvgScore(freshCopy)
        const { band, band_zh } = getBand(score)
        return {
          preloadedData: newPreloaded,
          mapData: freshCopy,
          liveGlobalScore: score,
          liveGlobalBand: band,
          liveGlobalBandZh: band_zh,
        }
      }
      return { preloadedData: newPreloaded }
    })
  },

  play: () => set({ isPlaying: true }),
  pause: () => set({ isPlaying: false }),
  togglePlay: () => set((s) => ({ isPlaying: !s.isPlaying })),

  setPlaySpeed: (speed) => set({ playSpeed: speed }),

  setDimension: (dim) => set({ mapDimension: dim, mapData: {} }),

  selectCountry: (code) => set({
    selectedCountry: code,
    sidePanelOpen: code !== null,
    sidePanelCountry: code,
  }),

  selectRegion: (code) => set({ selectedRegion: code }),

  setMapLoading: (loading) => set({ isMapLoading: loading }),

  setPreloadedRange: (range) => set({ preloadedRange: range }),

  setError: (msg) => set({ error: msg }),

  setDashboardData: (data) => set({ dashboardData: data }),
  setGlobalTrendData: (data) => set({ globalTrendData: data }),

  setDateRange: (range) => set({ dateRange: range }),
}))

export default useStore
