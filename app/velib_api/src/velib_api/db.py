"""Accès PostgreSQL partagé par les routers."""

from collections.abc import Iterator
from contextlib import contextmanager

import psycopg2
import psycopg2.extensions
import psycopg2.extras

from velib_api.config import settings


@contextmanager
def get_connection() -> Iterator[psycopg2.extensions.connection]:
    conn = psycopg2.connect(
        host=settings.pghost,
        port=settings.pgport,
        user=settings.pguser,
        password=settings.pgpassword,
        dbname=settings.pgdatabase,
    )
    try:
        yield conn
    finally:
        conn.close()


def query(sql: str, params: tuple = ()) -> list[dict]:
    """Exécute une requête et retourne une liste de dicts."""
    with (
        get_connection() as conn,
        conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur,
    ):
        cur.execute(sql, params)
        return [dict(row) for row in cur.fetchall()]
