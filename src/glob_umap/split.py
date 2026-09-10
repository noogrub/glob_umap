from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable

from psycopg import sql
from psycopg.types.json import Jsonb

from glob_umap.db import connect
from glob_umap.provenance import git_commit, software_versions, write_manifest
from glob_umap.source import file_sha256
from glob_umap.split_config import SplitConfig, load_split_config


ALGORITHM = "stratified_stable_hash"
IDENTITY = "origin_catalog_code_and_source_row"
ALLOCATION = "nearest_integer_per_class"


def assign_split(config_path: str | Path, report: Callable[[str], None]) -> None:
    config = load_split_config(config_path)
    with connect() as connection:
        sample_id = _sample_id(connection, config.sample_name)
        source_counts = _require_unassigned(connection, config, sample_id)
        _require_label_support(connection, sample_id)
        split_counts = _assign_members(connection, config, sample_id)
        assigned = sum(item["members"] for item in split_counts)
        expected = sum(source_counts.values())
        if assigned != expected:
            raise RuntimeError(
                f"Assigned {assigned} members; sample contains {expected}"
            )
        assignment_sha256 = _assignment_sha256(connection, sample_id)
        _record_definition(
            connection, config, sample_id, split_counts, assignment_sha256
        )

    output = {
        "stage": config.name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit(config.project_root),
        "configuration": {
            "path": str(config.config_path.relative_to(config.project_root)),
            "sha256": file_sha256(config.config_path),
            "resolved": config.resolved,
        },
        "sample": {"name": config.sample_name, "sample_id": sample_id},
        "algorithm": {
            "name": ALGORITHM,
            "identity": IDENTITY,
            "allocation": ALLOCATION,
        },
        "source_counts": source_counts,
        "split_counts": split_counts,
        "member_count": assigned,
        "assignment_sha256": assignment_sha256,
        "software": software_versions("psycopg", "PyYAML"),
    }
    write_manifest(config.report_path, output)
    report(f"Assigned {config.sample_name}: {assigned} members")
    for item in split_counts:
        report(
            f"  {item['split']} / {item['target_class']}: "
            f"{item['members']}"
        )
    report(f"Assignment sha256: {assignment_sha256}")
    report(f"Manifest: {config.report_path.relative_to(config.project_root)}")


def _sample_id(connection: Any, name: str) -> int:
    with connection.cursor() as cursor:
        cursor.execute("SELECT sample_id FROM ml.sample WHERE name = %s", (name,))
        row = cursor.fetchone()
    if row is None:
        raise ValueError(f"Materialized sample does not exist: {name}")
    return int(row[0])


def _require_unassigned(
    connection: Any, config: SplitConfig, sample_id: int
) -> dict[str, int]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT split, count(*)
            FROM ml.member
            WHERE sample_id = %s
            GROUP BY split
            ORDER BY split
            """,
            (sample_id,),
        )
        rows = cursor.fetchall()
    counts = {str(row[0]): int(row[1]) for row in rows}
    if not counts:
        raise ValueError(f"Sample has no members: {config.sample_name}")
    if set(counts) != {config.source_split}:
        raise ValueError(
            f"Sample members are not exclusively {config.source_split}: {counts}"
        )
    return counts


def _require_label_support(connection: Any, sample_id: int) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT count(*)
            FROM ml.member AS m
            WHERE m.sample_id = %s
              AND NOT EXISTS (
                  SELECT 1
                  FROM core.label AS l
                  WHERE l.object_id = m.object_id
                    AND l.class = m.target_class
              )
            """,
            (sample_id,),
        )
        unsupported = int(cursor.fetchone()[0])
    if unsupported:
        raise RuntimeError(
            f"Cannot split sample: {unsupported} members lack supporting label evidence"
        )


def _assign_members(
    connection: Any, config: SplitConfig, sample_id: int
) -> list[dict[str, Any]]:
    statement, parameters = _split_query(config, sample_id)
    with connection.cursor() as cursor:
        cursor.execute(statement, parameters)
        rows = cursor.fetchall()
    return [
        {"target_class": row[0], "split": row[1], "members": int(row[2])}
        for row in rows
    ]


def _split_query(
    config: SplitConfig, sample_id: int
) -> tuple[sql.SQL, tuple[Any, ...]]:
    statement = sql.SQL(
        """
        WITH ranked AS (
            SELECT m.object_id,
                   row_number() OVER (
                       PARTITION BY m.target_class
                       ORDER BY md5(concat(
                           c.code, ':',
                           origin.source_key::jsonb ->> 1, ':',
                           %s::text
                       )), c.code,
                       (origin.source_key::jsonb ->> 1)::bigint
                   ) AS class_rank,
                   count(*) OVER (
                       PARTITION BY m.target_class
                   ) AS class_count
            FROM ml.member AS m
            JOIN core.object AS o USING (object_id)
            JOIN core.record AS origin
              ON origin.record_id = o.origin_record_id
            JOIN core.catalog AS c USING (catalog_id)
            WHERE m.sample_id = %s
              AND m.split = %s::text
        ), assigned AS (
            UPDATE ml.member AS m
            SET split = CASE
                WHEN ranked.class_rank <= floor(
                    ranked.class_count * %s::double precision + 0.5
                )::bigint THEN %s::text
                ELSE %s::text
            END
            FROM ranked
            WHERE m.sample_id = %s
              AND m.object_id = ranked.object_id
            RETURNING m.target_class, m.split
        )
        SELECT target_class, split, count(*)
        FROM assigned
        GROUP BY target_class, split
        ORDER BY split, target_class
        """
    )
    parameters = (
        config.seed,
        sample_id,
        config.source_split,
        config.test_fraction,
        config.test_split,
        config.development_split,
        sample_id,
    )
    return statement, parameters


def _assignment_sha256(connection: Any, sample_id: int) -> str:
    digest = sha256()
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT c.code,
                   origin.source_key::jsonb ->> 1 AS source_row,
                   m.target_class,
                   m.split
            FROM ml.member AS m
            JOIN core.object AS o USING (object_id)
            JOIN core.record AS origin
              ON origin.record_id = o.origin_record_id
            JOIN core.catalog AS c USING (catalog_id)
            WHERE m.sample_id = %s
            ORDER BY c.code,
                     (origin.source_key::jsonb ->> 1)::bigint
            """,
            (sample_id,),
        )
        for row in cursor:
            digest.update("\t".join(str(value) for value in row).encode("ascii"))
            digest.update(b"\n")
    return digest.hexdigest()


def _record_definition(
    connection: Any,
    config: SplitConfig,
    sample_id: int,
    split_counts: list[dict[str, Any]],
    assignment_sha256: str,
) -> None:
    definition = {
        "configuration": {
            "path": str(config.config_path.relative_to(config.project_root)),
            "sha256": file_sha256(config.config_path),
            "resolved": config.resolved,
        },
        "algorithm": {
            "name": ALGORITHM,
            "identity": IDENTITY,
            "allocation": ALLOCATION,
        },
        "split_counts": split_counts,
        "assignment_sha256": assignment_sha256,
    }
    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE ml.sample
            SET definition = jsonb_set(
                definition, '{split}', %s, true
            )
            WHERE sample_id = %s
              AND NOT definition ? 'split'
            """,
            (Jsonb(definition), sample_id),
        )
        if cursor.rowcount != 1:
            raise ValueError("Sample definition already contains a split")
