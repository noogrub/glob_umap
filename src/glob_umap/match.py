from datetime import datetime, timezone
from pathlib import Path
from time import monotonic
from typing import Any, Callable

import numpy as np
from psycopg import sql
from psycopg.types.json import Jsonb

from glob_umap.core_config import MatchConfig, load_match_config
from glob_umap.db import connect
from glob_umap.provenance import git_commit, software_versions, write_manifest
from glob_umap.sky import candidate_batches
from glob_umap.source import file_sha256


def match_catalogues(config_path: str | Path, report: Callable[[str], None]) -> None:
    config = load_match_config(config_path)
    with connect() as connection:
        _require_migration(connection)
        _ensure_match_absent(connection, config.name)
        inputs = _catalogue_contracts(
            connection,
            (config.reference_catalog, config.target_catalog),
        )
        reference = _records(connection, config.reference_catalog)
        target = _records(connection, config.target_catalog)
        report(
            f"Crossmatching {len(target[0])} {config.target_catalog} records "
            f"against {len(reference[0])} {config.reference_catalog} records"
        )
        run_id = _create_run(connection, config)
        object_ids = _seed_objects(connection, config.reference_catalog)
        if len(object_ids) != len(reference[0]):
            raise RuntimeError("Reference object count does not match record count")
        _insert_identity_matches(connection, run_id, config)
        stats = _insert_candidates(
            connection,
            run_id,
            config,
            object_ids,
            reference,
            target,
            report,
        )

    output = {
        "match": config.name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit(config.project_root),
        "configuration": {
            "path": str(config.config_path.relative_to(config.project_root)),
            "sha256": file_sha256(config.config_path),
            "resolved": config.resolved,
        },
        "inputs": inputs,
        "counts": stats,
        "software": software_versions("numpy", "scipy", "psycopg", "PyYAML"),
    }
    write_manifest(config.report_path, output)
    report(f"Candidate generation complete: {stats['candidate_pairs']} pairs")
    report(f"Report: {config.report_path.relative_to(config.project_root)}")


def _records(
    connection: Any, catalog_code: str
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT record_id, ra_deg, dec_deg
            FROM core.record
            JOIN core.catalog USING (catalog_id)
            WHERE code = %s
            ORDER BY record_id
            """,
            (catalog_code,),
        )
        rows = cursor.fetchall()
    if not rows:
        raise ValueError(f"No normalized records found for {catalog_code}")
    identifiers = np.fromiter((row[0] for row in rows), dtype=np.int64)
    ra = np.fromiter((row[1] for row in rows), dtype=np.float64)
    dec = np.fromiter((row[2] for row in rows), dtype=np.float64)
    return identifiers, ra, dec


def _create_run(connection: Any, config: MatchConfig) -> int:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO core.match_run (
                name, method, config_path, config_sha256, resolved_config
            ) VALUES (%s, %s, %s, %s, %s)
            RETURNING match_run_id
            """,
            (
                config.name,
                config.method,
                str(config.config_path.relative_to(config.project_root)),
                file_sha256(config.config_path),
                Jsonb(config.resolved),
            ),
        )
        return cursor.fetchone()[0]


def _catalogue_contracts(
    connection: Any, catalog_codes: tuple[str, str]
) -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT code, local_path, sha256, loaded_rows, loaded_at
            FROM core.catalog
            WHERE code = ANY(%s)
            ORDER BY code
            """,
            (list(catalog_codes),),
        )
        rows = cursor.fetchall()
    found = {row[0] for row in rows}
    missing = sorted(set(catalog_codes) - found)
    if missing:
        raise ValueError(f"Catalogues are not registered: {missing}")
    return [
        {
            "catalog_code": row[0],
            "local_path": row[1],
            "sha256": row[2],
            "loaded_rows": row[3],
            "loaded_at": row[4].isoformat() if row[4] is not None else None,
        }
        for row in rows
    ]


def _seed_objects(connection: Any, catalog_code: str) -> np.ndarray:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO core.object (origin_record_id, ra_deg, dec_deg)
            SELECT record_id, ra_deg, dec_deg
            FROM core.record
            JOIN core.catalog USING (catalog_id)
            WHERE code = %s
            ORDER BY record_id
            RETURNING object_id, origin_record_id
            """,
            (catalog_code,),
        )
        rows = cursor.fetchall()
    rows.sort(key=lambda row: row[1])
    return np.fromiter((row[0] for row in rows), dtype=np.int64)


