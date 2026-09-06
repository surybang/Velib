"""Détail et historique d'une station."""

from fastapi import APIRouter, HTTPException, Query

from velib_api.db import query

router = APIRouter(prefix="/stations", tags=["stations"])


@router.get("")
def list_stations():
    """Liste des stations pour le sélecteur du dashboard."""
    return query("""
        SELECT DISTINCT stationcode, station_name, commune
        FROM gold.fct_velib_meteo
        ORDER BY station_name
    """)


@router.get("/{stationcode}/current")
def station_current(stationcode: str):
    """Dernier snapshot d'une station."""
    rows = query(
        """
        SELECT DISTINCT ON (stationcode)
            stationcode, station_name, commune, lat, lon
            , capacity, bikes_available, docks_available
            , mechanical, ebike, occupancy_rate
            , is_empty, is_full
            , temperature_2m, precipitation, wind_speed_10m
            , duedate AT TIME ZONE 'Europe/Paris' AS duedate_paris
        FROM gold.fct_velib_meteo
        WHERE stationcode = %s
        ORDER BY stationcode, duedate DESC
    """,
        (stationcode,),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Station introuvable")
    return rows[0]


@router.get("/{stationcode}/history")
def station_history(stationcode: str, hours: int = Query(default=24, ge=1, le=168)):
    """Historique d'une station sur les N dernières heures (max 7 jours)."""
    rows = query(
        """
        SELECT
            duedate AT TIME ZONE 'Europe/Paris' AS ts
            , bikes_available
            , docks_available
            , occupancy_rate
            , temperature_2m
            , precipitation
            , is_day
        FROM gold.fct_velib_meteo
        WHERE stationcode = %s
          AND duedate >= now() - make_interval(hours => %s)
        ORDER BY duedate
    """,
        (stationcode, hours),
    )
    if not rows:
        raise HTTPException(
            status_code=404, detail="Aucune donnée pour cette station sur cette période"
        )
    return rows
