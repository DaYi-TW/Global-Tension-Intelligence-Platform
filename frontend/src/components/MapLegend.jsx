import { TENSION_COLOR_STOPS, BAND_COLORS } from '../constants'

const LABELS = [
  { score: 10, label: '0–19', zh: '平穩', color: '#1a3a2a', text: '#38a169' },
  { score: 30, label: '20–39', zh: '關注', color: '#2d3a1a', text: '#68d391' },
  { score: 50, label: '40–59', zh: '升溫', color: '#4a3a0a', text: '#d69e2e' },
  { score: 70, label: '60–79', zh: '高壓', color: '#5a2a0a', text: '#dd6b20' },
  { score: 90, label: '80–100', zh: '危機', color: '#6a0a0a', text: '#e53e3e' },
]

export default function MapLegend() {
  return (
    <div
      className="absolute bottom-20 left-3 z-10"
      style={{
        background: '#151820cc',
        border: '1px solid #2a2d3a',
        borderRadius: '6px',
        padding: '10px 12px',
        backdropFilter: 'blur(6px)',
        minWidth: '120px',
      }}
    >
      <div className="text-muted text-xs mb-2 font-semibold uppercase tracking-wider">
        緊張度
      </div>
      {LABELS.map(l => (
        <div key={l.label} className="flex items-center gap-2 mb-1.5">
          <div
            className="w-3 h-3 rounded-sm flex-shrink-0"
            style={{ background: l.color, border: `1px solid ${l.text}44` }}
          />
          <span className="text-xs" style={{ color: l.text }}>{l.zh}</span>
          <span className="text-xs text-muted">{l.label}</span>
        </div>
      ))}
      <div className="flex items-center gap-2 mt-2 pt-2" style={{ borderTop: '1px solid #2a2d3a' }}>
        <div
          className="w-3 h-3 rounded-sm flex-shrink-0"
          style={{ background: '#1a1a2a', border: '1px solid #3a3d4a' }}
        />
        <span className="text-xs text-muted">無資料</span>
      </div>
    </div>
  )
}
