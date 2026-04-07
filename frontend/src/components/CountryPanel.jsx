import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import ReactECharts from 'echarts-for-react'
import useStore from '../store/useStore'
import { BAND_COLORS, getCountryName } from '../constants'
import { fetchCountries, fetchGlobalTrend, fetchEvents } from '../api/index'

const DIM_LABELS = {
  military:  '軍事',
  political: '政治',
  economic:  '經濟',
  social:    '社會',
  cyber:     '網路',
}

const EVENT_TYPE_ZH = {
  military_clash:    '軍事衝突',
  nuclear_threat:    '核武威脅',
  territorial_dispute: '領土爭端',
  sanctions:         '制裁措施',
  diplomatic_crisis: '外交危機',
  cyber_attack:      '網路攻擊',
  protest_unrest:    '抗議動亂',
  humanitarian:      '人道危機',
  ceasefire:         '停火協議',
  peace_talks:       '和平談判',
  economic_deal:     '經貿協議',
  military_exercise: '軍事演習',
  arms_deal:         '武器交易',
  refugee_crisis:    '難民危機',
  election:          '選舉事件',
  coup:              '政變',
  terrorism:         '恐怖攻擊',
  default:           '一般事件',
}

function getEventTypeZh(type) {
  return EVENT_TYPE_ZH[type] || type || '事件'
}

function DimBar({ label, value, color }) {
  return (
    <div className="flex items-center gap-2 mb-1.5">
      <span className="text-xs w-8 flex-shrink-0" style={{ color: '#8a8fa8' }}>{label}</span>
      <div className="flex-1 rounded-full h-1.5 overflow-hidden" style={{ background: '#2a2d3a' }}>
        <motion.div
          className="h-full rounded-full"
          style={{ background: color }}
          initial={{ width: 0 }}
          animate={{ width: `${value || 0}%` }}
          transition={{ duration: 0.6, ease: 'easeOut' }}
        />
      </div>
      <span className="text-xs w-8 text-right font-mono flex-shrink-0" style={{ color: '#e8eaf0', fontFamily: "'Share Tech Mono', monospace" }}>
        {value?.toFixed(1) ?? '—'}
      </span>
    </div>
  )
}

function ScoreBreakdown({ breakdown }) {
  if (!breakdown) return null
  const rows = [
    { label: '基礎嚴重度', value: breakdown.base_severity, fmt: v => v?.toFixed(3) },
    { label: '× 範圍權重', value: breakdown.scope_weight, fmt: v => `×${v?.toFixed(2)}` },
    { label: '× 地緣敏感度', value: breakdown.geo_sensitivity, fmt: v => `×${v?.toFixed(2)}` },
    { label: '× 行為者重要性', value: breakdown.actor_importance, fmt: v => `×${v?.toFixed(2)}` },
    { label: '× 來源信心', value: breakdown.source_confidence, fmt: v => `×${v?.toFixed(2)}` },
    { label: '× 時間衰減', value: breakdown.time_decay, fmt: v => `×${v?.toFixed(3)}` },
  ]
  return (
    <div className="rounded p-2.5 mt-1" style={{ background: '#1a1d26', border: '1px solid #2a2d3a' }}>
      {rows.map(r => (
        <div key={r.label} className="flex justify-between items-center py-0.5">
          <span style={{ color: '#8a8fa8', fontSize: '11px' }}>{r.label}</span>
          <span style={{ color: '#e8eaf0', fontSize: '11px', fontFamily: "'Share Tech Mono', monospace" }}>
            {r.value != null ? r.fmt(r.value) : '—'}
          </span>
        </div>
      ))}
    </div>
  )
}

