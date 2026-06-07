from rio_tiler.colormap import cmap as _cmap

_PRODUCT_COLORMAP: dict[str, str] = {
    "soil_moisture": "blues",
    "bsi": "ylorbn",
    "ndmi": "rdylgn",
    "ndvi": "rdylgn",
    "vegetation_water": "rdylgn",
    "sar_texture": "greys",
}

_DEFAULT = "viridis"


def get_colormap(product: str) -> dict:
    name = _PRODUCT_COLORMAP.get(product, _DEFAULT)
    return _cmap.get(name)
