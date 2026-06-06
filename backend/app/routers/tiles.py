from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from rio_tiler.errors import TileOutsideBounds
from rio_tiler.io import COGReader

from app.config import settings

router = APIRouter()


@router.get(
    "/tiles/{layer}/{z}/{x}/{y}.png",
    summary="Serve a map tile for a given layer",
    responses={200: {"content": {"image/png": {}}}, 404: {}, 422: {}},
)
def get_tile(layer: str, z: int, x: int, y: int) -> Response:
    tif_path: Path = settings.data_dir / f"{layer}.tif"

    if not tif_path.exists():
        raise HTTPException(status_code=404, detail=f"Layer '{layer}' not found")

    try:
        with COGReader(str(tif_path)) as cog:
            img = cog.tile(x, y, z)
    except TileOutsideBounds:
        # Return transparent 256×256 PNG for tiles outside the dataset extent
        raise HTTPException(status_code=404, detail="Tile outside layer bounds")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    png_bytes = img.render(img_format="PNG")
    return Response(content=png_bytes, media_type="image/png")
