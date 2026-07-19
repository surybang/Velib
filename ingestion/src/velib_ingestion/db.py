"""Accès PostgreSQL partagé par les fetchers.

Le pattern retenu est une connexion par exécution, ouverte et refermée dans un
context manager. Une connexion maintenue entre deux exécutions finit par être
fermée côté serveur (idle timeout), et psycopg2 ne le détecte qu'au moment de
l'utiliser, ce qui produit un « SSL SYSCALL error: EOF detected » en pleine
insertion.
"""

import time
from collections.abc import Iterator
from contextlib import contextmanager

import psycopg2
import psycopg2.extensions
from loguru import logger

from velib_ingestion.config import settings

CONNECT_ATTEMPTS = 5
CONNECT_DELAY_SECONDS = 3.0


def connect_with_retry(
    attempts: int = CONNECT_ATTEMPTS,
    delay: float = CONNECT_DELAY_SECONDS,
) -> psycopg2.extensions.connection:
    """Ouvre une connexion PostgreSQL, avec quelques tentatives.

    Le retry couvre le cas d'un démarrage concurrent avec la base (docker
    compose, pod qui redémarre), pas une indisponibilité durable.
    """
    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            conn = psycopg2.connect(
                host=settings.pghost,
                port=settings.pgport,
                user=settings.pguser,
                password=settings.pgpassword,
                dbname=settings.pgdatabase,
            )
            logger.debug("Connexion PostgreSQL établie (tentative {})", attempt)
            return conn
        except psycopg2.OperationalError as exc:
            last_exc = exc
            logger.warning(
                "PostgreSQL indisponible (tentative {}/{}) : {}", attempt, attempts, exc
            )
            if attempt < attempts:
                time.sleep(delay)
    raise RuntimeError(
        f"Connexion à PostgreSQL impossible après {attempts} tentatives"
    ) from last_exc


@contextmanager
def get_connection() -> Iterator[psycopg2.extensions.connection]:
    """Fournit une connexion fermée à la sortie du bloc, quoi qu'il arrive."""
    conn = connect_with_retry()
    try:
        yield conn
    finally:
        conn.close()
