import { useEffect, useRef, useCallback, memo } from 'react'
import maplibregl from 'maplibre-gl'
import useStore from '../store/useStore'
import { scoreToColor, NO_DATA_COLOR, getCountryName, BAND_COLORS } from '../constants'

const ISO_PROP = 'ISO3166-1-Alpha-3'

function scoreToFillColor(score) {
  return scoreToColor(score)
}

// Build a MapLibre 'match' fill-color expression from mapData
function buildColorExpression(mapData) {
  const expr = ['match', ['get', ISO_PROP]]
  const entries = Object.entries(mapData)
  for (const [iso3, d] of entries) {
    if (d && d.score != null) {
      expr.push(iso3, scoreToFillColor(d.score))
    }
  }
  expr.push(NO_DATA_COLOR) // fallback
  return expr
}

const MapView = memo(function MapView() {
  const mapContainer = useRef(null)
  const mapRef       = useRef(null)
  const popup        = useRef(null)
  const hoveredId    = useRef(null)
  const mapLoaded    = useRef(false)

  const mapData     = useStore(s => s.mapData)
  const selectCountry = useStore(s => s.selectCountry)
  const setError    = useStore(s => s.setError)

  // Init map once
  useEffect(() => {
    if (mapRef.current) return
    const map = new maplibregl.Map({
      container: mapContainer.current,
      style: 'https://tiles.openfreemap.org/styles/dark',
      center: [15, 20],
      zoom: 1.8,
      minZoom: 1.0,
      maxZoom: 8,
      attributionControl: false,
    })

    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'bottom-right')

    popup.current = new maplibregl.Popup({
      closeButton: false,
      closeOnClick: false,
      maxWidth: '220px',
    })

    map.on('load', () => {
      // Add countries GeoJSON source
      map.addSource('countries', {
        type: 'geojson',
        data: '/world.geojson',
        generateId: true,
      })

      // Fill layer
      map.addLayer({
        id: 'country-fill',
        type: 'fill',
        source: 'countries',
        paint: {
          'fill-color': NO_DATA_COLOR,
          'fill-opacity': [
            'case',
            ['boolean', ['feature-state', 'hover'], false],
            0.9,
            0.75,
          ],
        },
        transition: { duration: 400, delay: 0 },
      })

      // Border layer
      map.addLayer({
        id: 'country-border',
        type: 'line',
        source: 'countries',
        paint: {
          'line-color': [
            'case',
            ['boolean', ['feature-state', 'hover'], false],
            '#ffffff',
            '#3a3d4a',
          ],
          'line-width': [
            'case',
            ['boolean', ['feature-state', 'hover'], false],
            1.5,
            0.4,
          ],
        },
      })

      // Selected layer
      map.addLayer({
        id: 'country-selected',
        type: 'line',
        source: 'countries',
        paint: {
          'line-color': '#4299e1',
          'line-width': 2,
        },
        filter: ['==', ['get', ISO_PROP], ''],
      })

      mapLoaded.current = true

      // Apply initial data if available
      const currentMapData = useStore.getState().mapData
      if (Object.keys(currentMapData).length > 0) {
        applyColors(map, currentMapData)
      }
    })

    // Hover interactions
    map.on('mousemove', 'country-fill', (e) => {
      map.getCanvas().style.cursor = 'pointer'
      const feature = e.features[0]
      if (!feature) return

      // Update hover state
      if (hoveredId.current !== null) {
        map.setFeatureState({ source: 'countries', id: hoveredId.current }, { hover: false })
      }
      hoveredId.current = feature.id
      map.setFeatureState({ source: 'countries', id: feature.id }, { hover: true })

      const iso3 = feature.properties[ISO_PROP]
      const name = feature.properties['name']
      const countryName = getCountryName(iso3) || name
      const d = useStore.getState().mapData[iso3]

      const score = d?.score
      const band  = d?.band || '—'
      const bandZh = d?.band_zh || '無資料'
      const color = d ? (BAND_COLORS[d.band] || '#8a8fa8') : '#8a8fa8'

      popup.current
        .setLngLat(e.lngLat)
        .setHTML(`
          <div style="font-family:'Exo 2',sans-serif;font-size:13px;color:#e8eaf0">
            <div style="font-weight:700;font-size:14px;margin-bottom:4px">${countryName}</div>
            <div style="color:#8a8fa8;font-size:11px;margin-bottom:6px">${iso3} · ${name}</div>
            <div style="display:flex;align-items:center;gap:8px">
              <span style="font-size:22px;font-weight:900;font-family:'Share Tech Mono',monospace;color:${color}">
                ${score != null ? score.toFixed(1) : '—'}
              </span>
              <span style="padding:2px 6px;background:${color}22;color:${color};border:1px solid ${color}44;border-radius:3px;font-size:11px;font-weight:600">
                ${bandZh}
              </span>
            </div>
          </div>
        `)
        .addTo(map)
    })

    map.on('mouseleave', 'country-fill', () => {
      map.getCanvas().style.cursor = ''
      if (hoveredId.current !== null) {
        map.setFeatureState({ source: 'countries', id: hoveredId.current }, { hover: false })
        hoveredId.current = null
      }
      popup.current.remove()
    })

    // Click → select country
    map.on('click', 'country-fill', (e) => {
      const feature = e.features[0]
      if (!feature) return
      const iso3 = feature.properties[ISO_PROP]
      selectCountry(iso3)
      // Highlight selected
      map.setFilter('country-selected', ['==', ['get', ISO_PROP], iso3])
    })

    // Click on empty space → deselect
    map.on('click', (e) => {
      const features = map.queryRenderedFeatures(e.point, { layers: ['country-fill'] })
      if (features.length === 0) {
        selectCountry(null)
        map.setFilter('country-selected', ['==', ['get', ISO_PROP], ''])
      }
    })

    map.on('error', (e) => {
      console.warn('Map error:', e.error)
    })

    mapRef.current = map
    return () => {
      map.remove()
      mapRef.current = null
      mapLoaded.current = false
    }
  }, [])

  // Apply colors whenever mapData changes
  const applyColors = useCallback((map, data) => {
    if (!map || !map.isStyleLoaded()) return
    try {
      const expr = buildColorExpression(data)
      map.setPaintProperty('country-fill', 'fill-color', expr)
    } catch (err) {
      console.warn('Color update error:', err)
    }
  }, [])

  useEffect(() => {
    if (!mapLoaded.current || !mapRef.current) return
    applyColors(mapRef.current, mapData)
  }, [mapData, applyColors])

  return (
    <div className="absolute inset-0 w-full h-full" ref={mapContainer} />
  )
})

export default MapView
