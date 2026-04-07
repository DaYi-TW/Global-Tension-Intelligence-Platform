import { useEffect, useState } from 'react'
import ReactECharts from 'echarts-for-react'
import { fetchDashboardOverview, fetchGlobalTrend, fetchRegions } from '../api/index'
import { BAND_COLORS } from '../constants'

function StatCard({ title, value, sub, color }) {
  return (
    <div
      className="rounded p-4 flex flex-col gap-1"
      style={{ background: '#151820', border: '1px solid #2a2d3a' }}
    >
      <div className="text-muted text-xs uppercase tracking-wider">{title}</div>
      <div
        className="font-mono font-bold"
        style={{
          fontFamily: "'Share Tech Mono', monospace",
          fontSize: '32px',
          color: color || '#e8eaf0',
          lineHeight: 1,
        }}
      >
        {value ?? '—'}
      </div>
      {sub && <div className="text-muted text-xs">{sub}</div>}
    </div>
  )
}

export default function DashboardPage() {
  const [overview, setOverview] = useState(null)
  const [trend, setTrend] = useState(null)
  const [regions, setRegions] = useState(null)
  const [trendRange, setTrendRange] = useState('30d')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      fetchDashboardOverview(),
      fetchGlobalTrend(trendRange),
      fetchRegions(),
    ]).then(([ov, tr, reg]) => {
      setOverview(ov)
      setTrend(tr)
      setRegions(reg)
    }).catch(console.error).finally(() => setLoading(false))
  }, [trendRange])

  if (loading) return (
    <div className="flex-1 flex items-center justify-center text-muted">
      <div className="flex items-center gap-2">
        <div className="w-5 h-5 border-2 border-accent border-t-transparent rounded-full animate-spin" />
        <span>載入中...</span>
      </div>
    </div>
  )

  const score = overview?.global_tension
  const band  = overview?.global_band || 'Watch'
  const bandColor = BAND_COLORS[band] || '#8a8fa8'

  // Gauge chart
  const gaugeOption = {
    backgroundColor: 'transparent',
    series: [{
      type: 'gauge',
      startAngle: 210,
      endAngle: -30,
      min: 0,
      max: 100,
      radius: '90%',
      progress: { show: true, width: 12, itemStyle: { color: bandColor } },
      axisLine: { lineStyle: { width: 12, color: [[1, '#2a2d3a']] } },
      axisTick: { show: false },
      splitLine: {
        length: 10,
        lineStyle: { color: '#3a3d4a', width: 1 },
      },
      axisLabel: {
        distance: 20,
        color: '#8a8fa8',
        fontSize: 10,
      },
      pointer: {
        show: true,
        length: '65%',
        width: 4,
        itemStyle: { color: bandColor },
      },
      anchor: {
        show: true,
        size: 10,
        itemStyle: { color: bandColor },
      },
      detail: {
        valueAnimation: true,
        fontSize: 32,
        fontFamily: "'Share Tech Mono', monospace",
        color: bandColor,
        offsetCenter: [0, '20%'],
        formatter: '{value}',
      },
      title: {
        offsetCenter: [0, '45%'],
        color: '#8a8fa8',
        fontSize: 12,
        fontFamily: "'Exo 2', sans-serif",
      },
      data: [{ value: score?.toFixed(1) || 0, name: overview?.global_band_zh || '' }],
    }],
  }

  // Trend line chart
  const trendOption = trend ? {
    backgroundColor: 'transparent',
    grid: { top: 30, right: 20, bottom: 30, left: 50 },
    legend: {
      top: 0,
      textStyle: { color: '#8a8fa8', fontSize: 10 },
    },
    xAxis: {
      type: 'category',
      data: trend.data.map(d => d.date),
      axisLabel: {
        color: '#8a8fa8',
        fontSize: 9,
        rotate: 30,
        interval: Math.floor(trend.data.length / 6),
      },
      axisLine: { lineStyle: { color: '#2a2d3a' } },
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      axisLabel: { color: '#8a8fa8', fontSize: 9 },
      splitLine: { lineStyle: { color: '#2a2d3a', type: 'dashed' } },
    },
    series: [
      {
        name: '綜合',
        type: 'line',
        data: trend.data.map(d => d.net_tension),
        smooth: true, symbol: 'none',
        lineStyle: { color: bandColor, width: 2.5 },
        areaStyle: { color: `${bandColor}22` },
      },
      {
        name: '軍事',
        type: 'line',
        data: trend.data.map(d => d.military),
        smooth: true, symbol: 'none',
        lineStyle: { color: '#e53e3e', width: 1, type: 'dashed' },
      },
      {
        name: '政治',
        type: 'line',
        data: trend.data.map(d => d.political),
        smooth: true, symbol: 'none',
        lineStyle: { color: '#dd6b20', width: 1, type: 'dashed' },
      },
      {
        name: '經濟',
        type: 'line',
        data: trend.data.map(d => d.economic),
        smooth: true, symbol: 'none',
        lineStyle: { color: '#d69e2e', width: 1, type: 'dashed' },
      },
    ],
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#151820',
      borderColor: '#2a2d3a',
      textStyle: { color: '#e8eaf0', fontSize: 11 },
    },
  } : null

  // Region bar chart
  const regionOption = regions ? {
    backgroundColor: 'transparent',
    grid: { top: 5, right: 80, bottom: 5, left: 120 },
    xAxis: {
      type: 'value',
      min: 0,
      max: 100,
      axisLabel: { color: '#8a8fa8', fontSize: 9 },
      splitLine: { lineStyle: { color: '#2a2d3a', type: 'dashed' } },
    },
    yAxis: {
      type: 'category',
      data: (regions.regions || []).slice().reverse().map(r => {
        const names = {
          east_asia: '東亞', north_america: '北美', middle_east: '中東',
          south_asia: '南亞', europe: '歐洲', southeast_asia: '東南亞',
          latin_america: '拉美', africa: '非洲', central_asia: '中亞',
        }
        return names[r.region_code] || r.region_code
      }),
      axisLabel: { color: '#e8eaf0', fontSize: 11 },
      axisLine: { lineStyle: { color: '#2a2d3a' } },
    },
    series: [{
      type: 'bar',
      data: (regions.regions || []).slice().reverse().map(r => ({
        value: r.net_tension,
        itemStyle: {
          color: BAND_COLORS[r.band] || '#8a8fa8',
          borderRadius: [0, 3, 3, 0],
        },
      })),
      label: {
        show: true,
        position: 'right',
        color: '#e8eaf0',
        fontSize: 11,
        fontFamily: "'Share Tech Mono', monospace",
        formatter: '{c}',
      },
    }],
    tooltip: {
      backgroundColor: '#151820',
      borderColor: '#2a2d3a',
      textStyle: { color: '#e8eaf0', fontSize: 11 },
    },
  } : null

  const dims = overview?.dimensions
  const dimEntries = dims ? [
    { key: 'military',  label: '軍事', value: dims.military, color: '#e53e3e' },
    { key: 'political', label: '政治', value: dims.political, color: '#dd6b20' },
    { key: 'economic',  label: '經濟', value: dims.economic, color: '#d69e2e' },
    { key: 'social',    label: '社會', value: dims.social, color: '#48bb78' },
    { key: 'cyber',     label: '網路', value: dims.cyber, color: '#4299e1' },
  ] : []

  return (
    <div className="flex-1 overflow-y-auto" style={{ background: '#0d0f14' }}>
      <div className="max-w-7xl mx-auto p-6">

        {/* Title */}
        <div className="mb-6">
          <h1
            className="text-text font-black text-2xl tracking-widest"
            style={{ fontFamily: "'Exo 2', sans-serif" }}
          >
            全球局勢儀表板
          </h1>
          <div className="text-muted text-sm mt-1">{overview?.date || '—'} · 評分版本 {overview?.scoring_version || '—'}</div>
        </div>

        {/* Top row: gauge + stat cards */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
          {/* Gauge */}
          <div
            className="rounded p-4"
            style={{ background: '#151820', border: '1px solid #2a2d3a' }}
          >
            <div className="text-muted text-xs uppercase tracking-wider mb-2">世界緊張度</div>
            <ReactECharts option={gaugeOption} style={{ height: '200px' }} />
          </div>

          {/* Stat cards */}
          <div className="grid grid-cols-2 gap-3 lg:col-span-2">
            <StatCard
              title="今日評分"
              value={score?.toFixed(1)}
              sub={`較昨日 ${overview?.global_delta > 0 ? '↑' : '↓'}${Math.abs(overview?.global_delta || 0).toFixed(1)}`}
              color={bandColor}
            />
            <StatCard
              title="等級"
              value={overview?.global_band_zh || '—'}
              sub={band}
              color={bandColor}
            />
            {dimEntries.slice(0, 4).map(d => (
              <StatCard key={d.key} title={d.label} value={d.value?.toFixed(1)} color={d.color} />
            ))}
          </div>
        </div>

        {/* Trend chart */}
        <div
          className="rounded p-4 mb-4"
          style={{ background: '#151820', border: '1px solid #2a2d3a' }}
        >
          <div className="flex items-center justify-between mb-3">
            <div className="text-text text-sm font-semibold">全球緊張度趨勢</div>
            <div className="flex gap-1">
              {['7d', '30d', '90d', '1y'].map(r => (
                <button
                  key={r}
                  onClick={() => setTrendRange(r)}
                  className="px-2 py-1 text-xs rounded transition-all"
                  style={trendRange === r
                    ? { background: '#4299e122', color: '#4299e1', border: '1px solid #4299e144' }
                    : { background: 'transparent', color: '#8a8fa8', border: '1px solid transparent' }
                  }
                >
                  {r}
                </button>
              ))}
            </div>
          </div>
          {trendOption
            ? <ReactECharts option={trendOption} style={{ height: '200px' }} />
            : <div className="h-48 flex items-center justify-center text-muted text-xs">暫無資料</div>
          }
        </div>

        {/* Bottom: region bars + top countries */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
          {/* Region bars */}
          <div
            className="rounded p-4"
            style={{ background: '#151820', border: '1px solid #2a2d3a' }}
          >
            <div className="text-text text-sm font-semibold mb-3">區域緊張度排行</div>
            {regionOption
              ? <ReactECharts option={regionOption} style={{ height: '260px' }} />
              : <div className="h-48 flex items-center justify-center text-muted text-xs">暫無資料</div>
            }
          </div>

          {/* Top countries */}
          <div
            className="rounded p-4"
            style={{ background: '#151820', border: '1px solid #2a2d3a' }}
          >
            <div className="text-text text-sm font-semibold mb-3">今日高張力國家 Top 5</div>
            <div className="space-y-3">
              {(overview?.top_countries || []).map((c, i) => {
                const cc = BAND_COLORS[c.band] || '#8a8fa8'
                return (
                  <div key={c.country_code} className="flex items-center gap-3">
                    <span className="text-muted text-xs w-4 text-right">{i + 1}</span>
                    <span className="text-text text-sm font-mono w-8">{c.country_code}</span>
                    <div className="flex-1 bg-border rounded-full h-1.5 overflow-hidden">
                      <div
                        className="h-full rounded-full"
                        style={{ width: `${c.net_tension}%`, background: cc }}
                      />
                    </div>
                    <span className="text-xs font-mono w-10 text-right" style={{ color: cc, fontFamily: "'Share Tech Mono', monospace" }}>
                      {c.net_tension}
                    </span>
                    <span
                      className="text-xs px-1.5 py-0.5 rounded"
                      style={{ background: `${cc}22`, color: cc, border: `1px solid ${cc}44`, fontSize: '10px' }}
                    >
                      {c.band_zh}
                    </span>
                  </div>
                )
              })}
            </div>
          </div>
        </div>

        {/* AI summary */}
        {overview?.ai_daily_summary && (
          <div
            className="rounded p-4"
            style={{ background: '#151820', border: '1px solid #2a2d3a' }}
          >
            <div className="text-text text-sm font-semibold mb-2 flex items-center gap-2">
              <span>🤖</span>
              <span>AI 今日摘要</span>
            </div>
            <p className="text-muted text-sm leading-relaxed">{overview.ai_daily_summary}</p>
          </div>
        )}

      </div>
    </div>
  )
}
