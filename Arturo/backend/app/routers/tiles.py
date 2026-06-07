from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from rasterio.errors import RasterioIOError
from rio_tiler.errors import TileOutsideBounds
from rio_tiler.io import COGReader

from app.config import settings
from app.services.colormaps import get_colormap

router = APIRouter()


def _resolve(layer: str) -> Path:
    return settings.data_dir / f"{layer}.tif"


def _product_from_layer(layer: str) -> str:
    # layer id is <product>_<date>_<tile>
    return layer.split("_")[0]


@router.get(
    "/tiles/{layer}/tilejson.json",
    summary="TileJSON 2.2 metadata for a layer",
)
def get_tilejson(layer: str, request: Request) -> JSONResponse:
    tif_path = _resolve(layer)
    if not tif_path.exists():
        raise HTTPException(status_code=404, detail=f"Layer '{layer}' not found")

    try:
        with COGReader(str(tif_path)) as cog:
            bounds = list(cog.geographic_bounds)
            minzoom = cog.minzoom
            maxzoom = cog.maxzoom
    except RasterioIOError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid raster: {exc}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    west, south, east, north = bounds
    base = str(request.base_url).rstrip("/")
    return JSONResponse(
        {
            "tilejson": "2.2.0",
            "name": layer,
            "tiles": [f"{base}/tiles/{layer}/{{z}}/{{x}}/{{y}}.png"],
            "minzoom": minzoom,
            "maxzoom": maxzoom,
            "bounds": bounds,
            "center": [(west + east) / 2, (south + north) / 2, minzoom],
        }
    )


@router.get(
    "/tiles/{layer}/{z}/{x}/{y}.png",
    summary="Serve a map tile for a given layer",
    responses={200: {"content": {"image/png": {}}}, 404: {}, 422: {}},
)
def get_tile(layer: str, z: int, x: int, y: int) -> Response:
    tif_path = _resolve(layer)
    if not tif_path.exists():
        raise HTTPException(status_code=404, detail=f"Layer '{layer}' not found")

    try:
        with COGReader(str(tif_path)) as cog:
            img = cog.tile(x, y, z)
    except TileOutsideBounds:
        raise HTTPException(status_code=404, detail="Tile outside layer bounds")
    except RasterioIOError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid or corrupt raster: {exc}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    if img.count == 1:
        colormap = get_colormap(_product_from_layer(layer))
        png_bytes = img.render(img_format="PNG", colormap=colormap)
    else:
        png_bytes = img.render(img_format="PNG")

    return Response(content=png_bytes, media_type="image/png")
