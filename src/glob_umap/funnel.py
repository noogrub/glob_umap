from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from psycopg import sql

from glob_umap.db import connect
from glob_umap.provenance import git_commit, software_versions, write_manifest
from glob_umap.sample_config import ClassRule, SampleConfig, load_sample_config
from glob_umap.source import file_sha256


def build_funnel(config_path: str | Path, report: Callable[[str], None]) -> None:
    config = load_sample_config(config_path)
    with connect() as connection:
        counts = _query_counts(connection, config)

    comparison = {
        stage: {
            "paper": paper_count,
            "observed": counts.get(stage),
            "difference": (
                counts[stage] - paper_count if stage in counts else None
            ),
        }
        for stage, paper_count in config.paper_counts.items()
    }
    output = {
        "sample": config.name,
        "description": config.description,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit(config.project_root),
        "configuration": {
            "path": str(config.config_path.relative_to(config.project_root)),
            "sha256": file_sha256(config.config_path),
            "resolved": config.resolved,
        },
        "counts": counts,
        "paper_comparison": comparison,
        "software": software_versions("psycopg", "PyYAML"),
    }
    write_manifest(config.report_path, output)
    for stage, count in counts.items():
        report(f"{stage}: {count}")
    report(f"Report: {config.report_path.relative_to(config.project_root)}")


def _query_counts(connection: Any, config: SampleConfig) -> dict[str, int]:
    query, parameters = _count_query(config)
    with connection.cursor() as cursor:
        cursor.execute(query, parameters)
        row = cursor.fetchone()
    names = (
        "matched",
        "complete_photometry",
        "error_qualified",
        "globular_clusters",
        "galaxies",
        "stars",
        "labeled",
    )
    counts = {name: int(value) for name, value in zip(names, row)}
    return {
        "target_records": _catalog_record_count(
            connection, config.target_catalog
        ),
        **counts,
    }


def _count_query(config: SampleConfig) -> tuple[sql.Composed, list[Any]]:
    magnitude_clauses = []
    magnitude_parameters = []
    for item in config.measurements:
        column = _column(item.source, item.magnitude_column)
        clauses = [sql.SQL("{} IS NOT NULL").format(column)]
        clauses.extend(
            sql.SQL("{} <> %s").format(column)
            for _ in item.missing_magnitude_values
        )
        magnitude_clauses.append(_and(clauses))
        magnitude_parameters.extend(item.missing_magnitude_values)
    magnitude_complete = _and(magnitude_clauses)
    error_qualified = _and(
        sql.SQL("{} IS NOT NULL AND {} <= %s").format(
            _column(item.source, item.error_column),
            _column(item.source, item.error_column),
        )
        for item in config.measurements
    )
    error_parameters = [config.max_magnitude_error] * len(config.measurements)
    gc_expression, gc_parameters = _gc_expression(config)
    galaxy_expression, galaxy_parameters = _class_expression(
        config.galaxy, config.extended_class_column
    )
    star_expression, star_parameters = _class_expression(
        config.star, config.extended_class_column
    )
    policy = sql.SQL("reference_rank = 1")
    if config.match_policy == "reciprocal_nearest":
        policy += sql.SQL(" AND target_rank = 1")

    query = sql.SQL(
        """
        WITH candidates AS (
            SELECT m.object_id,
                   m.record_id AS target_record_id,
                   m.angular_sep_arcsec,
                   m.candidate_rank AS target_rank,
                   row_number() OVER (
                       PARTITION BY m.object_id
                       ORDER BY m.angular_sep_arcsec, m.record_id
                   ) AS reference_rank
            FROM core.match AS m
            JOIN core.match_run AS mr USING (match_run_id)
            JOIN core.record AS tr ON tr.record_id = m.record_id
            JOIN core.catalog AS tc ON tc.catalog_id = tr.catalog_id
            WHERE mr.name = %s AND tc.code = %s
        ),
        pairs AS (
            SELECT * FROM candidates WHERE {}
        ),
        measured AS (
            SELECT p.object_id,
                   {},
                   {} AS magnitude_complete,
                   {} AS errors_within_limit,
                   {} AS is_gc,
                   {} AS is_galaxy_candidate,
                   {} AS is_star_candidate
            FROM pairs AS p
            JOIN core.object AS o USING (object_id)
            JOIN core.record AS rr ON rr.record_id = o.origin_record_id
            JOIN core.catalog AS rc ON rc.catalog_id = rr.catalog_id
            JOIN {} AS reference ON reference.ingest_id = rr.raw_ingest_id
            JOIN core.record AS tr ON tr.record_id = p.target_record_id
            JOIN {} AS target ON target.ingest_id = tr.raw_ingest_id
            WHERE rc.code = %s
        ),
        population AS (
            SELECT *,
                   magnitude_complete AND errors_within_limit AS error_qualified
            FROM measured
        )
        SELECT count(*) AS matched,
               count(*) FILTER (WHERE magnitude_complete) AS complete_photometry,
               count(*) FILTER (WHERE error_qualified) AS error_qualified,
               count(*) FILTER (WHERE error_qualified AND is_gc) AS globular_clusters,
               count(*) FILTER (
                   WHERE error_qualified AND NOT is_gc AND is_galaxy_candidate
               ) AS galaxies,
               count(*) FILTER (
                   WHERE error_qualified AND NOT is_gc AND is_star_candidate
               ) AS stars,
               count(*) FILTER (
                   WHERE error_qualified AND (
                       is_gc OR (NOT is_gc AND is_galaxy_candidate)
                       OR (NOT is_gc AND is_star_candidate)
                   )
               ) AS labeled
        FROM population
        """
    ).format(
        policy,
        sql.SQL("p.angular_sep_arcsec"),
        magnitude_complete,
        error_qualified,
        gc_expression,
        galaxy_expression,
        star_expression,
        _table(config.reference_table),
        _table(config.target_table),
    )
    parameters = [
        config.match_run,
        config.target_catalog,
        *magnitude_parameters,
        *error_parameters,
        *gc_parameters,
        *galaxy_parameters,
        *star_parameters,
        config.reference_catalog,
    ]
    return query, parameters


