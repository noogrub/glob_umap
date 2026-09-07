from pathlib import Path
from time import monotonic
from typing import Any, Callable, Iterable

import psycopg
from psycopg import sql


def connect() -> psycopg.Connection[Any]:
    return psycopg.connect("")


def ensure_empty(
    connection: psycopg.Connection[Any], table_name: str
) -> None:
    table = _table_identifier(table_name)
    with connection.cursor() as cursor:
        cursor.execute(sql.SQL("SELECT count(*) FROM {}").format(table))
        count = cursor.fetchone()[0]
    if count != 0:
        raise ValueError(f"Target table is not empty: {table_name} ({count} rows)")


def validate_columns(
    connection: psycopg.Connection[Any],
    table_name: str,
    source_columns: list[str],
) -> None:
    schema_name, relation_name = _table_parts(table_name)
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            """,
            (schema_name, relation_name),
        )
        database_columns = {row[0] for row in cursor.fetchall()}

    required = {"source_file", "source_row", *source_columns}
    missing = sorted(required - database_columns)
    if missing:
        raise ValueError(
            f"Target table lacks configured columns: {table_name}: {missing}"
        )


def copy_rows(
    connection: psycopg.Connection[Any],
    table_name: str,
    source_file: Path,
    columns: list[str],
    source_rows: Iterable[tuple[int, list[str | None]]],
    progress_interval_seconds: float,
    progress: Callable[[int], None],
) -> int:
    table = _table_identifier(table_name)
    all_columns = ["source_file", "source_row", *columns]
    identifiers = sql.SQL(", ").join(map(sql.Identifier, all_columns))
    statement = sql.SQL("COPY {} ({}) FROM STDIN").format(table, identifiers)
    loaded = 0
    next_progress = monotonic() + progress_interval_seconds
    with connection.cursor().copy(statement) as copy:
        for source_row, values in source_rows:
            copy.write_row([str(source_file), source_row, *values])
            loaded += 1
            now = monotonic()
            if now >= next_progress:
                progress(loaded)
                next_progress = now + progress_interval_seconds
    return loaded


def ensure_catalog_codes_available(
    connection: psycopg.Connection[Any], sources: Iterable[dict[str, Any]]
) -> None:
    codes = [source["catalog"]["code"] for source in sources]
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT code FROM core.catalog WHERE code = ANY(%s)",
            (codes,),
        )
        existing = sorted(row[0] for row in cursor.fetchall())
    if existing:
        raise ValueError(f"Catalogue codes already registered: {existing}")


def register_catalog(
    connection: psycopg.Connection[Any],
    source: dict[str, Any],
    loaded_rows: int,
) -> None:
    catalog = source["catalog"]
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO core.catalog (
                code,
                title,
                release,
                source_url,
                local_path,
                sha256,
                expected_rows,
                loaded_rows,
                loaded_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            """,
            (
                catalog["code"],
                catalog["title"],
                catalog["release"],
                catalog["source_url"],
                source["path"],
                source["sha256"],
                source["expected_rows"],
                loaded_rows,
            ),
        )


def _table_identifier(table_name: str) -> sql.Composed:
    parts = _table_parts(table_name)
    return sql.Identifier(*parts)


def _table_parts(table_name: str) -> tuple[str, str]:
    parts = table_name.split(".")
    if len(parts) != 2 or any(not part.isidentifier() for part in parts):
        raise ValueError(f"Expected schema.table identifier: {table_name}")
    return parts[0], parts[1]
