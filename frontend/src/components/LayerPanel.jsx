import React from 'react'
import './LayerPanel.css'

export default function LayerPanel({ layers, activeId, onSelect, backendOnline }) {
  return (
    <aside className="layer-panel">
      <div className="panel-header">
        <p className="panel-title">Layers</p>
        <span className={`backend-badge ${backendOnline ? 'online' : 'offline'}`}>
          {backendOnline ? 'live' : 'no backend'}
        </span>
      </div>

      <ul>
        {layers.map(layer => (
          <li
            key={layer.id}
            className={`layer-item ${activeId === layer.id ? 'active' : ''} ${!layer.available ? 'unavailable' : ''}`}
            onClick={() => onSelect(layer.id)}
            title={layer.description}
          >
            <span className="layer-dot" style={{ background: layer.color }} />
            <div className="layer-info">
              <span className="layer-label">{layer.label}</span>
              <span className="layer-meta">
                {layer.date
                  ? <span className="layer-date">{layer.date}</span>
                  : <span className="layer-pending">pending</span>
                }
                <span className="layer-unit">{layer.unit}</span>
              </span>
            </div>
          </li>
        ))}
      </ul>

      <div className="panel-footer">
        <p>AOI: Argentine Pampas</p>
        <p>-65° – -57°W · -38° – -30°S</p>
      </div>
    </aside>
  )
}
