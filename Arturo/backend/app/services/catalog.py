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


def latest_file_for_product(product: str) -> Path | None:
    """Return the most recent .tif for a given product name, or None."""
    data_dir = settings.data_dir
    if not data_dir.exists():
        return None
    matches = sorted(
        (f for f in data_dir.glob(f"{product}_*.tif") if _FILENAME_RE.match(f.name)),
        key=lambda f: _FILENAME_RE.match(f.name).group("date"),
        reverse=True,
    )
    return matches[0] if matches else None


def list_layers() -> dict:
    data_dir = settings.data_dir
    if not data_dir.exists():
        return {"type": "FeatureCollection", "features": []}

    # Group by product name, keep only most recent date per product
    best: dict[str, tuple[str, Path]] = {}  # product -> (date, path)
    for tif in data_dir.glob("*.tif"):
        m = _FILENAME_RE.match(tif.name)
        if not m:
            continue
        product, date = m.group("product"), m.group("date")
        if product not in best or date > best[product][0]:
            best[product] = (date, tif)

    features = []
    for product, (date, tif) in sorted(best.items()):
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
                    "id": product,
                    "product": product,
                    "date": date,
                    "bounds": [west, south, east, north],
                },
            }
        )

    return {"type": "FeatureCollection", "features": features}
