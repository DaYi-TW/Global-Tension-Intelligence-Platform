import { useEffect, useRef, useCallback } from 'react'
import useStore from '../store/useStore'
import { PLAY_SPEEDS } from '../constants'
import { fetchMapHeat, fetchMapHeatRange } from '../api/index'

// Add days to YYYY-MM-DD string
function addDays(dateStr, n) {
  const d = new Date(dateStr)
  d.setDate(d.getDate() + n)
  return d.toISOString().split('T')[0]
}

function dateToIndex(dateStr, from) {
  const d0 = new Date(from)
  const d1 = new Date(dateStr)
  return Math.round((d1 - d0) / 86400000)
}

function indexToDate(idx, from) {
  return addDays(from, idx)
}

function totalDays(from, to) {
  return Math.round((new Date(to) - new Date(from)) / 86400000)
}

export default function Timeline() {
  const currentDate   = useStore(s => s.currentDate)
  const isPlaying     = useStore(s => s.isPlaying)
  const playSpeed     = useStore(s => s.playSpeed)
  const dateRange     = useStore(s => s.dateRange)
  const mapDimension  = useStore(s => s.mapDimension)
  const preloadedData = useStore(s => s.preloadedData)
  const preloadedRange = useStore(s => s.preloadedRange)

  const setDate    = useStore(s => s.setDate)
  const setMapData = useStore(s => s.setMapData)
  const setPreloadedBatch = useStore(s => s.setPreloadedBatch)
  const setMapLoading = useStore(s => s.setMapLoading)
  const setPreloadedRange = useStore(s => s.setPreloadedRange)
  const togglePlay = useStore(s => s.togglePlay)
  const setPlaySpeed = useStore(s => s.setPlaySpeed)
  const setError   = useStore(s => s.setError)

  const intervalRef   = useRef(null)
  const debounceRef   = useRef(null)
  const preloadingRef = useRef(false)

  const total = totalDays(dateRange.from, dateRange.to)
  const currentIdx = dateToIndex(currentDate, dateRange.from)

  // Load single day data
  const loadDate = useCallback(async (date) => {
    const cached = useStore.getState().preloadedData[date]
    if (cached) {
      setMapData(date, cached)
      return
    }
    setMapLoading(true)
    try {
      const result = await fetchMapHeat(date, mapDimension)
      const dataMap = {}
      for (const c of result.countries) {
        dataMap[c.country_code] = { score: c.score, band: c.band, band_zh: c.band_zh }
      }
      setMapData(date, dataMap)
    } catch (err) {
      setError(`無法載入 ${date} 的地圖資料`)
    } finally {
      setMapLoading(false)
    }
  }, [mapDimension, setMapData, setMapLoading, setError])

  // Preload a 30-day batch
  const preloadBatch = useCallback(async (from, to) => {
    if (preloadingRef.current) return
    preloadingRef.current = true
    try {
      const result = await fetchMapHeatRange(from, to, mapDimension)
      // result.dates: { 'YYYY-MM-DD': { ISO3: {score, band, band_zh} } }
      const converted = {}
      for (const [date, countries] of Object.entries(result.dates)) {
        const dataMap = {}
        for (const [iso3, d] of Object.entries(countries)) {
          dataMap[iso3] = d
        }
        converted[date] = dataMap
      }
      setPreloadedBatch(converted)
      setPreloadedRange({ from, to })
    } catch (err) {
      console.warn('Preload failed:', err)
    } finally {
      preloadingRef.current = false
    }
  }, [mapDimension, setPreloadedBatch, setPreloadedRange])

  // Initial load: preload last 30 days
  useEffect(() => {
    const to = dateRange.to
    const from = addDays(to, -29)
    preloadBatch(from, to)
  }, [mapDimension])

  // When currentDate changes, load data
  useEffect(() => {
    loadDate(currentDate)

    // Check if we need to preload more
    const pr = useStore.getState().preloadedRange
    if (pr && !preloadingRef.current) {
      const daysToEnd = totalDays(currentDate, pr.to)
      const daysToStart = totalDays(pr.from, currentDate)
      if (daysToEnd < 7) {
        // Preload 30 more days forward
        const newTo = addDays(pr.to, 30)
        preloadBatch(addDays(pr.to, 1), newTo)
      } else if (daysToStart < 7) {
        // Preload 30 more days backward
        const newFrom = addDays(pr.from, -30)
        preloadBatch(newFrom, addDays(pr.from, -1))
      }
    }
  }, [currentDate])

  // Playback timer
  useEffect(() => {
    if (intervalRef.current) clearInterval(intervalRef.current)
    if (!isPlaying) return
    const ms = PLAY_SPEEDS[playSpeed]
    intervalRef.current = setInterval(() => {
      const cur = useStore.getState().currentDate
      const { to } = useStore.getState().dateRange
      if (cur >= to) {
        useStore.getState().pause()
        return
      }
      setDate(addDays(cur, 1))
    }, ms)
    return () => clearInterval(intervalRef.current)
  }, [isPlaying, playSpeed, setDate])

  // Keyboard shortcuts
  useEffect(() => {
    const onKey = (e) => {
      if (e.target.tagName === 'INPUT') return
      if (e.code === 'Space') { e.preventDefault(); togglePlay() }
      if (e.code === 'ArrowRight') setDate(addDays(currentDate, 1) <= dateRange.to ? addDays(currentDate, 1) : currentDate)
      if (e.code === 'ArrowLeft')  setDate(addDays(currentDate, -1) >= dateRange.from ? addDays(currentDate, -1) : currentDate)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [currentDate, dateRange, togglePlay, setDate])

  const handleSlider = (e) => {
    const idx = parseInt(e.target.value)
    const date = indexToDate(idx, dateRange.from)
    setDate(date)
    // Debounce API call
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => loadDate(date), 200)
  }

  const jump = (days) => {
    const next = addDays(currentDate, days)
    const clamped = next < dateRange.from ? dateRange.from : next > dateRange.to ? dateRange.to : next
    setDate(clamped)
  }

  return (
    <div
      className="relative z-20 flex-shrink-0"
      style={{
        background: 'linear-gradient(to top, #0a0c10 0%, #151820ee 100%)',
        borderTop: '1px solid #2a2d3a',
        padding: '10px 20px 12px',
      }}
    >
      {/* Slider row */}
      <div className="flex items-center gap-3 mb-1">
        <span className="text-muted text-xs font-mono whitespace-nowrap">{dateRange.from}</span>
        <div className="flex-1 relative">
          <input
            type="range"
            min={0}
            max={total}
            value={currentIdx}
            onChange={handleSlider}
            className="w-full"
          />
        </div>
        <span className="text-muted text-xs font-mono whitespace-nowrap">{dateRange.to}</span>
      </div>

      {/* Controls row */}
      <div className="flex items-center justify-between">
        {/* Playback controls */}
        <div className="flex items-center gap-2">
          {/* Rewind */}
          <button
            onClick={() => jump(-7)}
            className="w-7 h-7 flex items-center justify-center rounded text-muted hover:text-text hover:bg-panel transition-colors text-xs"
            title="倒退 7 天"
          >
            ◀◀
          </button>
          {/* Play/Pause */}
          <button
            onClick={togglePlay}
            className="w-9 h-9 flex items-center justify-center rounded-full border transition-all"
            style={isPlaying
              ? { borderColor: '#4299e1', background: '#4299e122', color: '#4299e1' }
              : { borderColor: '#2a2d3a', background: 'transparent', color: '#8a8fa8' }
            }
            title={isPlaying ? '暫停 (Space)' : '播放 (Space)'}
          >
            {isPlaying ? '⏸' : '▶'}
          </button>
          {/* Fast forward */}
          <button
            onClick={() => jump(7)}
            className="w-7 h-7 flex items-center justify-center rounded text-muted hover:text-text hover:bg-panel transition-colors text-xs"
            title="快進 7 天"
          >
            ▶▶
          </button>
        </div>

        {/* Current date */}
        <div className="text-center">
          <span
            className="text-text font-mono text-lg tracking-widest"
            style={{ fontFamily: "'Share Tech Mono', monospace", letterSpacing: '0.1em' }}
          >
            {currentDate}
          </span>
          <span className="text-muted text-xs ml-3">← → 鍵切換日期 | Space 播放</span>
        </div>

        {/* Speed selector */}
        <div className="flex items-center gap-1">
          <span className="text-muted text-xs mr-2">速度</span>
          {['slow', 'normal', 'fast'].map(s => (
            <button
              key={s}
              onClick={() => setPlaySpeed(s)}
              className="px-2 py-1 text-xs rounded transition-all"
              style={playSpeed === s
                ? { background: '#4299e122', color: '#4299e1', border: '1px solid #4299e144' }
                : { background: 'transparent', color: '#8a8fa8', border: '1px solid transparent' }
              }
            >
              {s === 'slow' ? '慢' : s === 'normal' ? '中' : '快'}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
