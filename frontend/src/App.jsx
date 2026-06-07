import React, { useState } from 'react'
import MapView from './components/MapView'
import LayerPanel from './components/LayerPanel'
import Header from './components/Header'
import Legend from './components/Legend'
import { useLayers } from './hooks/useLayers'
import './App.css'

export default function App() {
  const { layers, loading, backendOnline } = useLayers()
  const [activeId, setActiveId] = useState('soil_moisture')

  const activeLayer = layers.find(l => l.id === activeId) ?? null

  if (loading) {
    return (
      <div className="app">
        <Header backendOnline={false} />
        <div className="loading">Loading layers…</div>
      </div>
    )
  }

  return (
    <div className="app">
      <Header backendOnline={backendOnline} />
      <div className="workspace">
        <LayerPanel
          layers={layers}
          activeId={activeId}
          onSelect={setActiveId}
          backendOnline={backendOnline}
        />
        <div className="map-area">
          <MapView activeLayer={activeLayer} />
          <Legend layer={activeLayer} />
        </div>
      </div>
    </div>
  )
}
