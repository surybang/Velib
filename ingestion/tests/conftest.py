"""Fixtures partagées entre les tests.

Les variables d'environnement sont posées AVANT l'import de config.py,
qui les valide au chargement du module. Sans ça, pydantic-settings lèverait
une ValidationError dès l'import.
"""

import os

import pytest

# Variables obligatoires sans défaut dans Settings
os.environ.setdefault("PGHOST", "localhost")
os.environ.setdefault("PGPORT", "5432")
os.environ.setdefault("PGDATABASE", "velib_test")
os.environ.setdefault("PGUSER", "test")
os.environ.setdefault("PGPASSWORD", "test")
os.environ.setdefault("VELIB_API_BASE_URL", "https://opendata.test/velib")
os.environ.setdefault("METEO_API_BASE_URL", "https://api.test/meteo")


@pytest.fixture
def velib_record() -> dict:
    """Un enregistrement brut tel que renvoyé par l'API Open Data Paris.

    Contient toutes les clés réelles de l'API, y compris coordonnees_geo
    imbriqué et station_opening_hours null, pour tester l'aplatissement.
    """
    return {
        "stationcode": "16107",
        "name": "Benjamin Godard - Victor Hugo",
        "is_installed": "OUI",
        "capacity": 35,
        "numdocksavailable": 21,
        "numbikesavailable": 13,
        "mechanical": 10,
        "ebike": 3,
        "is_renting": "OUI",
        "is_returning": "OUI",
        "duedate": "2026-07-01T09:54:55+02:00",
        "coordonnees_geo": {"lon": 2.275725, "lat": 48.865983},
        "nom_arrondissement_communes": "Paris",
        "code_insee_commune": "75056",
        "station_opening_hours": None,
    }


@pytest.fixture
def meteo_payload() -> dict:
    """Payload complet renvoyé par l'API Open-Meteo.

    L'horodatage est naïf (pas de suffixe fuseau) comme le renvoie l'API
    avec le paramètre timezone=Europe/Paris. C'est la subtilité principale
    à tester : on doit lui attacher le fuseau explicitement.
    """
    return {
        "current": {
            "time": "2026-07-02T21:45",  # naïf, heure de Paris
            "interval": 900,  # métadonnée à retirer
            "temperature_2m": 22.4,
            "relative_humidity_2m": 55,
            "apparent_temperature": 21.7,
            "is_day": 1,
            "precipitation": 0.0,
            "rain": 0.0,
            "showers": 0.0,
            "snowfall": 0.0,
            "cloud_cover": 50,
            "wind_speed_10m": 11.2,
        }
    }
