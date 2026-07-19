"""Fetcher Vélib : API Open Data Paris -> bronze.velib_stations.

Flux : API Open Data Paris -> pagination -> aplatissement geo -> PostgreSQL bronze

La pagination boucle jusqu'à total_count (~995 stations pour Paris).
Le tri (capacity DESC, stationcode ASC) garantit un ordre stable entre les pages,
capacity seule produisant des ex aequo qui feraient rater des enregistrements.

Note sur la fraîcheur : l'endpoint paginé Opendatasoft est servi depuis un cache
rafraîchi toutes les ~15 min, contrairement aux requêtes ciblées par stationcode.
Le champ duedate peut donc accuser un retard allant jusqu'à ce délai. La colonne
ingested_at, posée par la base, reste l'horloge fiable du pipeline.

Déduplication : contrainte uq_velib_station_update (stationcode, duedate).
"""

import time

import httpx
import psycopg2.extras
from loguru import logger

from velib_ingestion.config import settings
from velib_ingestion.db import get_connection

INTER_PAGE_DELAY_SECONDS = 0.2  # politesse envers l'API publique
HTTP_TIMEOUT_SECONDS = 30.0

_INSERT_SQL = """
    INSERT INTO bronze.velib_stations (
        stationcode, name, is_installed, capacity,
        numdocksavailable, numbikesavailable, mechanical, ebike,
        is_renting, is_returning, duedate, lon, lat,
        nom_arrondissement_communes, code_insee_commune
    ) VALUES %s
    ON CONFLICT ON CONSTRAINT uq_velib_station_update DO NOTHING
"""

_INSERT_TEMPLATE = (
    "(%(stationcode)s, %(name)s, %(is_installed)s, %(capacity)s,"
    " %(numdocksavailable)s, %(numbikesavailable)s, %(mechanical)s, %(ebike)s,"
    " %(is_renting)s, %(is_returning)s, %(duedate)s, %(lon)s, %(lat)s,"
    " %(nom_arrondissement_communes)s, %(code_insee_commune)s)"
)


class VelibFetcher:
    """Collecte un snapshot complet des stations Vélib' et l'insère en bronze."""

    def run(self) -> dict[str, int]:
        """Exécute une collecte complète.

        Returns:
            Un résumé {"fetched": n, "inserted": n} exploitable par
            l'orchestrateur (XCom) et par les tests.

        Raises:
            Toute exception réseau ou base est propagée : l'appelant doit
            échouer visiblement plutôt que de perdre des données en silence.
        """
        logger.info("Démarrage de la collecte Vélib")
        stations = self._fetch_all_stations()
        logger.info("{} stations récupérées, insertion en base", len(stations))

        inserted = self._insert_stations(stations)
        logger.info(
            "{} nouvelles lignes insérées dans bronze.velib_stations "
            "({} doublons ignorés)",
            inserted,
            len(stations) - inserted,
        )
        return {"fetched": len(stations), "inserted": inserted}

    def _fetch_all_stations(self) -> list[dict]:
        """Pagine l'API jusqu'à avoir récupéré tous les enregistrements."""
        stations: list[dict] = []
        offset = 0

        with httpx.Client(timeout=HTTP_TIMEOUT_SECONDS) as client:
            while True:
                params = {
                    "order_by": "capacity DESC, stationcode ASC",
                    "limit": settings.velib_api_page_size,
                    "offset": offset,
                    "refine": 'nom_arrondissement_communes:"Paris"',
                    "timezone": "Europe/Paris",
                }
                response = client.get(settings.velib_api_base_url, params=params)
                response.raise_for_status()
                payload = response.json()

                results: list[dict] = payload.get("results", [])
                if not results:
                    break

                stations.extend(self._flatten(record) for record in results)

                offset += len(results)
                total: int = payload.get("total_count", 0)
                logger.debug("Page offset={}/{} récupérée", offset, total)

                if offset >= total:
                    break

                time.sleep(INTER_PAGE_DELAY_SECONDS)

        return stations

    @staticmethod
    def _flatten(record: dict) -> dict:
        """Aplatit les coordonnées imbriquées et retire les champs inutilisés.

        L'API renvoie coordonnees_geo comme objet imbriqué, ce qui ne se mappe
        pas directement sur le schéma bronze. station_opening_hours est
        systématiquement null dans les données observées.
        """
        geo = record.pop("coordonnees_geo", None) or {}
        record["lon"] = geo.get("lon")
        record["lat"] = geo.get("lat")
        record.pop("station_opening_hours", None)
        return record

    @staticmethod
    def _insert_stations(stations: list[dict]) -> int:
        """Insère les stations en un seul aller-retour, retourne le nombre inséré.

        execute_values regroupe les valeurs en une requête unique, là où un
        execute par ligne produisait ~995 allers-retours réseau.
        """
        if not stations:
            return 0

        with get_connection() as conn, conn, conn.cursor() as cur:
            psycopg2.extras.execute_values(
                cur, _INSERT_SQL, stations, template=_INSERT_TEMPLATE, page_size=500
            )
            return cur.rowcount
