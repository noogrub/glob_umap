from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable

from psycopg import sql
from psycopg.types.json import Jsonb

from glob_umap.binding_config import BindingConfig, load_binding_config
from glob_umap.db import connect
from glob_umap.provenance import git_commit, software_versions, write_manifest
from glob_umap.source import file_sha256


REFERENCE_ROLE = "reference"
TARGET_ROLE = "target"


def bind_records(config_path: str | Path, report: Callable[[str], None]) -> None:
    config = load_binding_config(config_path)
    sample = config.materialization.sample
    with connect() as connection:
        _require_table(connection)
        sample_id = _sample_id(connection, sample.name)
        member_count = _member_count(connection, sample_id)
        _require_absent(connection, sample_id)
        catalogues = _catalogue_contracts(connection, config)

        inserted = {
            REFERENCE_ROLE: _insert_reference(connection, config, sample_id),
            TARGET_ROLE: _insert_target(connection, config, sample_id),
        }
        for source_role, count in inserted.items():
            if count != member_count:
                raise RuntimeError(
                    f"Bound {count} {source_role} records; sample contains "
                    f"{member_count} members"
                )

        summary = _binding_summary(connection, sample_id)
        binding_sha256 = _binding_sha256(connection, sample_id)
        _record_definition(
            connection, config, sample_id, summary, binding_sha256
        )

    output = {
        "stage": config.name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit(config.project_root),
        "configuration": {
            "binding": _config_file(config.config_path, config.project_root),
            "materialization": _config_file(
                config.materialization.config_path, config.project_root
            ),
            "sample": _config_file(sample.config_path, config.project_root),
            "resolved": config.resolved,
        },
        "sample": {"name": sample.name, "sample_id": sample_id},
        "selection": {
            "match_run": sample.match_run,
            "match_policy": sample.match_policy,
            "reference_catalog": sample.reference_catalog,
            "target_catalog": sample.target_catalog,
        },
        "catalogues": catalogues,
        "member_count": member_count,
        "inserted": inserted,
        "binding_summary": summary,
        "binding_sha256": binding_sha256,
        "software": software_versions("psycopg", "PyYAML"),
    }
    write_manifest(config.report_path, output)
    report(f"Bound catalogue records: {member_count} sample members")
    for source_role, count in inserted.items():
        report(f"  {source_role}: {count}")
    report(f"Binding sha256: {binding_sha256}")
    report(f"Manifest: {config.report_path.relative_to(config.project_root)}")


def _require_table(connection: Any) -> None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT to_regclass('ml.member_record')")
        present = cursor.fetchone()[0]
    if present is None:
        raise ValueError("Apply sql/41_member_record.sql before binding records")


def _sample_id(connection: Any, name: str) -> int:
    with connection.cursor() as cursor:
        cursor.execute("SELECT sample_id FROM ml.sample WHERE name = %s", (name,))
        row = cursor.fetchone()
    if row is None:
        raise ValueError(f"Materialized sample does not exist: {name}")
    return int(row[0])


def _member_count(connection: Any, sample_id: int) -> int:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT count(*) FROM ml.member WHERE sample_id = %s",
            (sample_id,),
        )
        count = int(cursor.fetchone()[0])
    if count == 0:
        raise ValueError("Materialized sample has no members")
    return count


def _require_absent(connection: Any, sample_id: int) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT count(*) FROM ml.member_record WHERE sample_id = %s",
            (sample_id,),
        )
        count = int(cursor.fetchone()[0])
    if count:
        raise ValueError(f"Sample already has bound records: {count}")


