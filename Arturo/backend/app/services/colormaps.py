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


def get_colormap(product: str) -> dict:
    name = _PRODUCT_COLORMAP.get(product, _DEFAULT)
    return _cmap.get(name)