function EventCard({ event, isExpanded, onToggle }) {
  const isRisk = event.risk_or_relief === 'risk'
  const accentColor = isRisk ? '#e53e3e' : '#38a169'
  const score = event.final_score
  const newsItems = event.news_sources || []

  return (
    <div
      className="rounded overflow-hidden cursor-pointer transition-all"
      style={{
        background: isExpanded ? '#1a1d26' : '#151820',
        border: `1px solid ${isExpanded ? accentColor + '44' : '#2a2d3a'}`,
        marginBottom: '8px',
      }}
      onClick={onToggle}
    >
      {/* Card header */}
      <div className="flex items-start gap-2 p-3">
        {/* Risk/relief indicator */}
        <div
          className="flex-shrink-0 w-1.5 self-stretch rounded-full mt-0.5"
          style={{ background: accentColor, minHeight: '12px' }}
        />

        <div className="flex-1 min-w-0">
          {/* Type badge + score */}
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span
              className="text-xs px-1.5 py-0.5 rounded font-semibold flex-shrink-0"
              style={{
                background: `${accentColor}22`,
                color: accentColor,
                border: `1px solid ${accentColor}44`,
                fontSize: '10px',
              }}
            >
              {getEventTypeZh(event.event_type)}
            </span>
            {score != null && (
              <span
                className="text-xs font-mono font-bold flex-shrink-0"
                style={{
                  color: accentColor,
                  fontFamily: "'Share Tech Mono', monospace",
                }}
              >
                {isRisk ? '+' : '-'}{score.toFixed(1)}
              </span>
            )}
            <span className="text-xs flex-shrink-0" style={{ color: '#8a8fa8' }}>
              {event.event_time ? event.event_time.slice(0, 10) : ''}
            </span>
          </div>

          {/* Title */}
          <div
            className="text-xs leading-snug"
            style={{ color: '#c8cad4', wordBreak: 'break-word' }}
          >
            {/* Clean up [GDELT] prefix */}
            {event.title?.replace(/^\[GDELT\]\s*/, '') || '—'}
          </div>

          {/* Countries involved */}
          {event.countries?.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-1.5">
              {event.countries.slice(0, 5).map(c => (
                <span
                  key={c}
                  className="text-xs px-1.5 py-0.5 rounded"
                  style={{ background: '#2a2d3a', color: '#8a8fa8', fontSize: '10px' }}
                >
                  {c}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Expand arrow */}
        <span
          className="flex-shrink-0 text-xs transition-transform duration-200"
          style={{
            color: '#8a8fa8',
            transform: isExpanded ? 'rotate(180deg)' : 'rotate(0)',
          }}
        >
          ▾
        </span>
      </div>

      {/* Expanded detail */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            style={{ overflow: 'hidden', borderTop: `1px solid ${accentColor}22` }}
            onClick={e => e.stopPropagation()}
          >
            <div className="px-3 pb-3 pt-2">

              {/* Score breakdown */}
              {event.score_breakdown && (
                <div className="mb-3">
                  <div className="text-xs font-semibold mb-1" style={{ color: '#8a8fa8' }}>
                    📊 評分分解
                  </div>
                  <ScoreBreakdown breakdown={event.score_breakdown} />
                  <div
                    className="flex justify-between items-center mt-1.5 px-2.5 py-1.5 rounded"
                    style={{ background: `${accentColor}18`, border: `1px solid ${accentColor}33` }}
                  >
                    <span style={{ color: accentColor, fontSize: '12px', fontWeight: 700 }}>最終分數</span>
                    <span style={{ color: accentColor, fontSize: '14px', fontWeight: 900, fontFamily: "'Share Tech Mono', monospace" }}>
                      {score?.toFixed(2)}
                    </span>
                  </div>
                </div>
              )}

              {/* Dimensions */}
              {event.dimensions && (
                <div className="mb-3">
                  <div className="text-xs font-semibold mb-1.5" style={{ color: '#8a8fa8' }}>
                    🎯 影響面向
                  </div>
                  {Object.entries(DIM_LABELS).map(([key, label]) => (
                    event.dimensions[key] != null && (
                      <DimBar key={key} label={label} value={event.dimensions[key]} color={accentColor} />
                    )
                  ))}
                </div>
              )}

              {/* News sources */}
              {newsItems.length > 0 && (
                <div>
                  <div className="text-xs font-semibold mb-1.5" style={{ color: '#8a8fa8' }}>
                    📰 新聞來源（{newsItems.length} 則）
                  </div>
                  <div className="space-y-1.5">
                    {newsItems.slice(0, 4).map((n, i) => (
                      <a
                        key={i}
                        href={n.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-start gap-2 p-2 rounded transition-colors no-underline group"
                        style={{
                          background: '#0d0f14',
                          border: '1px solid #2a2d3a',
                          display: 'flex',
                        }}
                        onClick={e => e.stopPropagation()}
                      >
                        <span
                          className="flex-shrink-0 px-1.5 py-0.5 rounded text-xs font-semibold"
                          style={{ background: '#2a2d3a', color: '#8a8fa8', fontSize: '10px', whiteSpace: 'nowrap' }}
                        >
                          {n.source_name || 'News'}
                        </span>
                        <span
                          className="text-xs leading-snug flex-1 min-w-0"
                          style={{ color: '#a0a4b8', wordBreak: 'break-word' }}
                        >
                          {n.title || n.url}
                        </span>
                        <span className="flex-shrink-0 text-xs" style={{ color: '#4299e1' }}>↗</span>
                      </a>
                    ))}
                    {newsItems.length > 4 && (
                      <div className="text-xs text-center" style={{ color: '#8a8fa8' }}>
                        +{newsItems.length - 4} 則更多來源
                      </div>
                    )}
                  </div>
                </div>
              )}

            </div>
          </motion.div>
        )}
      </AnimatePresence>
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
  const [trendData, setTrendData]         = useState(null)
  const [events, setEvents]               = useState([])
  const [loading, setLoading]             = useState(false)
  const [expandedEvent, setExpandedEvent] = useState(null)
  const [activeTab, setActiveTab]         = useState('events') // 'events' | 'dims'

  useEffect(() => {
    if (!sidePanelCountry || !sidePanelOpen) return
    setLoading(true)
    setCountryDetail(null)
    setTrendData(null)
    setEvents([])
    setExpandedEvent(null)

    Promise.all([
      fetchCountries(currentDate, null, 200),
      fetchGlobalTrend('30d'),
      fetchEvents({ country: sidePanelCountry, limit: 20, date: currentDate }),
    ])
      .then(([res, trendRes, eventsRes]) => {
        const country = res.countries.find(c => c.country_code === sidePanelCountry)
        setCountryDetail(country || null)
        setTrendData(trendRes.data)
        setEvents(eventsRes.events || [])
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [sidePanelCountry, sidePanelOpen, currentDate])

  const score     = mapData[sidePanelCountry]?.score
  const band      = mapData[sidePanelCountry]?.band
  const bandZh    = mapData[sidePanelCountry]?.band_zh
  const bandColor = band ? (BAND_COLORS[band] || '#8a8fa8') : '#8a8fa8'
  const countryName = getCountryName(sidePanelCountry)

  const trendOption = trendData ? {
    backgroundColor: 'transparent',
    grid: { top: 5, right: 8, bottom: 18, left: 36 },
    xAxis: {
      type: 'category',
      data: trendData.map(d => d.date.slice(5)),
      axisLabel: { color: '#8a8fa8', fontSize: 9, interval: Math.floor(trendData.length / 4) },
      axisLine: { lineStyle: { color: '#2a2d3a' } },
    },
    yAxis: {
      type: 'value', min: 0, max: 100,
      axisLabel: { color: '#8a8fa8', fontSize: 9 },
      splitLine: { lineStyle: { color: '#2a2d3a', type: 'dashed' } },
    },
    series: [{
      type: 'line',
      data: trendData.map(d => d.net_tension),
      smooth: true, symbol: 'none',
      lineStyle: { color: bandColor, width: 2 },
      areaStyle: {
        color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [{ offset: 0, color: `${bandColor}44` }, { offset: 1, color: `${bandColor}05` }] },
      },
    }],
    tooltip: { trigger: 'axis', backgroundColor: '#151820', borderColor: '#2a2d3a', textStyle: { color: '#e8eaf0', fontSize: 11 } },
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
          className="absolute right-0 top-0 h-full z-20 flex flex-col"
          style={{
            width: '340px',
            background: '#151820ee',
            borderLeft: '1px solid #2a2d3a',
            backdropFilter: 'blur(8px)',
          }}
        >
          {/* ── Header ─────────────────────────────────────────── */}
          <div className="flex items-center justify-between p-4 flex-shrink-0" style={{ borderBottom: '1px solid #2a2d3a' }}>
            <div>
              <div className="font-bold text-base" style={{ color: '#e8eaf0', fontFamily: "'Exo 2', sans-serif" }}>
                {countryName}
              </div>
              <div className="text-xs" style={{ color: '#8a8fa8' }}>{sidePanelCountry} · {currentDate}</div>
            </div>
            <button
              onClick={() => selectCountry(null)}
              style={{ background: 'transparent', border: 'none', color: '#8a8fa8', fontSize: '18px', cursor: 'pointer', padding: '4px 8px' }}
            >
              ✕
            </button>
          </div>

          {/* ── Score bar ──────────────────────────────────────── */}
          <div className="px-4 py-3 flex-shrink-0" style={{ borderBottom: '1px solid #2a2d3a' }}>
            <div className="flex items-end gap-3 mb-2">
              <span style={{
                fontFamily: "'Share Tech Mono', monospace", fontSize: '40px', fontWeight: '900',
                color: bandColor, lineHeight: 1, textShadow: `0 0 24px ${bandColor}44`,
              }}>
                {score != null ? score.toFixed(1) : '—'}
              </span>
              <div className="pb-1">
                <span className="text-xs font-semibold px-2 py-0.5 rounded" style={{
                  background: `${bandColor}22`, color: bandColor, border: `1px solid ${bandColor}44`,
                }}>
                  {bandZh || '—'}
                </span>
              </div>
            </div>
            <div className="h-1.5 rounded-full overflow-hidden" style={{ background: '#2a2d3a' }}>
              <motion.div className="h-full rounded-full"
                style={{ background: `linear-gradient(to right, ${bandColor}88, ${bandColor})` }}
                initial={{ width: 0 }}
                animate={{ width: `${score || 0}%` }}
                transition={{ duration: 0.8, ease: 'easeOut' }}
              />
            </div>
          </div>

          {/* ── Trend ──────────────────────────────────────────── */}
          <div className="px-4 pt-3 pb-1 flex-shrink-0" style={{ borderBottom: '1px solid #2a2d3a' }}>
            <div className="text-xs mb-1" style={{ color: '#8a8fa8' }}>📈 近 30 天全球趨勢（參考）</div>
            {trendOption
              ? <ReactECharts option={trendOption} style={{ height: '80px' }} />
              : <div style={{ height: '80px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#8a8fa8', fontSize: '12px' }}>
                  {loading ? '載入中...' : '暫無資料'}
                </div>
            }
          </div>

          {/* ── Tab switcher ──────────────────────────────────── */}
          <div className="flex flex-shrink-0" style={{ borderBottom: '1px solid #2a2d3a' }}>
            {[
              { key: 'events', label: `影響事件 ${events.length > 0 ? `(${events.length})` : ''}` },
              { key: 'dims',   label: '子維度' },
            ].map(tab => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className="flex-1 py-2.5 text-xs font-semibold transition-colors"
                style={{
                  background: activeTab === tab.key ? '#1a1d26' : 'transparent',
                  color: activeTab === tab.key ? '#e8eaf0' : '#8a8fa8',
                  borderBottom: activeTab === tab.key ? `2px solid ${bandColor}` : '2px solid transparent',
                  cursor: 'pointer',
                  border: 'none',
                  borderBottom: activeTab === tab.key ? `2px solid ${bandColor}` : '2px solid transparent',
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* ── Scrollable content ─────────────────────────────── */}
          <div className="flex-1 overflow-y-auto p-3">

            {/* Events tab */}
            {activeTab === 'events' && (
              <div>
                {loading && (
                  <div className="flex items-center justify-center py-8" style={{ color: '#8a8fa8', fontSize: '12px' }}>
                    <div className="w-4 h-4 border-2 border-accent border-t-transparent rounded-full animate-spin mr-2" style={{ borderColor: bandColor, borderTopColor: 'transparent' }} />
                    載入中...
                  </div>
                )}
                {!loading && events.length === 0 && (
                  <div className="text-center py-8" style={{ color: '#8a8fa8', fontSize: '12px' }}>
                    今日暫無相關事件資料
                  </div>
                )}
                {events.map(ev => (
                  <EventCard
                    key={ev.event_id}
                    event={ev}
                    isExpanded={expandedEvent === ev.event_id}
                    onToggle={() => setExpandedEvent(expandedEvent === ev.event_id ? null : ev.event_id)}
                  />
                ))}
              </div>
            )}

            {/* Dimensions tab */}
            {activeTab === 'dims' && (
              <div className="pt-1">
                {countryDetail ? (
                  Object.entries(DIM_LABELS).map(([key, label]) => (
                    <DimBar key={key} label={label} value={countryDetail[key]} color={bandColor} />
                  ))
                ) : (
                  <div className="text-center py-8" style={{ color: '#8a8fa8', fontSize: '12px' }}>
                    {loading ? '載入中...' : '暫無資料'}
                  </div>
                )}
              </div>
            )}

          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
