import React from 'react'
import './Legend.css'

const GRADIENTS = {
  blues:  'linear-gradient(to right, #f7fbff, #084594)',
  rdylgn: 'linear-gradient(to right, #d73027, #fee08b, #1a9850)',
  ylorrd: 'linear-gradient(to right, #ffffb2, #fd8d3c, #bd0026)',
  greys:  'linear-gradient(to right, #f7f7f7, #252525)',
  tab10:  'linear-gradient(to right, #1f77b4, #ff7f0e, #2ca02c, #d62728, #9467bd, #8c564b)',
}

export default function Legend({ layer }) {
  if (!layer) return null

  const gradient = GRADIENTS[layer.colormap] ?? GRADIENTS.blues

  if (layer.categorical) {
    const labels = Array.from({ length: layer.max - layer.min + 1 }, (_, i) => `Type ${i + 1}`)
    return (
      <div className="legend">
        <span className="legend-title">{layer.label}</span>
        <div className="legend-categorical">
          {labels.map((l, i) => (
            <span key={i} className="legend-cat-item">
              <span className="legend-cat-dot" style={{ background: GRADIENTS.tab10 }} />
              {l}
            </span>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="legend">
      <span className="legend-title">{layer.label}</span>
      <div className="legend-bar" style={{ background: gradient }} />
      <div className="legend-ticks">
        <span>{layer.min}</span>
        <span>{layer.unit}</span>
        <span>{layer.max}</span>
      </div>
    </div>
  )
}
