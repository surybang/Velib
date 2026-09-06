"""État actuel de toutes les stations, pour la carte."""

from fastapi import APIRouter

from velib_api.db import query

router = APIRouter(prefix="/map", tags=["map"])


@router.get("")
def get_map_data():
    """Snapshot le plus récent de chaque station avec position et occupation.

    Une ligne par station. L'état a jusqu'à ~15 min de retard (cache de l'API
    source), ce qui est la meilleure fraîcheur disponible.
    """
    return query("""
        SELECT DISTINCT ON (stationcode)
            stationcode
            , station_name
            , commune
            , lat
            , lon
            , capacity
            , bikes_available
            , docks_available
            , mechanical
            , ebike
            , occupancy_rate
            , is_empty
            , is_full
            , temperature_2m
            , precipitation
            , duedate AT TIME ZONE 'Europe/Paris' AS duedate_paris
        FROM gold.fct_velib_meteo
        ORDER BY stationcode, duedate DESC
    """)
