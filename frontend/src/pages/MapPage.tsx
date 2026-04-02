import { useState, useEffect, useRef, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Filter, Layers, X, GripHorizontal, Plus, Minus, Locate } from 'lucide-react'
import { getShipments } from '../api/shipments'
import { getRegions } from '../api/regions'
import { RiskBadge } from '../components/ui/RiskBadge'
import { WarStateBadge } from '../components/ui/WarStateBadge'
import type { Shipment, GeopoliticalRegion } from '../types'

// ─── Map math helpers ─────────────────────────────────────────────────────────
function latLonToTile(lat: number, lon: number, zoom: number) {
  const n = Math.pow(2, zoom)
  const x = Math.floor(((lon + 180) / 360) * n)
  const latRad = (lat * Math.PI) / 180
  const y = Math.floor(((1 - Math.log(Math.tan(latRad) + 1 / Math.cos(latRad)) / Math.PI) / 2) * n)
  return { x, y }
}

function tileToLatLon(x: number, y: number, zoom: number) {
  const n = Math.pow(2, zoom)
  const lon = (x / n) * 360 - 180
  const latRad = Math.atan(Math.sinh(Math.PI * (1 - (2 * y) / n)))
  const lat = (latRad * 180) / Math.PI
  return { lat, lon }
}

function latLonToPixel(lat: number, lon: number, centerLat: number, centerLon: number, zoom: number, width: number, height: number) {
  const scale = Math.pow(2, zoom)
  const worldSize = 256 * scale

  const lonToX = (l: number) => ((l + 180) / 360) * worldSize
  const latToY = (l: number) => {
    const r = (l * Math.PI) / 180
    return ((1 - Math.log(Math.tan(r) + 1 / Math.cos(r)) / Math.PI) / 2) * worldSize
  }

  const cx = lonToX(centerLon)
  const cy = latToY(centerLat)
  const px = lonToX(lon) - cx + width / 2
  const py = latToY(lat) - cy + height / 2
  return { x: px, y: py }
}

// ─── Realistic Map using OpenStreetMap tiles ──────────────────────────────────
function TileMap({
  centerLat, centerLon, zoom, width, height,
}: { centerLat: number; centerLon: number; zoom: number; width: number; height: number }) {
  const scale = Math.pow(2, zoom)
  const worldSize = 256 * scale
  const lonToX = (l: number) => ((l + 180) / 360) * worldSize
  const latToY = (l: number) => {
    const r = (l * Math.PI) / 180
    return ((1 - Math.log(Math.tan(r) + 1 / Math.cos(r)) / Math.PI) / 2) * worldSize
  }
  const cx = lonToX(centerLon)
  const cy = latToY(centerLat)

  const tileSize = 256
  const tilesX = Math.ceil(width / tileSize) + 2
  const tilesY = Math.ceil(height / tileSize) + 2

  const centerTile = latLonToTile(centerLat, centerLon, zoom)
  const offsetX = cx - centerTile.x * tileSize - width / 2
  const offsetY = cy - centerTile.y * tileSize - height / 2

  const tiles: { tx: number; ty: number; key: string }[] = []
  const maxTile = Math.pow(2, zoom)
  for (let dy = -Math.ceil(tilesY / 2); dy <= Math.ceil(tilesY / 2); dy++) {
    for (let dx = -Math.ceil(tilesX / 2); dx <= Math.ceil(tilesX / 2); dx++) {
      const tx = ((centerTile.x + dx) % maxTile + maxTile) % maxTile
      const ty = centerTile.y + dy
      if (ty < 0 || ty >= maxTile) continue
      tiles.push({ tx, ty, key: `${dx},${dy}` })
    }
  }

  return (
    <div style={{ position: 'absolute', inset: 0, overflow: 'hidden', background: '#a8c8f0' }}>
      {tiles.map(({ tx, ty, key }) => {
        const [dx, dy] = key.split(',').map(Number)
        const left = (centerTile.x + dx) * tileSize - cx + width / 2
        const top = (centerTile.y + dy) * tileSize - cy + height / 2
        // Use OpenStreetMap tiles (free, no key needed)
        const src = `https://tile.openstreetmap.org/${zoom}/${tx}/${ty}.png`
        return (
          <img
            key={`${zoom}-${tx}-${ty}`}
            src={src}
            alt=""
            draggable={false}
            style={{
              position: 'absolute',
              left, top,
              width: tileSize, height: tileSize,
              imageRendering: 'pixelated',
            }}
          />
        )
      })}
    </div>
  )
}

