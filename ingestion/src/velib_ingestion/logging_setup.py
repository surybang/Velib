"""Configuration de loguru, unique point d'entrée du logging du service."""

import sys

from loguru import logger

from velib_ingestion.config import settings

_HUMAN_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan> | <level>{message}</level>"
)


def setup_logging() -> None:
    """Configure loguru sur stdout.

    En conteneur (json_logs=True), les logs sont sérialisés en JSON pour être
    exploitables par l'orchestrateur. En local, format lisible et coloré.
    """
    logger.remove()
    logger.add(
        sys.stdout,
        level=settings.log_level,
        serialize=settings.json_logs,
        format=_HUMAN_FORMAT,
        backtrace=True,
        diagnose=False,  # ne jamais exposer les valeurs de variables (secrets)
    )
