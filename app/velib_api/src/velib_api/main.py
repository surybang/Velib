"""API Vélib' — point d'entrée FastAPI.

Toutes les routes métier sont préfixées par /v1. Une évolution incompatible du
contrat se fera sous /v2 sans casser les clients existants.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from velib_api.routers import city, health, map, stations

API_V1 = "/v1"

app = FastAPI(
    title="Vélib' API",
    description="Données Vélib' + météo pour le dashboard",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # à restreindre à l'URL Streamlit en prod
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix=API_V1)
app.include_router(map.router, prefix=API_V1)
app.include_router(city.router, prefix=API_V1)
app.include_router(stations.router, prefix=API_V1)


@app.get("/")
def root():
    return {"service": "velib-api", "docs": "/docs", "version": "v1"}
