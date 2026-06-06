import React from 'react'
import './LayerPanel.css'

export default function LayerPanel({ layers, activeLayer, onSelect }) {
  return (
    <aside className="layer-panel">
      <p className="panel-title">Layers</p>
      <ul>
        {layers.map(layer => (
          <li
            key={layer.id}
            className={`layer-item ${activeLayer === layer.id ? 'active' : ''}`}
            onClick={() => onSelect(layer.id)}
          >
            <span className="layer-dot" style={{ background: layer.color }} />
            <span className="layer-label">{layer.label}</span>
            <span className="layer-unit">{layer.unit}</span>
          </li>
        ))}
      </ul>
    </aside>
  )
}
