"""Tests de la configuration pydantic-settings.

On vérifie que Settings valide correctement les variables d'environnement
et rejette les configurations incomplètes, sans toucher à l'environnement
réel (les variables de test sont posées dans conftest.py).
"""


def test_settings_page_size_defaut():
    """velib_api_page_size a un défaut à 100, pas besoin de le déclarer."""
    from velib_ingestion.config import settings

    assert settings.velib_api_page_size == 100
