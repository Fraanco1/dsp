import React, { useEffect, useRef } from 'react'
import { MapContainer, TileLayer, useMap } from 'react-leaflet'
import './MapView.css'

// Argentine Pampas center and bbox
const CENTER = [-34.0, -61.0]
const ZOOM   = 7
const BOUNDS = [[-38, -65], [-30, -57]]

function buildTileUrl(layer) {
  // Use the full stem (layerId) so the backend can resolve the .tif file.
  // Colormap and rescaling are handled server-side — no query params needed.
  const stem = layer.layerId ?? layer.id
  return `/tiles/${stem}/{z}/{x}/{y}.png`
}

// Swaps the analytical overlay when activeLayer changes without remounting the map
function OverlayLayer({ layer }) {
  const map = useMap()
  const overlayRef = useRef(null)

  useEffect(() => {
    if (!layer?.available) {
      overlayRef.current?.remove()
      overlayRef.current = null
      return
    }

    const L = window.L ?? globalThis.L
    if (!L) return

    overlayRef.current?.remove()
    const url = buildTileUrl(layer)
    overlayRef.current = L.tileLayer(url, { opacity: 0.75, zIndex: 400 }).addTo(map)

    return () => {
      overlayRef.current?.remove()
      overlayRef.current = null
    }
  }, [layer, map])

  return null
}

export default function MapView({ activeLayer }) {
  return (
    <div className="map-wrapper">
      <MapContainer
        center={CENTER}
        zoom={ZOOM}
        maxBounds={BOUNDS}
        maxBoundsViscosity={0.5}
        className="map"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          zIndex={100}
        />
        <OverlayLayer layer={activeLayer} />
      </MapContainer>

      {activeLayer && !activeLayer.available && (
        <div className="map-overlay-notice">
          {activeLayer.label} — waiting for backend
        </div>
      )}
    </div>
  )
}
