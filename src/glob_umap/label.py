from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from psycopg import sql

from glob_umap.db import connect, ensure_empty
from glob_umap.label_config import LabelConfig, load_label_config
from glob_umap.provenance import git_commit, software_versions, write_manifest
from glob_umap.sample_config import ClassRule, SampleConfig
from glob_umap.source import file_sha256


def populate_labels(config_path: str | Path, report: Callable[[str], None]) -> None:
    config = load_label_config(config_path)
    sample = config.materialization.sample
    with connect() as connection:
        _require_unique_index(connection)
        ensure_empty(connection, "core.label")
        sample_id = _sample_id(connection, sample.name)
        inputs = _catalogue_contracts(connection, config)

        inserted = {
            config.master_photometric_evidence: _insert_master_photometric(
                connection, config
            ),
            config.master_spectroscopic_evidence: _insert_master_spectroscopic(
                connection, config
            ),
            config.spec_spectroscopic_evidence: _insert_spec_spectroscopic(
                connection, config
            ),
            f"{config.des_morphology_evidence}:galaxy": _insert_des_class(
                connection,
                config,
                sample.galaxy,
                config.materialization.galaxy_target_class,
            ),
            f"{config.des_morphology_evidence}:star": _insert_des_class(
                connection,
                config,
                sample.star,
                config.materialization.star_target_class,
            ),
        }
        support = _sample_support(connection, sample_id)
        unsupported = sum(item["unsupported"] for item in support)
        if unsupported:
            raise RuntimeError(
                f"Normalized evidence does not support {unsupported} sample members"
            )
        summary = _evidence_summary(connection)

    output = {
        "stage": config.name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit(config.project_root),
        "configuration": {
            "labels": _config_file(config.config_path, config.project_root),
            "materialization": _config_file(
                config.materialization.config_path, config.project_root
            ),
            "sample": _config_file(sample.config_path, config.project_root),
            "resolved": config.resolved,
        },
        "inputs": inputs,
        "inserted": inserted,
        "total_evidence_rows": sum(inserted.values()),
        "evidence_summary": summary,
        "sample": {"name": sample.name, "sample_id": sample_id},
        "sample_support": support,
        "software": software_versions("psycopg", "PyYAML"),
    }
    write_manifest(config.report_path, output)
    report(f"Normalized label evidence: {output['total_evidence_rows']} rows")
    for name, count in inserted.items():
        report(f"  {name}: {count}")
    report(f"Verified evidence for all sample members: {sample.name}")
    report(f"Manifest: {config.report_path.relative_to(config.project_root)}")


def _insert_master_photometric(connection: Any, config: LabelConfig) -> int:
    sample = config.materialization.sample
    query = sql.SQL(
        """
        INSERT INTO core.label (
            object_id, record_id, class, evidence, provenance, confidence, details
        )
        SELECT o.object_id, lr.record_id, %s, %s, %s, master.{probability},
               jsonb_build_object(
                   'source_id', master.{master_source},
                   'photometric_flag', master.{photometric_flag},
                   'spectroscopic_flag', master.{spectroscopic_flag}
               )
        FROM {master_table} AS master
        JOIN core.record AS lr ON lr.raw_ingest_id = master.ingest_id
        JOIN core.catalog AS lc ON lc.catalog_id = lr.catalog_id
        JOIN {reference_table} AS reference
          ON reference.{reference_source} = master.{master_source}
        JOIN core.record AS rr ON rr.raw_ingest_id = reference.ingest_id
        JOIN core.catalog AS rc ON rc.catalog_id = rr.catalog_id
        JOIN core.object AS o ON o.origin_record_id = rr.record_id
        WHERE lc.code = %s
          AND rc.code = %s
          AND master.{photometric_flag} = %s
          AND master.{probability} > %s
        ORDER BY o.object_id, lr.record_id
        """
    ).format(
        probability=sql.Identifier(sample.master_probability_column),
        master_source=sql.Identifier(sample.master_source_column),
        photometric_flag=sql.Identifier(sample.master_photometric_column),
        spectroscopic_flag=sql.Identifier(sample.master_spectroscopic_column),
        master_table=_table(sample.master_table),
        reference_table=_table(sample.reference_table),
        reference_source=sql.Identifier(sample.reference_source_column),
    )
    return _execute_insert(
        connection,
        query,
        (
            config.materialization.gc_target_class,
            config.master_photometric_evidence,
            config.master_provenance,
            config.master_catalog,
            sample.reference_catalog,
            sample.master_yes_value,
            sample.master_probability_min,
        ),
    )