// ─── Draggable Legend (single group) ─────────────────────────────────────────
const LEGEND_ITEMS = [
  { id: 'low',        color: '#22c55e',              label: 'Low (0–39)',    shape: 'circle' as const, category: 'Risk Score' },
  { id: 'medium',     color: '#f59e0b',              label: 'Medium (40–69)', shape: 'circle' as const, category: 'Risk Score' },
  { id: 'high',       color: '#ef4444',              label: 'High (70–100)', shape: 'circle' as const, category: 'Risk Score' },
  { id: 'restricted', color: 'rgba(239,68,68,0.8)',  label: 'Restricted',   shape: 'square' as const, category: 'War State' },
  { id: 'high-risk',  color: 'rgba(249,115,22,0.8)', label: 'High Risk',    shape: 'square' as const, category: 'War State' },
  { id: 'caution',    color: 'rgba(234,179,8,0.8)',  label: 'Caution',      shape: 'square' as const, category: 'War State' },
]

function DraggableLegend() {
  const [pos, setPos] = useState({ x: 16, y: 0 })
  const [dragging, setDragging] = useState(false)
  const offset = useRef({ x: 0, y: 0 })
  const ref = useRef<HTMLDivElement>(null)

  // Set initial Y after mount so we know window height
  useEffect(() => {
    setPos({ x: 16, y: window.innerHeight - 320 })
  }, [])

  const onMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    setDragging(true)
    offset.current = { x: e.clientX - pos.x, y: e.clientY - pos.y }
  }, [pos])

  useEffect(() => {
    if (!dragging) return
    const onMove = (e: MouseEvent) => setPos({ x: e.clientX - offset.current.x, y: e.clientY - offset.current.y })
    const onUp = () => setDragging(false)
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
    return () => { window.removeEventListener('mousemove', onMove); window.removeEventListener('mouseup', onUp) }
  }, [dragging])

  const onTouchStart = useCallback((e: React.TouchEvent) => {
    const t = e.touches[0]
    setDragging(true)
    offset.current = { x: t.clientX - pos.x, y: t.clientY - pos.y }
  }, [pos])

  useEffect(() => {
    if (!dragging) return
    const onMove = (e: TouchEvent) => {
      const t = e.touches[0]
      setPos({ x: t.clientX - offset.current.x, y: t.clientY - offset.current.y })
    }
    const onEnd = () => setDragging(false)
    window.addEventListener('touchmove', onMove, { passive: false })
    window.addEventListener('touchend', onEnd)
    return () => { window.removeEventListener('touchmove', onMove); window.removeEventListener('touchend', onEnd) }
  }, [dragging])

  return (
    <div
      ref={ref}
      style={{ position: 'absolute', left: pos.x, top: pos.y, zIndex: dragging ? 50 : 20, userSelect: 'none' }}
      className={`bg-white/95 backdrop-blur border rounded-xl shadow-2xl overflow-hidden transition-shadow ${
        dragging ? 'border-blue-400 shadow-blue-200 cursor-grabbing' : 'border-gray-200 cursor-default'
      }`}
    >
      {/* Drag handle header */}
      <div
        onMouseDown={onMouseDown}
        onTouchStart={onTouchStart}
        className="flex items-center gap-2 px-3 py-2 bg-gray-50 border-b border-gray-200 cursor-grab active:cursor-grabbing select-none"
      >
        <GripHorizontal size={14} className="text-gray-400" />
        <span className="text-gray-700 text-xs font-semibold tracking-wide uppercase">Legend</span>
      </div>

      {/* Items */}
      <div className="px-3 py-2 space-y-1 min-w-[160px]">
        <p className="text-gray-400 text-[10px] uppercase tracking-widest font-medium mt-1 mb-1.5">Risk Score</p>
        {LEGEND_ITEMS.filter(i => i.category === 'Risk Score').map(item => (
          <div key={item.id} className="flex items-center gap-2.5 py-0.5">
            <div
              className={item.shape === 'circle' ? 'w-3 h-3 rounded-full shrink-0 shadow-sm' : 'w-3 h-3 rounded-sm shrink-0 shadow-sm'}
              style={{ backgroundColor: item.color, border: '1.5px solid rgba(0,0,0,0.15)' }}
            />
            <span className="text-gray-700 text-xs">{item.label}</span>
          </div>
        ))}

        <div className="border-t border-gray-100 my-2" />
        <p className="text-gray-400 text-[10px] uppercase tracking-widest font-medium mb-1.5">War State</p>
        {LEGEND_ITEMS.filter(i => i.category === 'War State').map(item => (
          <div key={item.id} className="flex items-center gap-2.5 py-0.5">
            <div
              className="w-3 h-3 rounded-sm shrink-0 shadow-sm"
              style={{ backgroundColor: item.color, border: '1.5px solid rgba(0,0,0,0.15)' }}
            />
            <span className="text-gray-700 text-xs">{item.label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── Shipment popup ───────────────────────────────────────────────────────────
function ShipmentPopupCard({ shipment, onClose, onNavigate }: {
  shipment: Shipment; onClose: () => void; onNavigate: () => void
}) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-2xl w-64">
      <div className="flex items-start justify-between mb-3">
        <div>
          <p className="text-gray-900 font-semibold text-sm font-mono">{shipment.shipment_id.slice(0, 8).toUpperCase()}</p>
          <p className="text-gray-500 text-xs mt-0.5">{shipment.origin.name} → {shipment.destination.name}</p>
        </div>
        <button onClick={onClose} className="text-gray-400 hover:text-gray-600 p-1"><X size={14} /></button>
      </div>
      <div className="space-y-1.5 mb-3">
        {[
          { label: 'Risk Score', value: <RiskBadge score={shipment.risk_score} size="sm" /> },
          { label: 'Status', value: <span className="text-gray-800 text-xs">{shipment.status.replace(/_/g, ' ')}</span> },
          { label: 'Priority', value: <span className="text-gray-800 text-xs">{shipment.demand_priority}</span> },
        ].map(({ label, value }) => (
          <div key={label} className="flex justify-between items-center text-xs">
            <span className="text-gray-500">{label}</span>
            {value}
          </div>
        ))}
      </div>
      <button onClick={onNavigate} className="w-full bg-blue-600 hover:bg-blue-700 text-white text-xs font-medium py-1.5 rounded-lg transition-colors">
        View Details
      </button>
    </div>
  )
}

// ─── Shipment panel ───────────────────────────────────────────────────────────
function ShipmentPanel({ shipments, onSelect, onClose }: {
  shipments: Shipment[]; onSelect: (s: Shipment) => void; onClose: () => void
}) {
  const navigate = useNavigate()
  return (
    <div className="bg-white border border-gray-200 rounded-xl shadow-2xl w-72 max-h-[70vh] flex flex-col">
      <div className="flex items-center justify-between p-4 border-b border-gray-100">
        <p className="text-gray-900 font-semibold text-sm">Shipments ({shipments.length})</p>
        <button onClick={onClose} className="text-gray-400 hover:text-gray-600"><X size={16} /></button>
      </div>
      <div className="overflow-y-auto flex-1 p-2 space-y-1">
        {shipments.map((s) => (
          <button key={s.shipment_id} onClick={() => onSelect(s)}
            className="w-full text-left p-3 rounded-lg hover:bg-gray-50 transition-colors">
            <div className="flex items-center justify-between mb-1">
              <span className="text-gray-800 text-xs font-mono">{s.shipment_id.slice(0, 8)}</span>
              <RiskBadge score={s.risk_score} size="sm" />
            </div>
            <p className="text-gray-500 text-xs truncate">{s.origin.name} → {s.destination.name}</p>
          </button>
        ))}
      </div>
      <div className="p-3 border-t border-gray-100">
        <button onClick={() => navigate('/shipments')} className="w-full text-xs text-blue-600 hover:text-blue-700 font-medium py-1.5">
          View All Shipments →
        </button>
      </div>
    </div>
  )
}

// ─── Filter panel ─────────────────────────────────────────────────────────────
function MapFilters({ riskMin, riskMax, onRiskMinChange, onRiskMaxChange, onReset }: {
  riskMin: number; riskMax: number
  onRiskMinChange: (v: number) => void; onRiskMaxChange: (v: number) => void; onReset: () => void
}) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-2xl w-64">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Filter size={14} className="text-blue-600" />
          <p className="text-gray-900 font-semibold text-sm">Filters</p>
        </div>
        <button onClick={onReset} className="text-blue-600 text-xs hover:underline">Reset</button>
      </div>
      <div>
        <label className="text-gray-500 text-xs mb-2 block">Risk Score: {riskMin} – {riskMax}</label>
        <div className="space-y-2">
          <input type="range" min={0} max={100} value={riskMin} onChange={(e) => onRiskMinChange(Number(e.target.value))} className="w-full accent-blue-600" />
          <input type="range" min={0} max={100} value={riskMax} onChange={(e) => onRiskMaxChange(Number(e.target.value))} className="w-full accent-blue-600" />
        </div>
      </div>
    </div>
  )
}

// ─── Main Map Page ─────────────────────────────────────────────────────────────
export default function MapPage() {
  const navigate = useNavigate()
  const mapRef = useRef<HTMLDivElement>(null)
  const [mapSize, setMapSize] = useState({ width: 1200, height: 700 })
  const [centerLat, setCenterLat] = useState(20)
  const [centerLon, setCenterLon] = useState(10)
  const [zoom, setZoom] = useState(2)
  const [riskMin, setRiskMin] = useState(0)
  const [riskMax, setRiskMax] = useState(100)
  const [showFilters, setShowFilters] = useState(false)
  const [showPanel, setShowPanel] = useState(false)
  const [selectedShipment, setSelectedShipment] = useState<Shipment | null>(null)

  // Pan state
  const panning = useRef(false)
  const panStart = useRef({ x: 0, y: 0, lat: 20, lon: 10 })

  useEffect(() => {
    const update = () => {
      if (mapRef.current) {
        setMapSize({ width: mapRef.current.offsetWidth, height: mapRef.current.offsetHeight })
      }
    }
    update()
    window.addEventListener('resize', update)
    return () => window.removeEventListener('resize', update)
  }, [])

  // Zoom helpers
  const zoomIn = () => setZoom(z => Math.min(z + 1, 18))
  const zoomOut = () => setZoom(z => Math.max(z - 1, 1))
  const resetView = () => { setCenterLat(20); setCenterLon(10); setZoom(2) }

  // Mouse wheel zoom
  const onWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault()
    if (e.deltaY < 0) setZoom(z => Math.min(z + 1, 18))
    else setZoom(z => Math.max(z - 1, 1))
  }, [])

  // Pan handlers
  const onMouseDown = useCallback((e: React.MouseEvent) => {
    if ((e.target as HTMLElement).closest('[data-no-pan]')) return
    panning.current = true
    panStart.current = { x: e.clientX, y: e.clientY, lat: centerLat, lon: centerLon }
  }, [centerLat, centerLon])

  const onMouseMove = useCallback((e: React.MouseEvent) => {
    if (!panning.current) return
    const scale = Math.pow(2, zoom)
    const worldSize = 256 * scale
    const dx = e.clientX - panStart.current.x
    const dy = e.clientY - panStart.current.y
    const dLon = -(dx / worldSize) * 360
    const dLat = (dy / worldSize) * 180
    setCenterLon(panStart.current.lon + dLon)
    setCenterLat(Math.max(-85, Math.min(85, panStart.current.lat + dLat)))
  }, [zoom])

  const onMouseUp = useCallback(() => { panning.current = false }, [])

  const { data: shipmentsData } = useQuery({
    queryKey: ['shipments', { page: 1, page_size: 500 }],
    queryFn: () => getShipments({ page: 1, page_size: 500 }),
    refetchInterval: 30_000,
  })

  const { data: regions } = useQuery({
    queryKey: ['regions'],
    queryFn: getRegions,
    refetchInterval: 60_000,
  })

  const shipments = shipmentsData?.items || []
  const filteredShipments = shipments.filter(s => s.risk_score >= riskMin && s.risk_score <= riskMax)
  const highRisk = filteredShipments.filter(s => s.risk_score >= 70).length
  const medRisk = filteredShipments.filter(s => s.risk_score >= 40 && s.risk_score < 70).length
  const lowRisk = filteredShipments.filter(s => s.risk_score < 40).length

  const getRiskColor = (score: number) => score >= 70 ? '#ef4444' : score >= 40 ? '#f59e0b' : '#22c55e'

  // Stable positions for shipments (avoid random re-render)
  const shipmentPositions = useRef<Map<string, { lat: number; lon: number }>>(new Map())
  shipments.forEach(s => {
    if (!shipmentPositions.current.has(s.shipment_id)) {
      const lat = s.origin?.latitude ?? (Math.random() * 120 - 20)
      const lon = s.origin?.longitude ?? (Math.random() * 300 - 150)
      shipmentPositions.current.set(s.shipment_id, { lat, lon })
    }
  })

  return (
    <div className="relative h-[calc(100vh-3.5rem)] -m-6 overflow-hidden">
      {/* Map container */}
      <div
        ref={mapRef}
        className="absolute inset-0"
        style={{ cursor: panning.current ? 'grabbing' : 'grab' }}
        onWheel={onWheel}
        onMouseDown={onMouseDown}
        onMouseMove={onMouseMove}
        onMouseUp={onMouseUp}
        onMouseLeave={onMouseUp}
      >
        {/* OSM tile layer */}
        <TileMap
          centerLat={centerLat} centerLon={centerLon}
          zoom={zoom} width={mapSize.width} height={mapSize.height}
        />

        {/* Shipment dots */}
        <div className="absolute inset-0 pointer-events-none">
          {filteredShipments.map(s => {
            const pos = shipmentPositions.current.get(s.shipment_id)
            if (!pos) return null
            const { x, y } = latLonToPixel(pos.lat, pos.lon, centerLat, centerLon, zoom, mapSize.width, mapSize.height)
            if (x < -20 || x > mapSize.width + 20 || y < -20 || y > mapSize.height + 20) return null
            const color = getRiskColor(s.risk_score)
            return (
              <button
                key={s.shipment_id}
                data-no-pan
                onClick={() => setSelectedShipment(s)}
                className="absolute pointer-events-auto"
                style={{ left: x, top: y, transform: 'translate(-50%,-50%)', zIndex: 10 }}
                title={`${s.origin.name} → ${s.destination.name} | Risk: ${s.risk_score.toFixed(1)}`}
              >
                <div
                  className="rounded-full border-2 border-white shadow-lg hover:scale-150 transition-transform"
                  style={{ width: 14, height: 14, backgroundColor: color, boxShadow: `0 0 6px ${color}88` }}
                />
              </button>
            )
          })}
        </div>
      </div>

      {/* Top-left: stats bar */}
      <div className="absolute top-4 left-4 z-30" data-no-pan>
        <div className="bg-white/95 backdrop-blur border border-gray-200 rounded-xl px-4 py-2 shadow-lg">
          <div className="flex items-center gap-4 text-sm">
            <span className="text-gray-600">Total: <span className="text-gray-900 font-bold">{filteredShipments.length}</span></span>
            <span className="text-red-500">High: <span className="font-bold">{highRisk}</span></span>
            <span className="text-amber-500">Med: <span className="font-bold">{medRisk}</span></span>
            <span className="text-green-500">Low: <span className="font-bold">{lowRisk}</span></span>
          </div>
        </div>
      </div>

      {/* Top-right: controls */}
      <div className="absolute top-4 right-4 z-30 flex flex-col gap-2 items-end" data-no-pan>
        <div className="flex gap-2">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`flex items-center gap-2 px-3 py-2 rounded-xl border shadow-lg text-sm font-medium transition-colors ${
              showFilters ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-gray-700 border-gray-200 hover:bg-gray-50'
            }`}
          >
            <Filter size={14} /> Filters
          </button>
          <button
            onClick={() => setShowPanel(!showPanel)}
            className={`flex items-center gap-2 px-3 py-2 rounded-xl border shadow-lg text-sm font-medium transition-colors ${
              showPanel ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-gray-700 border-gray-200 hover:bg-gray-50'
            }`}
          >
            <Layers size={14} /> Shipments
          </button>
        </div>
        {showFilters && (
          <MapFilters riskMin={riskMin} riskMax={riskMax}
            onRiskMinChange={setRiskMin} onRiskMaxChange={setRiskMax}
            onReset={() => { setRiskMin(0); setRiskMax(100) }} />
        )}
        {showPanel && (
          <ShipmentPanel
            shipments={filteredShipments}
            onSelect={(s) => { setSelectedShipment(s); setShowPanel(false) }}
            onClose={() => setShowPanel(false)}
          />
        )}
      </div>

      {/* Zoom controls */}
      <div className="absolute right-4 bottom-24 z-30 flex flex-col gap-1" data-no-pan>
        <button onClick={zoomIn} className="w-9 h-9 bg-white border border-gray-200 rounded-lg shadow-lg flex items-center justify-center text-gray-700 hover:bg-gray-50 transition-colors font-bold">
          <Plus size={16} />
        </button>
        <div className="w-9 text-center text-xs text-gray-500 font-mono py-1 bg-white/80 rounded border border-gray-100">{zoom}</div>
        <button onClick={zoomOut} className="w-9 h-9 bg-white border border-gray-200 rounded-lg shadow-lg flex items-center justify-center text-gray-700 hover:bg-gray-50 transition-colors">
          <Minus size={16} />
        </button>
        <button onClick={resetView} className="w-9 h-9 bg-white border border-gray-200 rounded-lg shadow-lg flex items-center justify-center text-gray-700 hover:bg-gray-50 transition-colors mt-1" title="Reset view">
          <Locate size={14} />
        </button>
      </div>

      {/* Draggable legend group */}
      <DraggableLegend />

      {/* Selected shipment popup */}
      {selectedShipment && (
        <div className="absolute bottom-4 right-4 z-30" data-no-pan>
          <ShipmentPopupCard
            shipment={selectedShipment}
            onClose={() => setSelectedShipment(null)}
            onNavigate={() => navigate(`/shipments/${selectedShipment.shipment_id}`)}
          />
        </div>
      )}

      {/* OSM attribution */}
      <div className="absolute bottom-1 right-1 z-30 text-[10px] text-gray-500 bg-white/80 px-1.5 py-0.5 rounded">
        © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer" className="underline">OpenStreetMap</a> contributors
      </div>
    </div>
  )
}
