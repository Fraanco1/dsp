"""Compute slope (degrees) from a DEM GeoTIFF using GDAL."""

import subprocess
from pathlib import Path
from config import DATA_OUTPUT


def build_slope(
    terrain_path: Path | None = None,
    output: Path | None = None,
) -> Path:
    """
    Run gdaldem slope on a DEM and save slope.tif (values in degrees).

    Args:
        terrain_path: input DEM GeoTIFF (default: data/output/terrain.tif)
        output: output slope GeoTIFF path

    Returns:
        Path to the slope GeoTIFF.
    """
    terrain_path = terrain_path or DATA_OUTPUT / "terrain.tif"
    output = output or DATA_OUTPUT / "slope.tif"
    output.parent.mkdir(parents=True, exist_ok=True)

    if not terrain_path.exists():
        raise FileNotFoundError(f"Terrain file not found: {terrain_path}")

    cmd = [
        "gdaldem", "slope",
        str(terrain_path),
        str(output),
        "-of", "GTiff",
        "-b", "1",
        "-s", "111120",  # scale: degrees -> meters at equator approx
    ]

    print(f"Computing slope from {terrain_path.name} ...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"gdaldem slope failed:\n{result.stderr}")

    print(f"Slope map saved to {output}")
    return output
