import { Link, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { useEffect, useState } from 'react'
import useStore from '../store/useStore'
import { DIMENSIONS, BAND_COLORS } from '../constants'

function AnimatedNumber({ value }) {
  const [displayed, setDisplayed] = useState(value)
  useEffect(() => {
    if (value === null || value === undefined) return
    const target = value
    const start = displayed || 0
    const diff = target - start
    const steps = 20
    let step = 0
    const timer = setInterval(() => {
      step++
      setDisplayed(+(start + diff * (step / steps)).toFixed(1))
      if (step >= steps) { clearInterval(timer); setDisplayed(target) }
    }, 20)
    return () => clearInterval(timer)
  }, [value])
  return <>{displayed != null ? displayed.toFixed(1) : '—'}</>
}

export default function TopBar({ globalData }) {
  const mapDimension = useStore(s => s.mapDimension)
  const setDimension = useStore(s => s.setDimension)
  const currentDate  = useStore(s => s.currentDate)
  const location     = useLocation()

  const score = globalData?.global_tension
  const delta = globalData?.global_delta
  const band  = globalData?.global_band || 'Watch'
  const bandZh = globalData?.global_band_zh || '—'
  const bandColor = BAND_COLORS[band] || '#8a8fa8'

  return (
    <div
      className="relative z-30 flex-shrink-0 flex items-center justify-between px-4"
      style={{
        background: '#0d0f14ee',
        borderBottom: '1px solid #2a2d3a',
        height: '56px',
        backdropFilter: 'blur(8px)',
      }}
    >
      {/* Left: Logo + score */}
      <div className="flex items-center gap-4">
        <Link to="/" className="flex items-center gap-2 no-underline">
          <span className="text-lg">🌐</span>
          <span
            className="font-display font-black tracking-widest text-text"
            style={{ fontFamily: "'Exo 2', sans-serif", fontSize: '14px', letterSpacing: '0.15em' }}
          >
            GTIP
          </span>
        </Link>

        {/* Global score */}
        <div className="flex items-center gap-3 pl-4" style={{ borderLeft: '1px solid #2a2d3a' }}>
          <span
            style={{
              fontFamily: "'Share Tech Mono', monospace",
              fontSize: '26px',
              fontWeight: '900',
              color: bandColor,
              lineHeight: 1,
              textShadow: `0 0 20px ${bandColor}44`,
            }}
          >
            <AnimatedNumber value={score} />
          </span>

          {delta !== null && delta !== undefined && (
            <span
              className="text-xs font-mono"
              style={{ color: delta > 0 ? '#e53e3e' : '#38a169' }}
            >
              {delta > 0 ? '↑' : '↓'}{Math.abs(delta).toFixed(1)}
            </span>
          )}

          <span
            className="text-xs font-semibold px-2 py-0.5 rounded"
            style={{
              background: `${bandColor}22`,
              color: bandColor,
              border: `1px solid ${bandColor}44`,
              fontFamily: "'Exo 2', sans-serif",
              letterSpacing: '0.05em',
            }}
          >
            {band.toUpperCase()}
          </span>
        </div>
      </div>

      {/* Center: Dimension tabs */}
      <div className="flex items-center gap-1">
        {DIMENSIONS.map(d => (
          <button
            key={d.key}
            onClick={() => setDimension(d.key)}
            className="px-3 py-1 text-xs rounded transition-all font-semibold"
            style={mapDimension === d.key
              ? {
                  background: '#4299e122',
                  color: '#4299e1',
                  border: '1px solid #4299e144',
                }
              : {
                  background: 'transparent',
                  color: '#8a8fa8',
                  border: '1px solid transparent',
                }
            }
          >
            {d.label}
          </button>
        ))}
      </div>

      {/* Right: date + nav */}
      <div className="flex items-center gap-4">
        <span
          className="text-muted text-sm"
          style={{ fontFamily: "'Share Tech Mono', monospace" }}
        >
          {currentDate}
        </span>
        <div className="flex items-center gap-1" style={{ borderLeft: '1px solid #2a2d3a', paddingLeft: '12px' }}>
          <Link
            to="/"
            className="px-3 py-1 text-xs rounded transition-colors no-underline"
            style={{
              color: location.pathname === '/' ? '#4299e1' : '#8a8fa8',
              background: location.pathname === '/' ? '#4299e122' : 'transparent',
            }}
          >
            地圖
          </Link>
          <Link
            to="/dashboard"
            className="px-3 py-1 text-xs rounded transition-colors no-underline"
            style={{
              color: location.pathname === '/dashboard' ? '#4299e1' : '#8a8fa8',
              background: location.pathname === '/dashboard' ? '#4299e122' : 'transparent',
            }}
          >
            儀表板
          </Link>
        </div>
      </div>
    </div>
  )
}