def _catalog_record_count(connection: Any, catalog_code: str) -> int:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT count(*)
            FROM core.record
            JOIN core.catalog USING (catalog_id)
            WHERE code = %s
            """,
            (catalog_code,),
        )
        return int(cursor.fetchone()[0])


def _gc_expression(config: SampleConfig) -> tuple[sql.Composed, list[Any]]:
    master = _table(config.master_table)
    spec = _table(config.spec_table)
    reference_source = sql.SQL("reference.{}").format(
        sql.Identifier(config.reference_source_column)
    )
    expression = sql.SQL(
        """
        EXISTS (
            SELECT 1 FROM {} AS master
            WHERE master.{} = {}
              AND (
                  master.{} = %s
                  OR (
                      master.{} = %s
                      AND master.{} > %s
                  )
              )
        ) OR EXISTS (
            SELECT 1 FROM {} AS spec
            WHERE spec.{} = {}
              AND spec.{} >= %s
              AND spec.{} = ANY(%s)
        )
        """
    ).format(
        master,
        sql.Identifier(config.master_source_column),
        reference_source,
        sql.Identifier(config.master_spectroscopic_column),
        sql.Identifier(config.master_photometric_column),
        sql.Identifier(config.master_probability_column),
        spec,
        sql.Identifier(config.spec_source_column),
        reference_source,
        sql.Identifier(config.spec_snr_column),
        sql.Identifier(config.spec_class_column),
    )
    parameters = [
        config.master_yes_value,
        config.master_yes_value,
        config.master_probability_min,
        config.spec_snr_min,
        list(config.spec_classes),
    ]
    return expression, parameters


def _class_expression(
    rule: ClassRule, extended_class_column: str
) -> tuple[sql.Composed, list[Any]]:
    expression = sql.SQL(
        "target.{} = %s AND target.{} BETWEEN %s AND %s"
    ).format(
        sql.Identifier(extended_class_column),
        sql.Identifier(rule.magnitude_column),
    )
    return expression, [
        rule.extended_class_value,
        rule.magnitude_min,
        rule.magnitude_max,
    ]


def _column(source: str, name: str) -> sql.Composed:
    return sql.SQL("{}.{}").format(sql.Identifier(source), sql.Identifier(name))


def _and(expressions: Any) -> sql.Composed:
    return sql.SQL(" AND ").join(
        sql.SQL("({})").format(expression) for expression in expressions
    )


def _table(name: str) -> sql.Identifier:
    return sql.Identifier(*name.split("."))
