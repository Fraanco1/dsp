"""
Unsupervised soil composition clustering.

Fuses SAR (σ⁰ HH, σ⁰ HV) and optical (NDVI, BSI, NDMI) features into a
K-means cluster map. Each cluster captures a distinct soil/land-cover type
(e.g. dry bare soil, moist cropland, dense forest).
"""

from pathlib import Path
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import reproject
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.impute import SimpleImputer

from pipeline.processing.export import save_cog


def _load_band(path: Path) -> tuple[np.ndarray, dict]:
    with rasterio.open(path) as src:
        arr = src.read(1).astype(np.float32)
        arr[arr == src.nodata] = np.nan
        meta = src.meta.copy()
    return arr, meta


def _resample_to(source: np.ndarray, src_meta: dict, ref_meta: dict) -> np.ndarray:
    """Reproject source to the grid defined by ref_meta."""
    dest = np.full((ref_meta["height"], ref_meta["width"]), np.nan, dtype=np.float32)
    reproject(
        source=source,
        destination=dest,
        src_transform=src_meta["transform"],
        src_crs=src_meta["crs"],
        dst_transform=ref_meta["transform"],
        dst_crs=ref_meta["crs"],
        resampling=Resampling.bilinear,
        src_nodata=np.nan,
        dst_nodata=np.nan,
    )
    return dest


def build_clusters(
    feature_paths: dict[str, Path],
    acquisition_date: str,
    tile_id: str = "aoi",
    n_clusters: int = 6,
    output_dir: Path | None = None,
    reference_layer: str = "backscatter_hh",
) -> Path:
    """
    Run K-means clustering on fused SAR + optical features.

    Args:
        feature_paths: dict mapping feature name to COG path.
            Expected keys: "backscatter_hh", "backscatter_hv", "ndvi", "bsi", "ndmi"
            (any subset is accepted — missing layers are skipped)
        acquisition_date: ISO date string for output filename
        tile_id: tile identifier for filename
        n_clusters: number of K-means clusters (default 6)
        output_dir: output directory (default: data/processed)
        reference_layer: which layer defines the output grid (highest-res SAR layer)

    Returns:
        Path to the cluster-label COG (uint8, values 0 … n_clusters-1).
    """
    from config import DATA_PROCESSED
    output_dir = output_dir or DATA_PROCESSED
    output_dir.mkdir(parents=True, exist_ok=True)

    date_tag = acquisition_date.replace("-", "")
    out_path = output_dir / f"soil_cluster_{date_tag}_{tile_id}.tif"

    print(f"Building soil cluster map ({n_clusters} clusters) ...")

    ref_arr, ref_meta = _load_band(feature_paths[reference_layer])
    h, w = ref_arr.shape

    stack = []
    layer_names = []
    for name, path in feature_paths.items():
        if not path.exists():
            print(f"  Skipping missing layer: {name}")
            continue
        arr, meta = _load_band(path)
        if arr.shape != (h, w):
            arr = _resample_to(arr, meta, ref_meta)
        stack.append(arr.ravel())
        layer_names.append(name)

    print(f"  Feature layers: {layer_names}")

    X = np.stack(stack, axis=1)  # (n_pixels, n_features)

    # Impute NaN with column mean before clustering
    imputer = SimpleImputer(strategy="mean")
    X_imputed = imputer.fit_transform(X)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_imputed)

    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init="auto")
    labels = kmeans.fit_predict(X_scaled).astype(np.uint8)
    labels_img = labels.reshape(h, w)

    # Mark pixels where all features were NaN as 255 (nodata)
    all_nan = np.all(~np.isfinite(X), axis=1).reshape(h, w)
    labels_img[all_nan] = 255

    out_meta = ref_meta.copy()
    out_meta.update(count=1, dtype="uint8", nodata=255)
    save_cog(labels_img[np.newaxis, :, :], out_path, out_meta)
    print(f"  Cluster map → {out_path.name}")
    return out_path
