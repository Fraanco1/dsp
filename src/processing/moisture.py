"""
Build a soil-moisture proxy map from SAR data (SAOCOM or Sentinel-1).

For SAOCOM L2 Soil Moisture products the output is used directly.
For L1 GRD (SAOCOM or Sentinel-1), raw amplitude is converted to
backscatter coefficient sigma0 (dB). Lower sigma0 generally indicates
drier soil; wetter soil yields higher backscatter in L- and C-band.
"""

from pathlib import Path
import numpy as np
import rasterio
from rasterio.merge import merge
from rasterio.mask import mask
from shapely.geometry import box, mapping

from config import DATA_RAW, DATA_OUTPUT


def _amplitude_to_db(amplitude: np.ndarray) -> np.ndarray:
    """Convert SAR amplitude to backscatter in dB (sigma0)."""
    with np.errstate(divide="ignore", invalid="ignore"):
        db = 20 * np.log10(amplitude.astype(np.float32))
        db[~np.isfinite(db)] = np.nan
    return db


def _find_sar_files(saocom_dir: Path, s1_dir: Path) -> list[Path]:
    """Return SAR GeoTIFF files, preferring SAOCOM over Sentinel-1."""
    files = sorted(saocom_dir.glob("**/*.tif")) + sorted(saocom_dir.glob("**/*.TIF"))
    if not files:
        files = sorted(s1_dir.glob("**/*.tif")) + sorted(s1_dir.glob("**/*.TIF"))
    return files


def build_moisture(
    bbox: tuple[float, float, float, float],
    saocom_dir: Path | None = None,
    s1_dir: Path | None = None,
    output: Path | None = None,
) -> Path:
    """
    Build a moisture proxy GeoTIFF from SAR backscatter.

    SAOCOM scenes are preferred (L-band, ~25 cm wavelength — better soil
    penetration); Sentinel-1 is used as fallback (C-band).

    Args:
        bbox: (min_lon, min_lat, max_lon, max_lat)
        saocom_dir: directory with SAOCOM GeoTIFFs
        s1_dir: directory with Sentinel-1 GeoTIFFs
        output: output GeoTIFF path

    Returns:
        Path to the moisture proxy GeoTIFF.
    """
    saocom_dir = saocom_dir or DATA_RAW / "saocom"
    s1_dir = s1_dir or DATA_RAW / "sentinel1"
    output = output or DATA_OUTPUT / "moisture.tif"
    output.parent.mkdir(parents=True, exist_ok=True)

    sar_files = _find_sar_files(saocom_dir, s1_dir)
    if not sar_files:
        raise FileNotFoundError(
            f"No SAR GeoTIFF files found in {saocom_dir} or {s1_dir}. "
            "Run the download step first."
        )

    source = "SAOCOM" if list(saocom_dir.glob("**/*.tif")) else "Sentinel-1"
    print(f"Using {source} data ({len(sar_files)} file(s)) ...")

    aoi_geom = [mapping(box(*bbox))]
    datasets = [rasterio.open(p) for p in sar_files]
    mosaic, mosaic_transform = merge(datasets)
    src_crs = datasets[0].crs
    src_dtype = datasets[0].dtypes[0]
    for ds in datasets:
        ds.close()

    with rasterio.MemoryFile() as memfile:
        meta = {
            "driver": "GTiff",
            "height": mosaic.shape[1],
            "width": mosaic.shape[2],
            "count": mosaic.shape[0],
            "dtype": src_dtype,
            "crs": src_crs,
            "transform": mosaic_transform,
        }
        with memfile.open(**meta) as tmp:
            tmp.write(mosaic)
            clipped, clipped_transform = mask(tmp, aoi_geom, crop=True, nodata=0)

    # Convert to dB if the data appears to be raw amplitude (uint16 / float > 1)
    band = clipped[0].astype(np.float32)
    if band.max() > 2.0:
        band = _amplitude_to_db(band)

    out_meta = {
        "driver": "GTiff",
        "height": band.shape[0],
        "width": band.shape[1],
        "count": 1,
        "dtype": "float32",
        "crs": src_crs,
        "transform": clipped_transform,
        "nodata": np.nan,
    }
    with rasterio.open(output, "w", **out_meta) as dst:
        dst.write(band, 1)

    print(f"Moisture proxy (backscatter dB) saved to {output}")
    return output