def _insert_master_spectroscopic(connection: Any, config: LabelConfig) -> int:
    sample = config.materialization.sample
    query = sql.SQL(
        """
        INSERT INTO core.label (
            object_id, record_id, class, evidence, provenance, confidence, details
        )
        SELECT o.object_id, lr.record_id, %s, %s, %s, NULL,
               jsonb_build_object(
                   'source_id', master.{master_source},
                   'photometric_flag', master.{photometric_flag},
                   'spectroscopic_flag', master.{spectroscopic_flag}
               )
        FROM {master_table} AS master
        JOIN core.record AS lr ON lr.raw_ingest_id = master.ingest_id
        JOIN core.catalog AS lc ON lc.catalog_id = lr.catalog_id
        JOIN {reference_table} AS reference
          ON reference.{reference_source} = master.{master_source}
        JOIN core.record AS rr ON rr.raw_ingest_id = reference.ingest_id
        JOIN core.catalog AS rc ON rc.catalog_id = rr.catalog_id
        JOIN core.object AS o ON o.origin_record_id = rr.record_id
        WHERE lc.code = %s
          AND rc.code = %s
          AND master.{spectroscopic_flag} = %s
        ORDER BY o.object_id, lr.record_id
        """
    ).format(
        master_source=sql.Identifier(sample.master_source_column),
        photometric_flag=sql.Identifier(sample.master_photometric_column),
        spectroscopic_flag=sql.Identifier(sample.master_spectroscopic_column),
        master_table=_table(sample.master_table),
        reference_table=_table(sample.reference_table),
        reference_source=sql.Identifier(sample.reference_source_column),
    )
    return _execute_insert(
        connection,
        query,
        (
            config.materialization.gc_target_class,
            config.master_spectroscopic_evidence,
            config.master_provenance,
            config.master_catalog,
            sample.reference_catalog,
            sample.master_yes_value,
        ),
    )


def _insert_spec_spectroscopic(connection: Any, config: LabelConfig) -> int:
    sample = config.materialization.sample
    query = sql.SQL(
        """
        INSERT INTO core.label (
            object_id, record_id, class, evidence, provenance, confidence, details
        )
        SELECT o.object_id, lr.record_id, %s, %s, %s, NULL,
               jsonb_build_object(
                   'fds_id', spec.{spec_source},
                   'class', spec.{spec_class},
                   'signal_to_noise', spec.{spec_snr}
               )
        FROM {spec_table} AS spec
        JOIN core.record AS lr ON lr.raw_ingest_id = spec.ingest_id
        JOIN core.catalog AS lc ON lc.catalog_id = lr.catalog_id
        JOIN {reference_table} AS reference
          ON reference.{reference_source} = spec.{spec_source}
        JOIN core.record AS rr ON rr.raw_ingest_id = reference.ingest_id
        JOIN core.catalog AS rc ON rc.catalog_id = rr.catalog_id
        JOIN core.object AS o ON o.origin_record_id = rr.record_id
        WHERE lc.code = %s
          AND rc.code = %s
          AND spec.{spec_snr} >= %s
          AND spec.{spec_class} = ANY(%s)
        ORDER BY o.object_id, lr.record_id
        """
    ).format(
        spec_source=sql.Identifier(sample.spec_source_column),
        spec_class=sql.Identifier(sample.spec_class_column),
        spec_snr=sql.Identifier(sample.spec_snr_column),
        spec_table=_table(sample.spec_table),
        reference_table=_table(sample.reference_table),
        reference_source=sql.Identifier(sample.reference_source_column),
    )
    return _execute_insert(
        connection,
        query,
        (
            config.materialization.gc_target_class,
            config.spec_spectroscopic_evidence,
            config.spec_provenance,
            config.spec_catalog,
            sample.reference_catalog,
            sample.spec_snr_min,
            list(sample.spec_classes),
        ),
    )


