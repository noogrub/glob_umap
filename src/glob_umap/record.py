from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from psycopg import sql

from glob_umap.core_config import RecordSource, load_record_config
from glob_umap.db import connect, validate_columns
from glob_umap.provenance import git_commit, software_versions, write_manifest
from glob_umap.source import file_sha256


def populate_records(config_path: str | Path, report: Callable[[str], None]) -> None:
    config = load_record_config(config_path)
    results = []
    with connect() as connection:
        _ensure_empty(connection, "core.record")
        _ensure_empty(connection, "core.object")
        _ensure_empty(connection, "core.match")
        for source in config.sources:
            report(f"Recording {source.catalog_code} from {source.raw_table}")
            result = _populate_source(connection, source)
            results.append(result)
            report(
                f"Recorded {source.catalog_code}: {result['inserted_rows']} rows"
            )

    manifest = {
        "stage": config.name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit(config.project_root),
        "configuration": {
            "path": str(config.config_path.relative_to(config.project_root)),
            "sha256": file_sha256(config.config_path),
            "resolved": config.resolved,
        },
        "catalogues": results,
        "software": software_versions("psycopg", "PyYAML"),
        "total_records": sum(result["inserted_rows"] for result in results),
    }
    write_manifest(config.manifest_path, manifest)
    report(f"Record normalization complete: {manifest['total_records']} rows")
    report(f"Manifest: {config.manifest_path.relative_to(config.project_root)}")


def _populate_source(connection: Any, source: RecordSource) -> dict[str, Any]:
    required = [
        source.raw_ingest_column,
        *source.key_columns,
        source.ra_column,
        source.dec_column,
    ]
    validate_columns(connection, source.raw_table, required)
    catalog = _catalog(connection, source.catalog_code)
    catalog_id = catalog["catalog_id"]
    loaded_rows = catalog["loaded_rows"]
    table = sql.Identifier(*source.raw_table.split("."))
    keys = sql.SQL(", ").join(sql.Identifier(key) for key in source.key_columns)
    statement = sql.SQL(
        "INSERT INTO core.record ("
        "catalog_id, source_key, ra_deg, dec_deg, raw_ingest_id"
        ") SELECT %s, jsonb_build_array({})::text, {}, {}, {} "
        "FROM {} ORDER BY {}"
    ).format(
        keys,
        sql.Identifier(source.ra_column),
        sql.Identifier(source.dec_column),
        sql.Identifier(source.raw_ingest_column),
        table,
        sql.Identifier(source.raw_ingest_column),
    )
    with connection.cursor() as cursor:
        cursor.execute(statement, (catalog_id,))
        inserted = cursor.rowcount
    if loaded_rows is not None and inserted != loaded_rows:
        raise RuntimeError(
            f"Record-count mismatch for {source.catalog_code}: "
            f"catalogue has {loaded_rows}, inserted {inserted}"
        )
    return {
        "catalog_code": source.catalog_code,
        "raw_table": source.raw_table,
        **catalog,
        "inserted_rows": inserted,
    }


def _catalog(connection: Any, code: str) -> dict[str, Any]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT catalog_id, loaded_rows, local_path, sha256, loaded_at
            FROM core.catalog
            WHERE code = %s
            """,
            (code,),
        )
        row = cursor.fetchone()
    if row is None:
        raise ValueError(f"Catalogue is not registered: {code}")
    return {
        "catalog_id": row[0],
        "loaded_rows": row[1],
        "local_path": row[2],
        "sha256": row[3],
        "loaded_at": row[4].isoformat() if row[4] is not None else None,
    }


def _ensure_empty(connection: Any, table_name: str) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            sql.SQL("SELECT count(*) FROM {}").format(
                sql.Identifier(*table_name.split("."))
            )
        )
        count = cursor.fetchone()[0]
    if count:
        raise ValueError(f"Target table is not empty: {table_name} ({count} rows)")
