"""Entrypoint : une collecte météo, puis sortie."""

from velib_ingestion.entrypoints._runner import run_task
from velib_ingestion.fetchers.meteo_fetcher import MeteoFetcher


def main() -> None:
    """Collecte météo : une exécution, puis sortie."""
    run_task("ingest-meteo", MeteoFetcher().run)


if __name__ == "__main__":
    main()
