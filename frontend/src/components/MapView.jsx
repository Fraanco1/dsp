import React from 'react'
import { MapContainer, TileLayer, WMSTileLayer } from 'react-leaflet'
import './MapView.css'

// Argentine Pampas center
const CENTER = [-34.0, -61.0]
const ZOOM = 7

export default function MapView({ activeLayer }) {
  return (
    <div className="map-wrapper">
      <MapContainer center={CENTER} zoom={ZOOM} className="map">
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {/* Analytical overlay — served by Arturo's backend once ready */}
        {activeLayer && (
          <TileLayer
            key={activeLayer}
            url={`/tiles/${activeLayer}/{z}/{x}/{y}.png`}
            opacity={0.7}
          />
        )}
      </MapContainer>
    </div>
  )
}
