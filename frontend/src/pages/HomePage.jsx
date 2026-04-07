import { useEffect } from 'react'
import MapView from '../components/MapView'
import Timeline from '../components/Timeline'
import CountryPanel from '../components/CountryPanel'
import MapLegend from '../components/MapLegend'
import useStore from '../store/useStore'
import { fetchMapHeat } from '../api/index'

export default function HomePage() {
  const currentDate  = useStore(s => s.currentDate)
  const mapDimension = useStore(s => s.mapDimension)
  const setMapData   = useStore(s => s.setMapData)
  const setMapLoading = useStore(s => s.setMapLoading)
  const isMapLoading  = useStore(s => s.isMapLoading)
  const setError     = useStore(s => s.setError)

  // Load initial map data for today
  useEffect(() => {
    setMapLoading(true)
    fetchMapHeat(currentDate, mapDimension)
      .then(res => {
        const dataMap = {}
        for (const c of res.countries) {
          dataMap[c.country_code] = { score: c.score, band: c.band, band_zh: c.band_zh }
        }
        setMapData(currentDate, dataMap)
      })
      .catch(() => setError('無法載入地圖資料'))
      .finally(() => setMapLoading(false))
  }, [mapDimension])

  return (
    <div className="flex-1 relative overflow-hidden flex flex-col">
      {/* Map area */}
      <div className="flex-1 relative">
        <MapView />
        <MapLegend />
        <CountryPanel />

        {/* Loading overlay */}
        {isMapLoading && (
          <div
            className="absolute inset-0 flex items-center justify-center z-10 pointer-events-none"
            style={{ background: 'rgba(13,15,20,0.4)' }}
          >
            <div className="flex items-center gap-2 text-muted text-sm">
              <div className="w-4 h-4 border-2 border-accent border-t-transparent rounded-full animate-spin" />
              <span>載入中...</span>
            </div>
          </div>
        )}
      </div>

      {/* Timeline */}
      <Timeline />
    </div>
  )
}
