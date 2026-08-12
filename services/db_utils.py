from typing import Any, Iterable

from config.database import get_connection


def fetch_all_as_dicts(query: str, params: Iterable[Any] | None = None):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, tuple(params or ()))
        colunas = [column[0] for column in cursor.description] if cursor.description else []
        return [dict(zip(colunas, row)) for row in cursor.fetchall()]
    finally:
        conn.close()
