import { useState, useEffect } from 'react'
import { LAYER_META, LAYER_ORDER } from '../config/layers'

// Merges live /layers API response with static metadata.
// Falls back gracefully to static-only list when backend is unavailable.
export function useLayers() {
  const [layers, setLayers] = useState([])
  const [loading, setLoading] = useState(true)
  const [backendOnline, setBackendOnline] = useState(false)

  useEffect(() => {
    fetch('/layers')
      .then(r => {
        if (!r.ok) throw new Error(`/layers returned ${r.status}`)
        return r.json()
      })
      .then(geojson => {
        const features = geojson.features ?? []
        // Group by product id, keep most recent date per product
        const byId = {}
        for (const f of features) {
          const p = f.properties
          if (!byId[p.id] || p.date > byId[p.id].date) {
            byId[p.id] = { ...p, bbox: f.bbox }
          }
        }
        const merged = LAYER_ORDER
          .filter(id => LAYER_META[id])
          .map(id => ({
            ...LAYER_META[id],
            id,
            available: Boolean(byId[id]),
            ...(byId[id] ?? {}),
          }))
        setLayers(merged)
        setBackendOnline(true)
      })
      .catch(() => {
        // Backend not yet running — show all layers as "pending"
        const fallback = LAYER_ORDER
          .filter(id => LAYER_META[id])
          .map(id => ({ ...LAYER_META[id], id, available: false }))
        setLayers(fallback)
        setBackendOnline(false)
      })
      .finally(() => setLoading(false))
  }, [])

  return { layers, loading, backendOnline }
}
