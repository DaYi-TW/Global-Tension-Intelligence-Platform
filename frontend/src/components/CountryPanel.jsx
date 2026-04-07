import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import ReactECharts from 'echarts-for-react'
import useStore from '../store/useStore'
import { BAND_COLORS, getCountryName } from '../constants'
import { fetchCountries, fetchGlobalTrend } from '../api/index'

const DIM_LABELS = {
  military:  '軍事',
  political: '政治',
  economic:  '經濟',
  social:    '社會',
  cyber:     '網路',
}

function DimBar({ label, value, color }) {
  return (
    <div className="flex items-center gap-2 mb-2">
      <span className="text-muted text-xs w-8">{label}</span>
      <div className="flex-1 bg-border rounded-full h-1.5 overflow-hidden">
        <motion.div
          className="h-full rounded-full"
          style={{ background: color }}
          initial={{ width: 0 }}
          animate={{ width: `${value || 0}%` }}
          transition={{ duration: 0.6, ease: 'easeOut' }}
        />
      </div>
      <span className="text-text text-xs w-8 text-right font-mono">{value?.toFixed(1) || '—'}</span>
    </div>
  )
}

export default function CountryPanel() {
  const sidePanelOpen    = useStore(s => s.sidePanelOpen)
  const sidePanelCountry = useStore(s => s.sidePanelCountry)
  const mapData          = useStore(s => s.mapData)
  const currentDate      = useStore(s => s.currentDate)
  const selectCountry    = useStore(s => s.selectCountry)

  const [countryDetail, setCountryDetail] = useState(null)
  const [trendData, setTrendData] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!sidePanelCountry || !sidePanelOpen) return
    setLoading(true)
    setCountryDetail(null)
    setTrendData(null)

    // Fetch country dimensions
    fetchCountries(currentDate, null, 200)
      .then(res => {
        const country = res.countries.find(c => c.country_code === sidePanelCountry)
        setCountryDetail(country || null)
      })
      .catch(() => {})

    // Fetch 30d global trend as proxy (real country trend would need new API)
    fetchGlobalTrend('30d')
      .then(res => setTrendData(res.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [sidePanelCountry, currentDate])

  const score = mapData[sidePanelCountry]?.score
  const band  = mapData[sidePanelCountry]?.band
  const bandZh = mapData[sidePanelCountry]?.band_zh
  const bandColor = band ? (BAND_COLORS[band] || '#8a8fa8') : '#8a8fa8'
  const countryName = getCountryName(sidePanelCountry)

  const trendOption = trendData ? {
    backgroundColor: 'transparent',
    grid: { top: 10, right: 10, bottom: 20, left: 40 },
    xAxis: {
      type: 'category',
      data: trendData.map(d => d.date.slice(5)),
      axisLabel: { color: '#8a8fa8', fontSize: 9 },
      axisLine: { lineStyle: { color: '#2a2d3a' } },
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      axisLabel: { color: '#8a8fa8', fontSize: 9 },
      splitLine: { lineStyle: { color: '#2a2d3a', type: 'dashed' } },
    },
    series: [{
      type: 'line',
      data: trendData.map(d => d.net_tension),
      smooth: true,
      symbol: 'none',
      lineStyle: { color: bandColor, width: 2 },
      areaStyle: {
        color: {
          type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: `${bandColor}44` },
            { offset: 1, color: `${bandColor}05` },
          ],
        },
      },
    }],
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#151820',
      borderColor: '#2a2d3a',
      textStyle: { color: '#e8eaf0', fontSize: 11 },
    },
  } : null

  return (
    <AnimatePresence>
      {sidePanelOpen && sidePanelCountry && (
        <motion.div
          key="country-panel"
          initial={{ x: '100%', opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: '100%', opacity: 0 }}
          transition={{ type: 'spring', damping: 28, stiffness: 300 }}
          className="absolute right-0 top-0 h-full z-20 overflow-y-auto"
          style={{
            width: '300px',
            background: '#151820ee',
            borderLeft: '1px solid #2a2d3a',
            backdropFilter: 'blur(8px)',
          }}
        >
          {/* Header */}
          <div
            className="flex items-center justify-between p-4"
            style={{ borderBottom: '1px solid #2a2d3a' }}
          >
            <div>
              <div
                className="font-bold text-base text-text"
                style={{ fontFamily: "'Exo 2', sans-serif" }}
              >
                {countryName}
              </div>
              <div className="text-muted text-xs">{sidePanelCountry}</div>
            </div>
            <button
              onClick={() => selectCountry(null)}
              className="text-muted hover:text-text w-7 h-7 flex items-center justify-center rounded transition-colors"
              style={{ background: 'transparent', border: 'none', fontSize: '16px', cursor: 'pointer' }}
            >
              ✕
            </button>
          </div>

          {/* Score */}
          <div className="p-4" style={{ borderBottom: '1px solid #2a2d3a' }}>
            <div className="flex items-end gap-3 mb-2">
              <span
                style={{
                  fontFamily: "'Share Tech Mono', monospace",
                  fontSize: '42px',
                  fontWeight: '900',
                  color: bandColor,
                  lineHeight: 1,
                  textShadow: `0 0 30px ${bandColor}44`,
                }}
              >
                {score != null ? score.toFixed(1) : '—'}
              </span>
              <div className="pb-1">
                <div
                  className="text-xs font-semibold px-2 py-0.5 rounded inline-block"
                  style={{
                    background: `${bandColor}22`,
                    color: bandColor,
                    border: `1px solid ${bandColor}44`,
                  }}
                >
                  {bandZh || '—'}
                </div>
              </div>
            </div>
            {/* Score bar */}
            <div className="h-1.5 rounded-full overflow-hidden" style={{ background: '#2a2d3a' }}>
              <motion.div
                className="h-full rounded-full"
                style={{ background: `linear-gradient(to right, ${bandColor}88, ${bandColor})` }}
                initial={{ width: 0 }}
                animate={{ width: `${score || 0}%` }}
                transition={{ duration: 0.8, ease: 'easeOut' }}
              />
            </div>
          </div>

          {/* Trend chart */}
          <div className="p-4" style={{ borderBottom: '1px solid #2a2d3a' }}>
            <div className="text-muted text-xs mb-2 flex items-center gap-1">
              <span>📈</span>
              <span>近 30 天全球趨勢</span>
            </div>
            {trendOption ? (
              <ReactECharts option={trendOption} style={{ height: '100px' }} />
            ) : (
              <div className="h-24 flex items-center justify-center text-muted text-xs">
                {loading ? '載入中...' : '暫無資料'}
              </div>
            )}
          </div>

          {/* Dimensions */}
          {countryDetail && (
            <div className="p-4" style={{ borderBottom: '1px solid #2a2d3a' }}>
              <div className="text-muted text-xs mb-3 flex items-center gap-1">
                <span>📊</span>
                <span>子維度分析</span>
              </div>
              {Object.entries(DIM_LABELS).map(([key, label]) => (
                <DimBar
                  key={key}
                  label={label}
                  value={countryDetail[key]}
                  color={bandColor}
                />
              ))}
            </div>
          )}

          {/* Date */}
          <div className="p-4 text-muted text-xs text-center">
            資料日期：{currentDate}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
