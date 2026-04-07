import { create } from 'zustand'

// Today's date as YYYY-MM-DD
const today = new Date().toISOString().split('T')[0]
const thirtyDaysAgo = new Date(Date.now() - 30 * 86400000).toISOString().split('T')[0]

const useStore = create((set, get) => ({
  // ── 時間軸狀態 ──────────────────────────────────────────────────
  currentDate: today,
  isPlaying: false,
  playSpeed: 'normal',       // 'slow' | 'normal' | 'fast'
  dateRange: { from: thirtyDaysAgo, to: today },

  // ── 地圖狀態 ────────────────────────────────────────────────────
  mapDimension: 'overall',   // 'overall' | 'military' | 'political' | 'economic' | 'social' | 'cyber'
  selectedCountry: null,     // ISO alpha-3 or null
  selectedRegion: null,
  mapData: {},               // Record<ISO3, { score, band, band_zh }>
  preloadedData: {},         // Record<YYYY-MM-DD, Record<ISO3, { score, band, band_zh }>>
  isMapLoading: false,
  preloadedRange: null,      // { from, to } | null

  // ── UI 狀態 ─────────────────────────────────────────────────────
  sidePanelOpen: false,
  sidePanelCountry: null,
  error: null,

  // ── Dashboard 快取 ──────────────────────────────────────────────
  dashboardData: null,
  globalTrendData: null,

  // ── Actions ─────────────────────────────────────────────────────
  setDate: (date) => {
    const { preloadedData, mapDimension } = get()
    const dayData = preloadedData[date]
    if (dayData) {
      set({ currentDate: date, mapData: dayData, isMapLoading: false })
    } else {
      set({ currentDate: date })
    }
  },

  setMapData: (date, data) => {
    set((state) => ({
      mapData: data,
      preloadedData: { ...state.preloadedData, [date]: data },
    }))
  },

  setPreloadedBatch: (batchDates) => {
    // batchDates: Record<YYYY-MM-DD, Record<ISO3, {score, band, band_zh}>>
    set((state) => ({
      preloadedData: { ...state.preloadedData, ...batchDates },
    }))
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
