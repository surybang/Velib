"""Fetcher météo : API Open-Meteo -> bronze.meteo_paris.

L'API renvoie un horodatage local sans suffixe de fuseau (paramètre
timezone=Europe/Paris dans l'URL). On attache donc explicitement le fuseau
avant insertion : sans cela, psycopg2 interpréterait la valeur naïve comme de
l'UTC et décalerait la mesure de deux heures en été.

Déduplication : contrainte uq_meteo_measured_at (measured_at).
"""

from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
from loguru import logger

from velib_ingestion.config import settings
from velib_ingestion.db import get_connection

PARIS_TZ = ZoneInfo("Europe/Paris")
HTTP_TIMEOUT_SECONDS = 30.0

_INSERT_SQL = """
    INSERT INTO bronze.meteo_paris (
        measured_at, temperature_2m, relative_humidity_2m, apparent_temperature,
        is_day, precipitation, rain, showers, snowfall, cloud_cover, wind_speed_10m
    ) VALUES (
        %(time)s, %(temperature_2m)s, %(relative_humidity_2m)s,
        %(apparent_temperature)s, %(is_day)s, %(precipitation)s, %(rain)s,
        %(showers)s, %(snowfall)s, %(cloud_cover)s, %(wind_speed_10m)s
    )
    ON CONFLICT ON CONSTRAINT uq_meteo_measured_at DO NOTHING
"""


class MeteoFetcher:
    """Collecte la mesure météo courante et l'insère en bronze."""

    def run(self) -> dict[str, int]:
        """Exécute une collecte.

        Returns:
            {"inserted": 1} si la mesure est nouvelle, {"inserted": 0} si elle
            était déjà présente (l'API renvoie la même mesure pendant 15 min).

        Raises:
            Toute exception réseau ou base est propagée.
        """
        logger.info("Démarrage de la collecte météo")
        weather = self._fetch_current_weather()

        inserted = self._insert_weather(weather)
        if inserted:
            logger.info("Météo insérée pour {}", weather["time"])
        else:
            logger.info("Météo déjà présente pour {}, ignorée", weather["time"])
        return {"inserted": inserted}

    @staticmethod
    def _fetch_current_weather() -> dict:
        """Appelle l'API et normalise le payload.

        L'horodatage reçu est naïf mais exprimé en heure de Paris : on lui
        attache le fuseau pour que la conversion vers UTC au stockage soit juste.
        Le champ interval est une métadonnée de l'API sans intérêt métier.
        """
        with httpx.Client(timeout=HTTP_TIMEOUT_SECONDS) as client:
            response = client.get(settings.meteo_api_base_url)
            response.raise_for_status()
            payload = response.json()

        current = dict(payload["current"])
        current.pop("interval", None)
        current["time"] = datetime.fromisoformat(current["time"]).replace(
            tzinfo=PARIS_TZ
        )
        return current

    @staticmethod
    def _insert_weather(weather: dict) -> int:
        """Insère la mesure, retourne 1 si insérée, 0 si doublon."""
        with get_connection() as conn, conn, conn.cursor() as cur:
            cur.execute(_INSERT_SQL, weather)
            return cur.rowcount
