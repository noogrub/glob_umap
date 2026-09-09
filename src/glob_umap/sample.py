from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from psycopg import sql
from psycopg.types.json import Jsonb

from glob_umap.db import connect
from glob_umap.funnel import population_ctes, query_counts
from glob_umap.materialize_config import (
    MaterializationConfig,
    load_materialization_config,
)
from glob_umap.provenance import git_commit, software_versions, write_manifest
from glob_umap.source import file_sha256


def materialize_sample(
    config_path: str | Path, report: Callable[[str], None]
) -> None:
    settings = load_materialization_config(config_path)
    config = settings.sample
    with connect() as connection:
        _ensure_absent(connection, config.name)
        expected = query_counts(connection, config)
        sample_id = _create_sample(connection, settings)
        class_counts = _insert_members(connection, settings, sample_id)
        inserted = sum(class_counts.values())
        if inserted != expected["labeled"]:
            raise RuntimeError(
                f"Materialized {inserted} members; funnel expected "
                f"{expected['labeled']}"
            )

    output = {
        "sample": config.name,
        "sample_id": sample_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit(settings.project_root),
        "configuration": {
            "path": str(settings.config_path.relative_to(settings.project_root)),
            "sha256": file_sha256(settings.config_path),
            "resolved": settings.resolved,
        },
        "sample_configuration": {
            "path": str(config.config_path.relative_to(config.project_root)),
            "sha256": file_sha256(config.config_path),
            "resolved": config.resolved,
        },
        "funnel_counts": expected,
        "member_count": inserted,
        "class_counts": class_counts,
        "initial_split": settings.initial_split,
        "member_weight": settings.member_weight,
        "software": software_versions("psycopg", "PyYAML"),
    }
    write_manifest(settings.report_path, output)
    report(f"Materialized {config.name}: {inserted} members")
    for target_class, count in class_counts.items():
        report(f"  {target_class}: {count}")
    report(
        "Report: "
        f"{settings.report_path.relative_to(settings.project_root)}"
    )


def _ensure_absent(connection: Any, name: str) -> None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM ml.sample WHERE name = %s", (name,))
        if cursor.fetchone() is not None:
            raise ValueError(f"Sample already exists: {name}")


def _create_sample(connection: Any, settings: MaterializationConfig) -> int:
    config = settings.sample
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO ml.sample (
                name, description, config_path, config_sha256, definition
            ) VALUES (%s, %s, %s, %s, %s)
            RETURNING sample_id
            """,
            (
                config.name,
                config.description,
                str(settings.config_path.relative_to(settings.project_root)),
                file_sha256(settings.config_path),
                Jsonb(
                    {
                        "materialization": settings.resolved["materialization"],
                        "sample": config.resolved,
                    }
                ),
            ),
        )
        return int(cursor.fetchone()[0])


def _insert_members(
    connection: Any, settings: MaterializationConfig, sample_id: int
) -> dict[str, int]:
    statement, parameters = _member_query(settings, sample_id)
    with connection.cursor() as cursor:
        cursor.execute(statement, parameters)
        rows = cursor.fetchall()
    counts = {
        settings.gc_target_class: 0,
        settings.galaxy_target_class: 0,
        settings.star_target_class: 0,
    }
    for target_class, count in rows:
        counts[target_class] = int(count)
    return counts


def _member_query(
    settings: MaterializationConfig, sample_id: int
) -> tuple[sql.Composed, list[Any]]:
    config = settings.sample
    population, population_parameters = population_ctes(config)
    statement = sql.SQL(
        """
        WITH {}, selected AS (
            SELECT object_id,
                   CASE
                       WHEN is_gc THEN %s
                       WHEN is_galaxy_candidate THEN %s
                       WHEN is_star_candidate THEN %s
                   END AS target_class
            FROM population
            WHERE error_qualified
              AND (is_gc OR is_galaxy_candidate OR is_star_candidate)
        ), inserted AS (
            INSERT INTO ml.member (
                sample_id, object_id, split, target_class, weight
            )
            SELECT %s, object_id, %s, target_class, %s
            FROM selected
            ORDER BY object_id
            RETURNING target_class
        )
        SELECT target_class, count(*)
        FROM inserted
        GROUP BY target_class
        ORDER BY target_class
        """
    ).format(population)
    parameters = [
        *population_parameters,
        settings.gc_target_class,
        settings.galaxy_target_class,
        settings.star_target_class,
        sample_id,
        settings.initial_split,
        settings.member_weight,
    ]
    return statement, parameters
