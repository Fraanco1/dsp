"""
Generate synthetic Cloud-Optimized GeoTIFFs for all expected products.

Writes to data/processed/ following the pipeline contract:
    <product>_<date>_<tile>.tif

Run from repo root:
    python Arturo/scripts/generate_test_data.py
"""

from pathlib import Path
import numpy as np
import rasterio
from rasterio.transform import from_bounds
from rasterio.crs import CRS

# ── Config ──────────────────────────────────────────────────────────────────

BBOX = (-65.0, -38.0, -57.0, -30.0)  # Pampas (min_lon, min_lat, max_lon, max_lat)
RESOLUTION = 0.02                     # degrees per pixel (~2 km)
DATE = "20240315"
TILE = "pampa_aoi"
OUTPUT_DIR = Path(__file__).parents[2] / "data" / "processed"

# product -> (min_value, max_value, nodata)
PRODUCTS = {
    "soil_moisture":  (0.05, 0.45, np.nan),
    "ndvi":           (-0.1, 0.85, np.nan),
    "ndmi":           (-0.3, 0.6,  np.nan),
    "ndwi":           (-0.5, 0.3,  np.nan),
    "bsi":            (-0.4, 0.5,  np.nan),
    "backscatter_hh": (-22.0, -6.0, np.nan),
}

# ── Helpers ──────────────────────────────────────────────────────────────────

def _smooth(arr: np.ndarray, passes: int = 6) -> np.ndarray:
    """Simple box-filter smoothing — no scipy needed."""
    for _ in range(passes):
        arr = (
            arr
            + np.roll(arr, 1, 0) + np.roll(arr, -1, 0)
            + np.roll(arr, 1, 1) + np.roll(arr, -1, 1)
        ) / 5.0
    return arr


def _make_field(shape: tuple, vmin: float, vmax: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    raw = rng.random(shape).astype(np.float32)
    smooth = _smooth(raw).astype(np.float32)
    return smooth * (vmax - vmin) + vmin


def _add_nodata_border(arr: np.ndarray, width: int = 5) -> np.ndarray:
    """Blank out a border so transparency rendering is testable."""
    out = arr.copy()
    out[:width, :] = np.nan
    out[-width:, :] = np.nan
    out[:, :width] = np.nan
    out[:, -width:] = np.nan
    return out


def _write_cog(array: np.ndarray, path: Path, transform, crs) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    profile = {
        "driver": "GTiff",
        "dtype": "float32",
        "width": array.shape[1],
        "height": array.shape[0],
        "count": 1,
        "crs": crs,
        "transform": transform,
        "nodata": np.nan,
        "compress": "deflate",
        "tiled": True,
        "blockxsize": 256,
        "blockysize": 256,
    }
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(array[np.newaxis, :, :])
        dst.build_overviews([2, 4, 8], rasterio.enums.Resampling.average)
        dst.update_tags(ns="rio_overview", resampling="average")


def _write_categorical_cog(array: np.ndarray, path: Path, transform, crs) -> None:
    """For soil_cluster — integer clusters 0-5."""
    path.parent.mkdir(parents=True, exist_ok=True)
    profile = {
        "driver": "GTiff",
        "dtype": "uint8",
        "width": array.shape[1],
        "height": array.shape[0],
        "count": 1,
        "crs": crs,
        "transform": transform,
        "nodata": 255,
        "compress": "deflate",
        "tiled": True,
        "blockxsize": 256,
        "blockysize": 256,
    }
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(array[np.newaxis, :, :])
        dst.build_overviews([2, 4, 8], rasterio.enums.Resampling.nearest)
        dst.update_tags(ns="rio_overview", resampling="nearest")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    min_lon, min_lat, max_lon, max_lat = BBOX
    width  = int((max_lon - min_lon) / RESOLUTION)
    height = int((max_lat - min_lat) / RESOLUTION)
    transform = from_bounds(min_lon, min_lat, max_lon, max_lat, width, height)
    crs = CRS.from_epsg(4326)

    print(f"Grid: {width}×{height} pixels at {RESOLUTION}° resolution")
    print(f"Output: {OUTPUT_DIR}/\n")

    for i, (product, (vmin, vmax, _)) in enumerate(PRODUCTS.items()):
        field = _make_field((height, width), vmin, vmax, seed=i)
        field = _add_nodata_border(field)
        path = OUTPUT_DIR / f"{product}_{DATE}_{TILE}.tif"
        _write_cog(field, path, transform, crs)
        print(f"  {product:20s} → {path.name}")

    # soil_cluster: categorical (K-means label 0-5)
    rng = np.random.default_rng(99)
    raw = rng.integers(0, 6, size=(height, width), dtype=np.uint8)
    raw_smooth = np.round(_smooth(raw.astype(np.float32), passes=12)).astype(np.uint8)
    raw_smooth = np.clip(raw_smooth, 0, 5)
    cluster_path = OUTPUT_DIR / f"soil_cluster_{DATE}_{TILE}.tif"
    _write_categorical_cog(raw_smooth, cluster_path, transform, crs)
    print(f"  {'soil_cluster':20s} → {cluster_path.name}")

    print(f"\nDone. {len(PRODUCTS) + 1} COGs written.")


if __name__ == "__main__":
    main()
