import re
from pathlib import Path

import rasterio
from rasterio.warp import transform_bounds

from app.config import settings

# Expected filename pattern: <product>_<date>_<tile>.tif
_FILENAME_RE = re.compile(
    r"^(?P<product>[a-z][a-z0-9_]*)_(?P<date>\d{8})_(?P<tile>[a-z0-9_]+)\.tif$"
)


def _cog_bounds_wgs84(path: Path) -> list[float]:
    with rasterio.open(path) as src:
        bounds = transform_bounds(src.crs, "EPSG:4326", *src.bounds)
    return list(bounds)  # [west, south, east, north]


def list_layers() -> dict:
    data_dir = settings.data_dir
    features = []

    if not data_dir.exists():
        return {"type": "FeatureCollection", "features": features}

    for tif in sorted(data_dir.glob("*.tif")):
        m = _FILENAME_RE.match(tif.name)
        if not m:
            continue

        product = m.group("product")
        date = m.group("date")
        tile = m.group("tile")
        layer_id = tif.stem  # filename without .tif

        try:
            west, south, east, north = _cog_bounds_wgs84(tif)
        except Exception:
            continue

        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [west, south],
                            [east, south],
                            [east, north],
                            [west, north],
                            [west, south],
                        ]
                    ],
                },
                "properties": {
                    "id": layer_id,
                    "product": product,
                    "date": date,
                    "tile": tile,
                    "bounds": [west, south, east, north],
                },
            }
        )

    return {"type": "FeatureCollection", "features": features}