def _insert_reference(
    connection: Any, config: BindingConfig, sample_id: int
) -> int:
    sample = config.materialization.sample
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO ml.member_record (
                sample_id, object_id, source_role, record_id
            )
            SELECT m.sample_id, m.object_id, %s, o.origin_record_id
            FROM ml.member AS m
            JOIN core.object AS o USING (object_id)
            JOIN core.record AS r ON r.record_id = o.origin_record_id
            JOIN core.catalog AS c USING (catalog_id)
            WHERE m.sample_id = %s
              AND c.code = %s
            ORDER BY m.object_id
            """,
            (REFERENCE_ROLE, sample_id, sample.reference_catalog),
        )
        return int(cursor.rowcount)


def _insert_target(
    connection: Any, config: BindingConfig, sample_id: int
) -> int:
    query, parameters = _target_query(config, sample_id)
    with connection.cursor() as cursor:
        cursor.execute(query, parameters)
        return int(cursor.rowcount)


def _target_query(
    config: BindingConfig, sample_id: int
) -> tuple[sql.Composed, tuple[Any, ...]]:
    sample = config.materialization.sample
    policy = sql.SQL("reference_rank = 1")
    if sample.match_policy == "reciprocal_nearest":
        policy += sql.SQL(" AND target_rank = 1")
    query = sql.SQL(
        """
        WITH candidates AS (
            SELECT m.object_id,
                   m.record_id,
                   m.candidate_rank AS target_rank,
                   row_number() OVER (
                       PARTITION BY m.object_id
                       ORDER BY m.angular_sep_arcsec, m.record_id
                   ) AS reference_rank
            FROM core.match AS m
            JOIN core.match_run AS mr USING (match_run_id)
            JOIN core.record AS r ON r.record_id = m.record_id
            JOIN core.catalog AS c USING (catalog_id)
            WHERE mr.name = %s
              AND c.code = %s
        ), selected AS (
            SELECT object_id, record_id
            FROM candidates
            WHERE {policy}
        )
        INSERT INTO ml.member_record (
            sample_id, object_id, source_role, record_id
        )
        SELECT members.sample_id, members.object_id, %s, selected.record_id
        FROM ml.member AS members
        JOIN selected USING (object_id)
        WHERE members.sample_id = %s
        ORDER BY members.object_id
        """
    ).format(policy=policy)
    parameters = (
        sample.match_run,
        sample.target_catalog,
        TARGET_ROLE,
        sample_id,
    )
    return query, parameters


def _binding_summary(
    connection: Any, sample_id: int
) -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT mr.source_role,
                   c.code,
                   count(*) AS bindings,
                   count(DISTINCT mr.record_id) AS distinct_records
            FROM ml.member_record AS mr
            JOIN core.record AS r USING (record_id)
            JOIN core.catalog AS c USING (catalog_id)
            WHERE mr.sample_id = %s
            GROUP BY mr.source_role, c.code
            ORDER BY mr.source_role, c.code
            """,
            (sample_id,),
        )
        rows = cursor.fetchall()
    return [
        {
            "source_role": row[0],
            "catalog_code": row[1],
            "bindings": int(row[2]),
            "distinct_records": int(row[3]),
        }
        for row in rows
    ]


def _binding_sha256(connection: Any, sample_id: int) -> str:
    digest = sha256()
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT origin_catalog.code,
                   origin.source_key::jsonb ->> 1 AS origin_source_row,
                   m.target_class,
                   m.split,
                   mr.source_role,
                   bound_catalog.code,
                   bound.source_key::jsonb ->> 1 AS bound_source_row
            FROM ml.member AS m
            JOIN core.object AS o USING (object_id)
            JOIN core.record AS origin
              ON origin.record_id = o.origin_record_id
            JOIN core.catalog AS origin_catalog
              ON origin_catalog.catalog_id = origin.catalog_id
            JOIN ml.member_record AS mr
              ON mr.sample_id = m.sample_id
             AND mr.object_id = m.object_id
            JOIN core.record AS bound ON bound.record_id = mr.record_id
            JOIN core.catalog AS bound_catalog
              ON bound_catalog.catalog_id = bound.catalog_id
            WHERE m.sample_id = %s
            ORDER BY origin_catalog.code,
                     (origin.source_key::jsonb ->> 1)::bigint,
                     mr.source_role
            """,
            (sample_id,),
        )
        for row in cursor:
            digest.update("\t".join(str(value) for value in row).encode("ascii"))
            digest.update(b"\n")
    return digest.hexdigest()


def _catalogue_contracts(
    connection: Any, config: BindingConfig
) -> list[dict[str, Any]]:
    sample = config.materialization.sample
    codes = sorted({sample.reference_catalog, sample.target_catalog})
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT code, local_path, sha256, loaded_rows, loaded_at
            FROM core.catalog
            WHERE code = ANY(%s)
            ORDER BY code
            """,
            (codes,),
        )
        rows = cursor.fetchall()
    if {row[0] for row in rows} != set(codes):
        raise ValueError("Not all binding catalogues are registered")
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


def _record_definition(
    connection: Any,
    config: BindingConfig,
    sample_id: int,
    summary: list[dict[str, Any]],
    binding_sha256: str,
) -> None:
    sample = config.materialization.sample
    definition = {
        "configuration": {
            "binding": _config_file(config.config_path, config.project_root),
            "materialization": _config_file(
                config.materialization.config_path, config.project_root
            ),
            "sample": _config_file(sample.config_path, config.project_root),
            "resolved": config.resolved,
        },
        "selection": {
            "match_run": sample.match_run,
            "match_policy": sample.match_policy,
            "reference_catalog": sample.reference_catalog,
            "target_catalog": sample.target_catalog,
        },
        "binding_summary": summary,
        "binding_sha256": binding_sha256,
    }
    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE ml.sample
            SET definition = jsonb_set(
                definition, '{records}', %s, true
            )
            WHERE sample_id = %s
              AND NOT definition ? 'records'
            """,
            (Jsonb(definition), sample_id),
        )
        if cursor.rowcount != 1:
            raise ValueError("Sample definition already contains record bindings")


def _config_file(path: Path, root: Path) -> dict[str, str]:
    return {
        "path": str(path.relative_to(root)),
        "sha256": file_sha256(path),
    }
