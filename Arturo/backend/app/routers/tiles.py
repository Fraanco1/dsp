import rasterio
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse, Response
from rasterio.errors import RasterioIOError
from rasterio.warp import transform_bounds
from rio_tiler.colormap import cmap as _cmap
from rio_tiler.errors import TileOutsideBounds
from rio_tiler.io import COGReader

from app.services.catalog import file_for_product_date, latest_file_for_product
from app.services.colormaps import PRODUCT_RANGE, get_colormap

router = APIRouter()


@router.get(
    "/tiles/{layer}/tilejson.json",
    summary="TileJSON 2.2 metadata for a layer",
)
def get_tilejson(
    layer: str,
    request: Request,
    date: str | None = Query(default=None, description="Date YYYYMMDD"),
) -> JSONResponse:
    tif_path = file_for_product_date(layer, date) if date else latest_file_for_product(layer)
    if tif_path is None:
        detail = f"Layer '{layer}' not found for date {date}" if date else f"Layer '{layer}' not found"
        raise HTTPException(status_code=404, detail=detail)

    try:
        with COGReader(str(tif_path)) as cog:
            minzoom = cog.minzoom
            maxzoom = cog.maxzoom
        with rasterio.open(str(tif_path)) as src:
            bounds = list(transform_bounds(src.crs, "EPSG:4326", *src.bounds))
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
def get_tile(
    layer: str,
    z: int,
    x: int,
    y: int,
    date: str | None = Query(default=None, description="Date YYYYMMDD — defaults to latest"),
    rescale: str | None = Query(default=None, description="min,max for linear stretch"),
    colormap_name: str | None = Query(default=None, description="Colormap name"),
) -> Response:
    tif_path = file_for_product_date(layer, date) if date else latest_file_for_product(layer)
    if tif_path is None:
        detail = f"Layer '{layer}' not found for date {date}" if date else f"Layer '{layer}' not found"
        raise HTTPException(status_code=404, detail=detail)

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
        # Determine rescale range: request param → product default → skip
        if rescale:
            try:
                vmin, vmax = map(float, rescale.split(","))
            except Exception:
                vmin, vmax = None, None
        else:
            default = PRODUCT_RANGE.get(layer)
            vmin, vmax = default if default else (None, None)

        if vmin is not None and vmax is not None:
            img.rescale(in_range=((vmin, vmax),))

        if colormap_name:
            try:
                colormap = _cmap.get(colormap_name)
            except Exception:
                colormap = get_colormap(layer)
        else:
            colormap = get_colormap(layer)

        png_bytes = img.render(img_format="PNG", colormap=colormap, add_mask=True)
    else:
        png_bytes = img.render(img_format="PNG", add_mask=True)

    return Response(content=png_bytes, media_type="image/png")
