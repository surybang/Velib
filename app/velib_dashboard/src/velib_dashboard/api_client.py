"""Client HTTP vers l'API FastAPI.

Streamlit n'interroge jamais la base directement. Toutes les données passent
par ce module. Si l'API est injoignable, les fonctions renvoient des valeurs
vides plutôt que de faire planter le dashboard.
"""

import os
from typing import Any

import httpx

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")
API_V1 = f"{API_BASE}/v1"
TIMEOUT = 10.0


def _get(path: str, params: dict | None = None) -> Any:
    try:
        r = httpx.get(f"{API_V1}{path}", params=params, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def get_status() -> dict:
    return _get("/status") or {}


def get_city_stats() -> dict:
    return _get("/city/stats") or {}


def get_by_commune() -> list[dict]:
    return _get("/city/by_commune") or []


def get_map_data() -> list[dict]:
    return _get("/map") or []


def get_stations() -> list[dict]:
    return _get("/stations") or []


def get_station_current(stationcode: str) -> dict:
    return _get(f"/stations/{stationcode}/current") or {}


def get_station_history(stationcode: str, hours: int = 24) -> list[dict]:
    return _get(f"/stations/{stationcode}/history", {"hours": hours}) or []
