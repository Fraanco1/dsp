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


def file_for_product_date(product: str, date: str) -> Path | None:
    """Return the .tif for a specific product + date, or None."""
    data_dir = settings.data_dir
    if not data_dir.exists():
        return None
    matches = [
        f for f in data_dir.glob(f"{product}_{date}_*.tif")
        if _FILENAME_RE.match(f.name)
    ]
    return matches[0] if matches else None


def list_layers() -> dict:
    data_dir = settings.data_dir
    if not data_dir.exists():
        return {"type": "FeatureCollection", "features": []}

    # Collect all dates per product
    all_dates: dict[str, list[str]] = {}
    latest: dict[str, tuple[str, Path]] = {}

    for tif in data_dir.glob("*.tif"):
        m = _FILENAME_RE.match(tif.name)
        if not m:
            continue
        product, date = m.group("product"), m.group("date")
        all_dates.setdefault(product, [])
        if date not in all_dates[product]:
            all_dates[product].append(date)
        if product not in latest or date > latest[product][0]:
            latest[product] = (date, tif)

    features = []
    for product in sorted(all_dates):
        date, tif = latest[product]
        try:
            west, south, east, north = _cog_bounds_wgs84(tif)
        except Exception:
            continue

        dates_sorted = sorted(all_dates[product], reverse=True)

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
                    "date": date,           # most recent — backward compat
                    "dates": dates_sorted,  # all available dates, newest first
                    "bounds": [west, south, east, north],
                },
            }
        )

    return {"type": "FeatureCollection", "features": features}
