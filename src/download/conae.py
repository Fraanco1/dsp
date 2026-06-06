"""Download SAOCOM SAR data from CONAE STAC catalog."""

from pathlib import Path
import requests
from config import DATA_RAW, CONAE_USER, CONAE_PASSWORD, CONAE_STAC_URL


def _stac_search(bbox: tuple, date_start: str, date_end: str, collection: str) -> list[dict]:
    """Query CONAE STAC catalog and return a list of items."""
    url = f"{CONAE_STAC_URL}/search"
    min_lon, min_lat, max_lon, max_lat = bbox
    payload = {
        "collections": [collection],
        "bbox": [min_lon, min_lat, max_lon, max_lat],
        "datetime": f"{date_start}/{date_end}",
        "limit": 50,
    }
    auth = (CONAE_USER, CONAE_PASSWORD) if CONAE_USER else None
    resp = requests.post(url, json=payload, auth=auth, timeout=30)
    resp.raise_for_status()
    return resp.json().get("features", [])


def _download_asset(asset_url: str, dest_path: Path, auth: tuple | None) -> Path:
    resp = requests.get(asset_url, auth=auth, stream=True, timeout=120)
    resp.raise_for_status()
    with open(dest_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=1 << 20):
            f.write(chunk)
    return dest_path


def download_saocom(
    bbox: tuple[float, float, float, float],
    date_start: str,
    date_end: str,
    product_type: str = "SAOCOM_L1B_GRD",
    dest: Path | None = None,
) -> list[Path]:
    """
    Search and download SAOCOM scenes from CONAE catalog.

    Args:
        bbox: (min_lon, min_lat, max_lon, max_lat)
        date_start: ISO date string e.g. "2024-01-01"
        date_end: ISO date string e.g. "2024-02-01"
        product_type: STAC collection name (SAOCOM_L1B_GRD or SAOCOM_L2_SM)
        dest: destination directory

    Returns:
        List of downloaded file paths.
    """
    dest = dest or DATA_RAW / "saocom"
    dest.mkdir(parents=True, exist_ok=True)

    auth = (CONAE_USER, CONAE_PASSWORD) if CONAE_USER else None

    print(f"Searching CONAE catalog for {product_type} ...")
    items = _stac_search(bbox, date_start, date_end, collection=product_type)

    if not items:
        print(f"No SAOCOM scenes found for bbox {bbox} between {date_start} and {date_end}.")
        return []

    print(f"Found {len(items)} scene(s). Downloading ...")
    paths: list[Path] = []
    for item in items:
        scene_id = item["id"]
        assets = item.get("assets", {})
        # Prefer the 'data' asset; fall back to the first available asset
        asset = assets.get("data") or next(iter(assets.values()), None)
        if asset is None:
            print(f"  Skipping {scene_id}: no downloadable asset found")
            continue

        href = asset["href"]
        filename = Path(href).name or f"{scene_id}.zip"
        dest_path = dest / filename

        if dest_path.exists():
            print(f"  Already exists: {filename}")
            paths.append(dest_path)
            continue

        print(f"  Downloading {filename} ...")
        _download_asset(href, dest_path, auth)
        paths.append(dest_path)

    return paths
