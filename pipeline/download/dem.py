"""Download Copernicus DEM GLO-30 tiles via NASA Earthdata (earthaccess)."""

from pathlib import Path
import earthaccess
from config import DATA_RAW, EARTHDATA_USERNAME, EARTHDATA_PASSWORD


def download_dem(
    bbox: tuple[float, float, float, float],
    dest: Path | None = None,
) -> list[Path]:
    """
    Download Copernicus DEM GLO-30 tiles covering bbox.

    Used for terrain correction in the SAR preprocessing chain.

    Args:
        bbox: (min_lon, min_lat, max_lon, max_lat)
        dest: destination directory (default: data/raw/dem)

    Returns:
        List of downloaded tile paths.
    """
    dest = dest or DATA_RAW / "dem"
    dest.mkdir(parents=True, exist_ok=True)

    if EARTHDATA_USERNAME and EARTHDATA_PASSWORD:
        earthaccess.login(strategy="environment")
    else:
        earthaccess.login()  # interactive / .netrc fallback

    min_lon, min_lat, max_lon, max_lat = bbox
    results = earthaccess.search_data(
        short_name="COP-DEM_GLO-30-DGED",
        bounding_box=(min_lon, min_lat, max_lon, max_lat),
    )

    if not results:
        raise RuntimeError(f"No Copernicus DEM GLO-30 tiles found for bbox {bbox}")

    print(f"Found {len(results)} DEM tile(s). Downloading to {dest} ...")
    files = earthaccess.download(results, local_path=str(dest))
    paths = [Path(f) for f in files]
    print(f"Downloaded: {[p.name for p in paths]}")
    return paths
