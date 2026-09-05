"""Tests du MeteoFetcher : parsing du payload et gestion du fuseau horaire.

Le fuseau est la subtilité centrale : l'API renvoie un horodatage naïf en
heure de Paris. Sans attachement explicite du fuseau, psycopg2 le stockerait
comme UTC, décalant la mesure de 2h en été. Ces tests vérifient que ce n'est
pas le cas.
"""

from datetime import UTC

import httpx
import pytest
import respx

from velib_ingestion.config import settings
from velib_ingestion.fetchers.meteo_fetcher import MeteoFetcher

# ---------------------------------------------------------------------------
# _fetch_current_weather
# ---------------------------------------------------------------------------


@respx.mock
def test_attache_le_fuseau_paris(meteo_payload):
    """L'horodatage naïf de l'API doit recevoir le fuseau Europe/Paris."""
    respx.get(settings.meteo_api_base_url).mock(
        return_value=httpx.Response(200, json=meteo_payload)
    )

    weather = MeteoFetcher._fetch_current_weather()

    # Le fuseau doit être attaché
    assert weather["time"].tzinfo is not None
    # En CEST (UTC+2), l'offset est de 7200 secondes
    assert weather["time"].utcoffset().total_seconds() == 7200


@respx.mock
def test_retire_interval(meteo_payload):
    """Le champ interval est une métadonnée API sans intérêt métier."""
    respx.get(settings.meteo_api_base_url).mock(
        return_value=httpx.Response(200, json=meteo_payload)
    )

    weather = MeteoFetcher._fetch_current_weather()

    assert "interval" not in weather


@respx.mock
def test_conserve_les_mesures(meteo_payload):
    """Toutes les mesures météo doivent être présentes après parsing."""
    respx.get(settings.meteo_api_base_url).mock(
        return_value=httpx.Response(200, json=meteo_payload)
    )

    weather = MeteoFetcher._fetch_current_weather()

    assert weather["temperature_2m"] == 22.4
    assert weather["relative_humidity_2m"] == 55
    assert weather["apparent_temperature"] == 21.7
    assert weather["is_day"] == 1
    assert weather["wind_speed_10m"] == 11.2


@respx.mock
def test_propage_erreur_http(meteo_payload):
    """Une erreur réseau doit remonter pour que l'orchestrateur voie l'échec."""
    respx.get(settings.meteo_api_base_url).mock(return_value=httpx.Response(503))

    with pytest.raises(httpx.HTTPStatusError):
        MeteoFetcher._fetch_current_weather()


@respx.mock
def test_horodatage_correct_en_utc(meteo_payload):
    """Vérifie la valeur UTC réelle : 21h45 Paris CEST = 19h45 UTC.

    C'est le test qui prouve concrètement que le décalage de 2h ne se produit
    pas, en comparant l'heure UTC attendue avec celle stockée.
    """
    respx.get(settings.meteo_api_base_url).mock(
        return_value=httpx.Response(200, json=meteo_payload)
    )

    weather = MeteoFetcher._fetch_current_weather()


    utc_time = weather["time"].astimezone(UTC)
    assert utc_time.hour == 19
    assert utc_time.minute == 45