def _insert_identity_matches(
    connection: Any, run_id: int, config: MatchConfig
) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO core.match (
                match_run_id, object_id, record_id, angular_sep_arcsec,
                method, search_radius_arcsec, candidate_count, candidate_rank,
                selected, ambiguous
            )
            SELECT %s, object_id, origin_record_id, 0.0, %s, %s,
                   1, 1, true, false
            FROM core.object
            ORDER BY origin_record_id
            """,
            (run_id, config.method, config.search_radius_arcsec),
        )


def _insert_candidates(
    connection: Any,
    run_id: int,
    config: MatchConfig,
    object_ids: np.ndarray,
    reference: tuple[np.ndarray, np.ndarray, np.ndarray],
    target: tuple[np.ndarray, np.ndarray, np.ndarray],
    report: Callable[[str], None],
) -> dict[str, int | float | None]:
    target_ids, target_ra, target_dec = target
    _, reference_ra, reference_dec = reference
    target_with_candidates = 0
    ambiguous_targets = 0
    candidate_pairs = 0
    reference_hits = np.zeros(object_ids.size, dtype=np.int64)
    separations: list[float] = []
    next_report = monotonic() + config.progress_interval_seconds
    statement = sql.SQL(
        "COPY core.match ("
        "match_run_id, object_id, record_id, angular_sep_arcsec, method, "
        "search_radius_arcsec, candidate_count, candidate_rank, selected, ambiguous"
        ") FROM STDIN"
    )
    with connection.cursor().copy(statement) as copy:
        for _, stop, rows in candidate_batches(
            object_ids,
            reference_ra,
            reference_dec,
            target_ids,
            target_ra,
            target_dec,
            config.search_radius_arcsec,
            config.chunk_rows,
            config.workers,
        ):
            seen_targets: set[int] = set()
            for target_id, object_id, separation, count, rank in rows:
                copy.write_row(
                    (
                        run_id,
                        object_id,
                        target_id,
                        separation,
                        config.method,
                        config.search_radius_arcsec,
                        count,
                        rank,
                        False,
                        count > 1,
                    )
                )
                seen_targets.add(target_id)
                object_index = int(np.searchsorted(object_ids, object_id))
                reference_hits[object_index] += 1
                separations.append(separation)
            target_with_candidates += len(seen_targets)
            ambiguous_targets += sum(
                1 for row in rows if row[4] == 1 and row[3] > 1
            )
            candidate_pairs += len(rows)
            if monotonic() >= next_report:
                report(
                    f"  searched {stop}/{target_ids.size} target records; "
                    f"found {candidate_pairs} candidate pairs"
                )
                next_report = monotonic() + config.progress_interval_seconds

    separation_values = np.asarray(separations, dtype=np.float64)
    return {
        "reference_records": int(object_ids.size),
        "target_records": int(target_ids.size),
        "target_with_candidates": target_with_candidates,
        "target_without_candidates": int(target_ids.size - target_with_candidates),
        "target_with_one_candidate": target_with_candidates - ambiguous_targets,
        "target_with_multiple_candidates": ambiguous_targets,
        "reference_with_targets": int(np.count_nonzero(reference_hits)),
        "reference_with_multiple_targets": int(np.count_nonzero(reference_hits > 1)),
        "candidate_pairs": candidate_pairs,
        "separation_min_arcsec": (
            float(np.min(separation_values)) if separation_values.size else None
        ),
        "separation_median_arcsec": (
            float(np.median(separation_values)) if separation_values.size else None
        ),
        "separation_max_arcsec": (
            float(np.max(separation_values)) if separation_values.size else None
        ),
    }


def _ensure_match_absent(connection: Any, name: str) -> None:
    for table in ("core.object", "core.match"):
        with connection.cursor() as cursor:
            cursor.execute(
                sql.SQL("SELECT count(*) FROM {}").format(
                    sql.Identifier(*table.split("."))
                )
            )
            count = cursor.fetchone()[0]
        if count:
            raise ValueError(f"Target table is not empty: {table} ({count} rows)")
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM core.match_run WHERE name = %s", (name,))
        if cursor.fetchone() is not None:
            raise ValueError(f"Match run already exists: {name}")


def _require_migration(connection: Any) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'core'
              AND table_name = 'object'
              AND column_name = 'origin_record_id'
            """
        )
        if cursor.fetchone() is None:
            raise ValueError("Apply sql/31_object_origin.sql before matching")
