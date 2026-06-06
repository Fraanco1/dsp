from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.services.catalog import list_layers

router = APIRouter()


@router.get("/layers", summary="List available raster layers")
def get_layers() -> JSONResponse:
    return JSONResponse(content=list_layers())
