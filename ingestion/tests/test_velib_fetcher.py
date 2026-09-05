"""Tests du VelibFetcher : parsing, aplatissement et pagination.

On ne touche ni au réseau ni à la base : httpx est intercepté par respx,
psycopg2 n'est jamais appelé dans ces tests (on teste uniquement les
méthodes qui ne font pas d'I/O base).
"""

import httpx
import pytest
import respx

from velib_ingestion.config import settings
from velib_ingestion.fetchers.velib_fetcher import VelibFetcher

# ---------------------------------------------------------------------------
# _flatten
# ---------------------------------------------------------------------------


def test_flatten_extrait_lon_lat(velib_record):
    """coordonnees_geo imbriqué doit être aplati en lon/lat au niveau racine."""
    flat = VelibFetcher._flatten(dict(velib_record))

    assert flat["lon"] == 2.275725
    assert flat["lat"] == 48.865983
    assert "coordonnees_geo" not in flat


def test_flatten_supprime_station_opening_hours(velib_record):
    """station_opening_hours est systématiquement null et inutile en base."""
    flat = VelibFetcher._flatten(dict(velib_record))

    assert "station_opening_hours" not in flat


def test_flatten_coordonnees_absentes_donne_none(velib_record):
    """Une station sans coordonnées géographiques ne doit pas lever d'exception."""
    record = dict(velib_record)
    record["coordonnees_geo"] = None

    flat = VelibFetcher._flatten(record)

    assert flat["lon"] is None
    assert flat["lat"] is None


def test_flatten_coordonnees_manquantes_donne_none(velib_record):
    """Si la clé coordonnees_geo est absente, lon/lat doivent valoir None."""
    record = dict(velib_record)
    del record["coordonnees_geo"]

    flat = VelibFetcher._flatten(record)

    assert flat["lon"] is None
    assert flat["lat"] is None


def test_flatten_conserve_les_autres_champs(velib_record):
    """L'aplatissement ne doit pas supprimer les champs métier."""
    flat = VelibFetcher._flatten(dict(velib_record))

    assert flat["stationcode"] == "16107"
    assert flat["capacity"] == 35
    assert flat["is_renting"] == "OUI"


# ---------------------------------------------------------------------------
# _fetch_all_stations (pagination)
# ---------------------------------------------------------------------------


@respx.mock
def test_pagination_recupere_toutes_les_stations(velib_record):
    """La boucle doit s'arrêter quand offset >= total_count."""
    page_1 = {"total_count": 3, "results": [velib_record, velib_record]}
    page_2 = {"total_count": 3, "results": [velib_record]}

    respx.get(settings.velib_api_base_url).mock(
        side_effect=[
            httpx.Response(200, json=page_1),
            httpx.Response(200, json=page_2),
        ]
    )

    stations = VelibFetcher()._fetch_all_stations()

    assert len(stations) == 3


@respx.mock
def test_pagination_sarrete_sur_page_vide(velib_record):
    """Une page sans résultats interrompt la boucle même si total_count > offset."""
    respx.get(settings.velib_api_base_url).mock(
        side_effect=[
            httpx.Response(200, json={"total_count": 99, "results": [velib_record]}),
            httpx.Response(200, json={"total_count": 99, "results": []}),
        ]
    )

    stations = VelibFetcher()._fetch_all_stations()

    assert len(stations) == 1


@respx.mock
def test_pagination_propage_erreur_http():
    """Une erreur HTTP doit remonter pour que l'orchestrateur voie l'échec."""
    respx.get(settings.velib_api_base_url).mock(return_value=httpx.Response(503))

    with pytest.raises(httpx.HTTPStatusError):
        VelibFetcher()._fetch_all_stations()


@respx.mock
def test_pagination_une_seule_page(velib_record):
    """Quand total_count == len(results), une seule requête suffit."""
    respx.get(settings.velib_api_base_url).mock(
        return_value=httpx.Response(
            200, json={"total_count": 1, "results": [velib_record]}
        )
    )

    stations = VelibFetcher()._fetch_all_stations()

    assert len(stations) == 1
    # Une seule requête envoyée
    assert respx.calls.call_count == 1


# ---------------------------------------------------------------------------
# _insert_stations (cas limites sans base)
# ---------------------------------------------------------------------------


def test_insert_stations_liste_vide_retourne_zero():
    """Aucune requête ne doit être envoyée pour une liste vide."""
    result = VelibFetcher._insert_stations([])

    assert result == 0
