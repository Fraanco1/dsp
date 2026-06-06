from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import layers, tiles

app = FastAPI(
    title="Satellite Soil Analysis — Tile Server",
    description="Serves Cloud-Optimized GeoTIFF tiles and layer metadata.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(tiles.router)
app.include_router(layers.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
