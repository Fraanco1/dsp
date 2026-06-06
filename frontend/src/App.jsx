import React, { useState } from 'react'
import MapView from './components/MapView'
import LayerPanel from './components/LayerPanel'
import Header from './components/Header'
import './App.css'

const LAYERS = [
  { id: 'soil_moisture', label: 'Soil Moisture', unit: 'm³/m³', color: '#3b82f6' },
  { id: 'bsi',           label: 'Bare Soil Index', unit: 'BSI', color: '#f59e0b' },
  { id: 'ndmi',          label: 'Veg. Water Content', unit: 'NDMI', color: '#10b981' },
  { id: 'ndvi',          label: 'Vegetation (NDVI)', unit: 'NDVI', color: '#22c55e' },
]

export default function App() {
  const [activeLayer, setActiveLayer] = useState(LAYERS[0].id)

  return (
    <div className="app">
      <Header />
      <div className="workspace">
        <LayerPanel layers={LAYERS} activeLayer={activeLayer} onSelect={setActiveLayer} />
        <MapView activeLayer={activeLayer} />
      </div>
    </div>
  )
}
