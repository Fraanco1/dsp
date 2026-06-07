from rio_tiler.colormap import cmap as _cmap

_PRODUCT_COLORMAP: dict[str, str] = {
    "soil_moisture":  "blues",
    "soil_cluster":   "tab10",
    "bsi":            "ylorrd",
    "ndmi":           "rdylgn",
    "ndvi":           "rdylgn",
    "ndwi":           "blues",
    "backscatter_hh": "greys",
    "sar_texture":    "greys",
}

_DEFAULT = "viridis"

# Fallback (vmin, vmax) used when the request doesn't include a rescale param.
# Matches LAYER_META min/max in the frontend's config/layers.js.
PRODUCT_RANGE: dict[str, tuple[float, float]] = {
    "soil_moisture":  (0.0,   0.5),
    "soil_cluster":   (0,     5),
    "bsi":            (-1.0,  1.0),
    "ndmi":           (-1.0,  1.0),
    "ndvi":           (-1.0,  1.0),
    "ndwi":           (-1.0,  1.0),
    "backscatter_hh": (-25.0, -5.0),
    "sar_texture":    (0.0,   1.0),
}


def get_colormap(product: str) -> dict:
    name = _PRODUCT_COLORMAP.get(product, _DEFAULT)
    return _cmap.get(name)
