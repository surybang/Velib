"""Santé de l'API et fraîcheur du pipeline."""

from datetime import UTC, datetime

from fastapi import APIRouter

from velib_api.db import query

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.now(UTC).isoformat()}


@router.get("/status")
def pipeline_status():
    """Dernière collecte et nombre de stations, pour le bandeau du dashboard."""
    rows = query("""
        SELECT
            max(ingested_at) AT TIME ZONE 'Europe/Paris' AS derniere_ingestion
            , max(duedate)   AT TIME ZONE 'Europe/Paris' AS dernier_duedate
            , count(DISTINCT stationcode)                AS stations_actives
            , now()          AT TIME ZONE 'Europe/Paris' AS maintenant
        FROM gold.fct_velib_meteo
    """)
    return rows[0] if rows else {}
