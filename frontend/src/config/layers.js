// Static metadata for every product the pipeline can produce.
// Merged at runtime with live data from GET /layers (which adds dates, tile_id, bbox).
export const LAYER_META = {
  soil_moisture: {
    label: 'Soil Moisture',
    unit: 'm³/m³',
    color: '#3b82f6',
    min: 0,
    max: 0.5,
    colormap: 'blues',
    description: 'Volumetric water content — Water Cloud Model estimate from SAOCOM L-band σ⁰',
  },
  soil_cluster: {
    label: 'Soil Composition',
    unit: 'cluster',
    color: '#a855f7',
    min: 0,
    max: 5,
    colormap: 'tab10',
    categorical: true,
    description: 'K-means clusters on fused SAR + optical features (soil type proxy)',
  },
  ndvi: {
    label: 'Vegetation (NDVI)',
    unit: 'index',
    color: '#22c55e',
    min: -1,
    max: 1,
    colormap: 'rdylgn',
    description: 'Normalized Difference Vegetation Index — (NIR−Red)/(NIR+Red)',
  },
  ndmi: {
    label: 'Veg. Water Content',
    unit: 'NDMI',
    color: '#10b981',
    min: -1,
    max: 1,
    colormap: 'rdylgn',
    description: 'Normalized Difference Moisture Index — (NIR−SWIR1)/(NIR+SWIR1)',
  },
  ndwi: {
    label: 'Open Water',
    unit: 'NDWI',
    color: '#06b6d4',
    min: -1,
    max: 1,
    colormap: 'blues',
    description: 'Normalized Difference Water Index — (Green−NIR)/(Green+NIR)',
  },
  bsi: {
    label: 'Bare Soil Index',
    unit: 'BSI',
    color: '#f59e0b',
    min: -1,
    max: 1,
    colormap: 'ylorrd',
    description: 'Bare Soil Index — ((SWIR1+Red)−(NIR+Blue)) / ((SWIR1+Red)+(NIR+Blue))',
  },
  backscatter_hh: {
    label: 'SAR Backscatter HH',
    unit: 'dB',
    color: '#94a3b8',
    min: -25,
    max: -5,
    colormap: 'greys',
    description: 'SAOCOM L-band σ⁰ HH polarization — terrain-corrected backscatter',
  },
}

// Display order in the layer panel
export const LAYER_ORDER = [
  'soil_moisture',
  'soil_cluster',
  'ndvi',
  'ndmi',
  'ndwi',
  'bsi',
  'backscatter_hh',
]