def _insert_des_class(
    connection: Any,
    config: LabelConfig,
    rule: ClassRule,
    target_class: str,
) -> int:
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
                   ) AS reference_rank,
                   m.angular_sep_arcsec
            FROM core.match AS m
            JOIN core.match_run AS mr
              ON mr.match_run_id = m.match_run_id
            JOIN core.record AS tr ON tr.record_id = m.record_id
            JOIN core.catalog AS tc ON tc.catalog_id = tr.catalog_id
            WHERE mr.name = %s AND tc.code = %s
        ), pairs AS (
            SELECT * FROM candidates WHERE {policy}
        )
        INSERT INTO core.label (
            object_id, record_id, class, evidence, provenance, confidence, details
        )
        SELECT p.object_id, p.record_id, %s, %s, %s, NULL,
               jsonb_build_object(
                   'extended_class', target.{extended_class},
                   'magnitude', target.{magnitude},
                   'match_run', %s::text,
                   'match_policy', %s::text,
                   'angular_sep_arcsec', p.angular_sep_arcsec
               )
        FROM pairs AS p
        JOIN core.record AS tr ON tr.record_id = p.record_id
        JOIN {target_table} AS target ON target.ingest_id = tr.raw_ingest_id
        WHERE target.{extended_class} = %s
          AND target.{magnitude} BETWEEN %s AND %s
        ORDER BY p.object_id, p.record_id
        """
    ).format(
        policy=policy,
        extended_class=sql.Identifier(sample.extended_class_column),
        magnitude=sql.Identifier(rule.magnitude_column),
        target_table=_table(sample.target_table),
    )
    return _execute_insert(
        connection,
        query,
        (
            sample.match_run,
            sample.target_catalog,
            target_class,
            config.des_morphology_evidence,
            config.des_provenance,
            sample.match_run,
            sample.match_policy,
            rule.extended_class_value,
            rule.magnitude_min,
            rule.magnitude_max,
        ),
    )


def _execute_insert(connection: Any, query: Any, parameters: tuple[Any, ...]) -> int:
    with connection.cursor() as cursor:
        cursor.execute(query, parameters)
        return int(cursor.rowcount)


def _sample_id(connection: Any, name: str) -> int:
    with connection.cursor() as cursor:
        cursor.execute("SELECT sample_id FROM ml.sample WHERE name = %s", (name,))
        row = cursor.fetchone()
    if row is None:
        raise ValueError(f"Materialized sample does not exist: {name}")
    return int(row[0])


def _sample_support(connection: Any, sample_id: int) -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT m.target_class,
                   count(*) AS members,
                   count(*) FILTER (WHERE EXISTS (
                       SELECT 1 FROM core.label AS l
                       WHERE l.object_id = m.object_id
                         AND l.class = m.target_class
                   )) AS supported
            FROM ml.member AS m
            WHERE m.sample_id = %s
            GROUP BY m.target_class
            ORDER BY m.target_class
            """,
            (sample_id,),
        )
        rows = cursor.fetchall()
    return [
        {
            "target_class": row[0],
            "members": int(row[1]),
            "supported": int(row[2]),
            "unsupported": int(row[1] - row[2]),
        }
        for row in rows
    ]


def _evidence_summary(connection: Any) -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT class, evidence, provenance,
                   count(*) AS evidence_rows,
                   count(DISTINCT object_id) AS objects
            FROM core.label
            GROUP BY class, evidence, provenance
            ORDER BY class, evidence, provenance
            """
        )
        rows = cursor.fetchall()
    return [
        {
            "class": row[0],
            "evidence": row[1],
            "provenance": row[2],
            "evidence_rows": int(row[3]),
            "objects": int(row[4]),
        }
        for row in rows
    ]


def _catalogue_contracts(
    connection: Any, config: LabelConfig
) -> list[dict[str, Any]]:
    sample = config.materialization.sample
    codes = sorted(
        {
            sample.reference_catalog,
            sample.target_catalog,
            config.master_catalog,
            config.spec_catalog,
        }
    )
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
        raise ValueError("Not all label-source catalogues are registered")
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


def _require_unique_index(connection: Any) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT 1 FROM pg_indexes
            WHERE schemaname = 'core'
              AND tablename = 'label'
              AND indexname = 'label_source_evidence_idx'
            """
        )
        if cursor.fetchone() is None:
            raise ValueError("Apply sql/32_label_evidence.sql before labels")


def _config_file(path: Path, root: Path) -> dict[str, str]:
    return {
        "path": str(path.relative_to(root)),
        "sha256": file_sha256(path),
    }


def _table(name: str) -> sql.Identifier:
    return sql.Identifier(*name.split("."))
