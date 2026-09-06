"""Métriques agrégées à l'échelle de la ville."""

from fastapi import APIRouter

from velib_api.db import query

router = APIRouter(prefix="/city", tags=["city"])

_LATEST_CTE = """
    WITH latest AS (
        SELECT DISTINCT ON (stationcode)
            stationcode, commune, bikes_available, docks_available
            , occupancy_rate, is_empty, is_full
            , temperature_2m, precipitation
        FROM gold.fct_velib_meteo
        ORDER BY stationcode, duedate DESC
    )
"""


@router.get("/stats")
def city_stats():
    """Vélos, places, occupation moyenne, ruptures, météo sur le dernier snapshot."""
    return query(
        _LATEST_CTE
        + """
        SELECT
            count(*)                                  AS total_stations
            , sum(bikes_available)                    AS total_velos
            , sum(docks_available)                    AS total_places
            , round(avg(occupancy_rate)::numeric, 1)  AS occupation_moyenne
            , count(*) FILTER (WHERE is_empty)        AS stations_vides
            , count(*) FILTER (WHERE is_full)         AS stations_pleines
            , round(avg(temperature_2m)::numeric, 1)  AS temperature
            , round(sum(precipitation)::numeric, 1)   AS precipitation
        FROM latest
    """
    )[0]


@router.get("/by_commune")
def stats_by_commune():
    """Occupation et ruptures par commune, sur le dernier snapshot."""
    return query(
        _LATEST_CTE
        + """
        SELECT
            commune
            , count(*)                                AS nb_stations
            , sum(bikes_available)                    AS total_velos
            , round(avg(occupancy_rate)::numeric, 1)  AS occupation_moyenne
            , count(*) FILTER (WHERE is_empty)        AS stations_vides
        FROM latest
        GROUP BY commune
        ORDER BY occupation_moyenne DESC
    """
    )
