"""Enveloppe commune aux entrypoints : logging, exécution, code de sortie."""

import sys
from collections.abc import Callable

from loguru import logger

from velib_ingestion.logging_setup import setup_logging


def run_task(name: str, task: Callable[[], dict]) -> None:
    """Exécute une tâche et traduit son issue en code de sortie processus."""
    setup_logging()
    try:
        result = task()
    except Exception:  # noqa: BLE001
        logger.exception("Échec de la tâche {}", name)
        sys.exit(1)

    logger.info("Tâche {} terminée : {}", name, result)
    sys.exit(0)
