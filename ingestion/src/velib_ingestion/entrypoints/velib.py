"""Entrypoint : une collecte Vélib', puis sortie."""

from velib_ingestion.entrypoints._runner import run_task
from velib_ingestion.fetchers.velib_fetcher import VelibFetcher


def main() -> None:
    """Collecte Vélib' : une exécution, puis sortie."""
    run_task("ingest-velib", VelibFetcher().run)


if __name__ == "__main__":
    main()
