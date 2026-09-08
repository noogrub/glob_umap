import math
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from psycopg import sql

from glob_umap.audit_config import AuditConfig, TableAudit, load_audit_config
from glob_umap.config import load_dataset_config
from glob_umap.db import connect
from glob_umap.provenance import write_manifest
from glob_umap.source import file_sha256, target_columns


def audit_raw(config_path: str | Path, report: Callable[[str], None]) -> None:
    config = load_audit_config(config_path)
    dataset = load_dataset_config(config.dataset_config_path)
    sources = {source["table"]: source for source in dataset.sources}
    if set(sources) != {table.table for table in config.tables}:
        raise ValueError("Audit tables must exactly match dataset source tables")

    results = []
    with connect() as connection:
        for table in config.tables:
            report(f"Auditing {table.table}")
            result = _audit_table(
                connection,
                table,
                sources[table.table],
                config,
            )
            results.append(result)
            report(
                f"  rows={result['row_count']}, "
                f"duplicate_rows={result['key']['duplicate_rows']}, "
                f"invalid_coordinates={result['coordinates']['invalid_rows']}"
            )

    output = {
        "audit": config.name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git_commit(config.project_root),
        "configuration": {
            "audit": _config_file(config.config_path, config.project_root),
            "dataset": _config_file(dataset.config_path, config.project_root),
            "sources": [
                _config_file(path, config.project_root)
                for path in dataset.source_config_paths
            ],
        },
        "dataset": dataset.name,
        "tables": results,
    }
    write_manifest(config.output_path, output)
    report(f"Audit: {config.output_path.relative_to(config.project_root)}")


def _audit_table(
    connection: Any,
    table: TableAudit,
    source: dict[str, Any],
    config: AuditConfig,
) -> dict[str, Any]:
    identifier = _table_identifier(table.table)
    columns = target_columns(source)
    row_count = _scalar(
        connection,
        sql.SQL("SELECT count(*) FROM {}").format(identifier),
    )
    null_counts = _null_counts(connection, identifier, columns)
    ranges = _numeric_ranges(connection, identifier, table.table, columns)
    key_result = _key_audit(connection, identifier, table.key_columns)
    coordinate_result = _coordinate_audit(connection, identifier, table, config)
    return {
        "table": table.table,
        "expected_rows": source["expected_rows"],
        "row_count": row_count,
        "row_count_matches": row_count == source["expected_rows"],
        "key": key_result,
        "coordinates": coordinate_result,
        "null_counts": null_counts,
        "numeric_ranges": ranges,
    }


def _null_counts(connection: Any, table: Any, columns: list[str]) -> dict[str, int]:
    expressions = [
        sql.SQL("count(*) FILTER (WHERE {} IS NULL)").format(sql.Identifier(column))
        for column in columns
    ]
    query = sql.SQL("SELECT {} FROM {}").format(sql.SQL(", ").join(expressions), table)
    with connection.cursor() as cursor:
        cursor.execute(query)
        values = cursor.fetchone()
    return dict(zip(columns, values, strict=True))


def _key_audit(connection: Any, table: Any, columns: tuple[str, ...]) -> dict[str, int]:
    identifiers = [sql.Identifier(column) for column in columns]
    null_test = sql.SQL(" OR ").join(
        sql.SQL("{} IS NULL").format(identifier) for identifier in identifiers
    )
    key_list = sql.SQL(", ").join(identifiers)
    null_rows = _scalar(
        connection,
        sql.SQL("SELECT count(*) FROM {} WHERE {}").format(table, null_test),
    )
    duplicate_query = sql.SQL(
        "SELECT count(*), COALESCE(sum(n - 1), 0)::bigint FROM ("
        "SELECT count(*) AS n FROM {} WHERE NOT ({}) GROUP BY {} HAVING count(*) > 1"
        ") AS duplicates"
    ).format(table, null_test, key_list)
    with connection.cursor() as cursor:
        cursor.execute(duplicate_query)
        duplicate_groups, duplicate_rows = cursor.fetchone()
    return {
        "null_rows": null_rows,
        "duplicate_groups": duplicate_groups,
        "duplicate_rows": duplicate_rows,
    }


def _coordinate_audit(
    connection: Any, table: Any, audit: TableAudit, config: AuditConfig
) -> dict[str, int]:
    ra = sql.Identifier(audit.coordinate_columns[0])
    dec = sql.Identifier(audit.coordinate_columns[1])
    query = sql.SQL(
        "SELECT count(*) FILTER (WHERE {} IS NULL OR {} IS NULL), "
        "count(*) FILTER (WHERE {} < %s OR {} >= %s OR {} < %s OR {} > %s) "
        "FROM {}"
    ).format(ra, dec, ra, ra, dec, dec, table)
    bounds = config.bounds
    with connection.cursor() as cursor:
        cursor.execute(
            query,
            (
                bounds["ra_min_deg"],
                bounds["ra_max_deg"],
                bounds["dec_min_deg"],
                bounds["dec_max_deg"],
            ),
        )
        null_rows, invalid_rows = cursor.fetchone()
    return {"null_rows": null_rows, "invalid_rows": invalid_rows}


def _numeric_ranges(
    connection: Any,
    table: Any,
    table_name: str,
    configured_columns: list[str],
) -> dict[str, dict[str, int | float | str | None]]:
    schema_name, relation_name = table_name.split(".")
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = %s
              AND table_name = %s
              AND data_type IN (
                  'smallint', 'integer', 'bigint', 'real',
                  'double precision', 'numeric'
              )
            """,
            (schema_name, relation_name),
        )
        database_numeric = {row[0] for row in cursor.fetchall()}

    columns = [
        column for column in configured_columns if column in database_numeric
    ]
    expressions = []
    for column in columns:
        identifier = sql.Identifier(column)
        expressions.extend(
            (
                sql.SQL("min({})").format(identifier),
                sql.SQL("max({})").format(identifier),
            )
        )
    query = sql.SQL("SELECT {} FROM {}").format(
        sql.SQL(", ").join(expressions), table
    )
    with connection.cursor() as cursor:
        cursor.execute(query)
        values = cursor.fetchone()

    ranges = {}
    for index, column in enumerate(columns):
        ranges[column] = {
            "min": _json_number(values[2 * index]),
            "max": _json_number(values[2 * index + 1]),
        }
    return ranges


def _json_number(value: Any) -> int | float | str | None:
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    return value


def _scalar(connection: Any, query: Any) -> int:
    with connection.cursor() as cursor:
        cursor.execute(query)
        return cursor.fetchone()[0]


def _table_identifier(name: str) -> Any:
    return sql.Identifier(*name.split("."))


def _git_commit(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _config_file(path: Path, root: Path) -> dict[str, str]:
    return {
        "path": str(path.relative_to(root)),
        "sha256": file_sha256(path),
    }
