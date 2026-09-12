from datetime import datetime, timezone
from hashlib import sha256
from math import isfinite
from pathlib import Path
from typing import Any, Callable

import numpy as np
from psycopg.types.json import Jsonb

from glob_umap.db import connect
from glob_umap.feature_config import BandSource, FeatureConfig, load_feature_config
from glob_umap.provenance import git_commit, software_versions, write_manifest
from glob_umap.source import file_sha256


def build_features(
    config_path: str | Path, report: Callable[[str], None]
) -> None:
    config = load_feature_config(config_path)
    with connect() as connection:
        _require_table(connection)
        sample_id, member_count = _sample(connection, config.sample_name)
        dependency = _photometry_dependency(connection, sample_id)
        feature_set_id = _create_feature_set(
            connection, config, sample_id, dependency
        )
        counts: dict[str, int] = {}
        report(
            f"Materializing {len(config.bands)} magnitudes for "
            f"{member_count} sample members"
        )
        for band in config.bands:
            name = f"{config.magnitude_prefix}{band.band}"
            counts[name] = _insert_magnitude(
                connection, feature_set_id, sample_id, name, band
            )
        by_band = {item.band: item for item in config.bands}
        report(f"Materializing {len(config.color_pairs)} pairwise colors")
        for left, right in config.color_pairs:
            name = f"{left}{config.color_separator}{right}"
            counts[name] = _insert_color(
                connection,
                feature_set_id,
                sample_id,
                name,
                by_band[left],
                by_band[right],
            )
        incomplete = {
            name: count for name, count in counts.items() if count != member_count
        }
        if incomplete:
            raise RuntimeError(
                f"Feature rows do not cover all {member_count} members: {incomplete}"
            )

        report("Auditing feature coverage, identities, and numerical rank")
        audit = _audit_features(
            connection, config, feature_set_id, sample_id, member_count
        )
        report("Computing feature-set digest")
        feature_sha256 = _feature_sha256(
            connection, feature_set_id, sample_id
        )
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE ml.feature_set
                SET feature_sha256 = %s,
                    definition = jsonb_set(definition, '{audit}', %s, true)
                WHERE feature_set_id = %s
                  AND feature_sha256 IS NULL
                """,
                (feature_sha256, Jsonb(audit), feature_set_id),
            )
            if cursor.rowcount != 1:
                raise RuntimeError("Feature-set provenance update failed")

    output = {
        "stage": config.name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit(config.project_root),
        "configuration": {
            "features": _config_file(config.config_path, config.project_root),
            "photometry": _config_file(
                config.photometry.config_path, config.project_root
            ),
            "resolved": config.resolved,
        },
        "sample": {
            "name": config.sample_name,
            "sample_id": sample_id,
            "members": member_count,
        },
        "feature_set_id": feature_set_id,
        "feature_counts": counts,
        "groups": {name: list(values) for name, values in config.groups.items()},
        "audit": audit,
        "feature_sha256": feature_sha256,
        "photometry_dependency": dependency,
        "software": software_versions("numpy", "psycopg", "PyYAML"),
    }
    write_manifest(config.report_path, output)
    report(f"Materialized feature set {config.name}: {member_count} members")
    report(
        f"  {len(config.groups['magnitudes'])} magnitudes, "
        f"{len(config.groups['all_colors'])} colors"
    )
    report(
        f"  color rank={audit['color_matrix']['numerical_rank']}, "
        f"maximum identity residual="
        f"{audit['color_matrix']['maximum_identity_residual']:.3e}"
    )
    report(f"Feature sha256: {feature_sha256}")
    report(f"Manifest: {config.report_path.relative_to(config.project_root)}")


def _require_table(connection: Any) -> None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT to_regclass('ml.feature_set')")
        present = cursor.fetchone()[0]
    if present is None:
        raise ValueError("Apply sql/42_feature.sql before building features")


def _sample(connection: Any, name: str) -> tuple[int, int]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT s.sample_id, count(m.object_id)
            FROM ml.sample AS s
            LEFT JOIN ml.member AS m USING (sample_id)
            WHERE s.name = %s
            GROUP BY s.sample_id
            """,
            (name,),
        )
        row = cursor.fetchone()
    if row is None:
        raise ValueError(f"Materialized sample does not exist: {name}")
    if int(row[1]) == 0:
        raise ValueError(f"Materialized sample has no members: {name}")
    return int(row[0]), int(row[1])


def _photometry_dependency(connection: Any, sample_id: int) -> dict[str, Any]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT definition -> 'photometry'
            FROM ml.sample
            WHERE sample_id = %s
            """,
            (sample_id,),
        )
        row = cursor.fetchone()
    if row is None or row[0] is None:
        raise ValueError("Sample has no recorded photometry normalization")
    return dict(row[0])


def _create_feature_set(
    connection: Any,
    config: FeatureConfig,
    sample_id: int,
    dependency: dict[str, Any],
) -> int:
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM ml.feature_set WHERE name = %s", (config.name,))
        if cursor.fetchone() is not None:
            raise ValueError(f"Feature set already exists: {config.name}")
        cursor.execute(
            """
            INSERT INTO ml.feature_set (
                sample_id, name, config_path, config_sha256, definition
            ) VALUES (%s, %s, %s, %s, %s)
            RETURNING feature_set_id
            """,
            (
                sample_id,
                config.name,
                str(config.config_path.relative_to(config.project_root)),
                file_sha256(config.config_path),
                Jsonb(
                    {
                        "configuration": config.resolved,
                        "photometry": dependency,
                    }
                ),
            ),
        )
        return int(cursor.fetchone()[0])


def _insert_magnitude(
    connection: Any,
    feature_set_id: int,
    sample_id: int,
    name: str,
    band: BandSource,
) -> int:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO ml.feature (
                feature_set_id, object_id, name, value, uncertainty
            )
            SELECT %s, m.object_id, %s, p.mag, p.mag_err
            FROM ml.member AS m
            JOIN ml.member_record AS mr
              ON mr.sample_id = m.sample_id
             AND mr.object_id = m.object_id
             AND mr.source_role = %s
            JOIN core.phot AS p
              ON p.record_id = mr.record_id
             AND p.band = %s
             AND p.measure = %s
             AND p.dereddened = %s
            WHERE m.sample_id = %s
            ORDER BY m.object_id
            """,
            (
                feature_set_id,
                name,
                band.source_role,
                band.band,
                band.measure,
                band.dereddened,
                sample_id,
            ),
        )
        return int(cursor.rowcount)


def _insert_color(
    connection: Any,
    feature_set_id: int,
    sample_id: int,
    name: str,
    left: BandSource,
    right: BandSource,
) -> int:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            WITH left_band AS (
                SELECT m.object_id, p.mag, p.mag_err
                FROM ml.member AS m
                JOIN ml.member_record AS mr
                  ON mr.sample_id = m.sample_id
                 AND mr.object_id = m.object_id
                 AND mr.source_role = %s
                JOIN core.phot AS p
                  ON p.record_id = mr.record_id
                 AND p.band = %s
                 AND p.measure = %s
                 AND p.dereddened = %s
                WHERE m.sample_id = %s
            ), right_band AS (
                SELECT m.object_id, p.mag, p.mag_err
                FROM ml.member AS m
                JOIN ml.member_record AS mr
                  ON mr.sample_id = m.sample_id
                 AND mr.object_id = m.object_id
                 AND mr.source_role = %s
                JOIN core.phot AS p
                  ON p.record_id = mr.record_id
                 AND p.band = %s
                 AND p.measure = %s
                 AND p.dereddened = %s
                WHERE m.sample_id = %s
            )
            INSERT INTO ml.feature (
                feature_set_id, object_id, name, value, uncertainty
            )
            SELECT %s,
                   left_band.object_id,
                   %s,
                   left_band.mag - right_band.mag,
                   sqrt(
                       left_band.mag_err * left_band.mag_err
                       + right_band.mag_err * right_band.mag_err
                   )
            FROM left_band
            JOIN right_band USING (object_id)
            ORDER BY left_band.object_id
            """,
            (
                left.source_role,
                left.band,
                left.measure,
                left.dereddened,
                sample_id,
                right.source_role,
                right.band,
                right.measure,
                right.dereddened,
                sample_id,
                feature_set_id,
                name,
            ),
        )
        return int(cursor.rowcount)


def _audit_features(
    connection: Any,
    config: FeatureConfig,
    feature_set_id: int,
    sample_id: int,
    member_count: int,
) -> dict[str, Any]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT f.name,
                   count(*),
                   min(f.value),
                   max(f.value),
                   avg(f.value),
                   stddev_pop(f.value),
                   min(f.uncertainty),
                   max(f.uncertainty)
            FROM ml.feature AS f
            WHERE f.feature_set_id = %s
            GROUP BY f.name
            ORDER BY f.name
            """,
            (feature_set_id,),
        )
        statistics = [
            {
                "name": row[0],
                "count": int(row[1]),
                "minimum": float(row[2]),
                "maximum": float(row[3]),
                "mean": float(row[4]),
                "standard_deviation": float(row[5]),
                "minimum_uncertainty": float(row[6]),
                "maximum_uncertainty": float(row[7]),
            }
            for row in cursor.fetchall()
        ]
        cursor.execute(
            """
            SELECT m.split, m.target_class, count(*)
            FROM ml.member AS m
            WHERE m.sample_id = %s
            GROUP BY m.split, m.target_class
            ORDER BY m.split, m.target_class
            """,
            (sample_id,),
        )
        population = [
            {"split": row[0], "target_class": row[1], "members": int(row[2])}
            for row in cursor.fetchall()
        ]
        cursor.execute(
            """
            SELECT f.object_id,
                   array_agg(
                       f.value
                       ORDER BY array_position(%s::text[], f.name)
                   )
            FROM ml.feature AS f
            WHERE f.feature_set_id = %s
              AND f.name = ANY(%s::text[])
            GROUP BY f.object_id
            HAVING count(*) = %s
            ORDER BY f.object_id
            """,
            (
                list(config.color_names),
                feature_set_id,
                list(config.color_names),
                len(config.color_names),
            ),
        )
        matrix_rows = cursor.fetchall()
    if len(matrix_rows) != member_count:
        raise RuntimeError(
            f"Color audit found {len(matrix_rows)} complete rows; expected {member_count}"
        )
    matrix = np.asarray([row[1] for row in matrix_rows], dtype=np.float64)
    if not np.isfinite(matrix).all():
        raise ValueError("Feature matrix contains nonfinite values")
    centered = matrix - matrix.mean(axis=0)
    singular_values = np.linalg.svd(centered, compute_uv=False)
    rank_tolerance = max(centered.shape) * np.finfo(np.float64).eps * singular_values[0]
    numerical_rank = int(np.sum(singular_values > rank_tolerance))
    if numerical_rank != config.expected_color_rank:
        raise RuntimeError(
            f"Color matrix rank is {numerical_rank}; expected "
            f"{config.expected_color_rank}"
        )

    index = {name: position for position, name in enumerate(config.color_names)}
    adjacent_names = config.groups["adjacent_colors"]
    maximum_residual = 0.0
    for left_index, left in enumerate(config.color_order):
        for right_index in range(left_index + 1, len(config.color_order)):
            right = config.color_order[right_index]
            name = f"{left}{config.color_separator}{right}"
            expected = np.zeros(member_count, dtype=np.float64)
            for position in range(left_index, right_index):
                adjacent_name = adjacent_names[position]
                expected += matrix[:, index[adjacent_name]]
            residual = float(np.max(np.abs(matrix[:, index[name]] - expected)))
            maximum_residual = max(maximum_residual, residual)
    if maximum_residual > config.algebraic_tolerance:
        raise RuntimeError(
            f"Color identity residual {maximum_residual} exceeds configured "
            f"tolerance {config.algebraic_tolerance}"
        )

    return {
        "population": population,
        "statistics": statistics,
        "color_matrix": {
            "rows": member_count,
            "columns": len(config.color_names),
            "expected_rank": config.expected_color_rank,
            "numerical_rank": numerical_rank,
            "rank_tolerance": float(rank_tolerance),
            "singular_values": [float(value) for value in singular_values],
            "algebraic_tolerance": config.algebraic_tolerance,
            "maximum_identity_residual": maximum_residual,
        },
        "uncertainty_model": config.color_uncertainty,
    }


def _feature_sha256(
    connection: Any, feature_set_id: int, sample_id: int
) -> str:
    digest = sha256()
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT catalog.code,
                   origin.source_key::jsonb ->> 1 AS source_row,
                   m.split,
                   m.target_class,
                   f.name,
                   f.value,
                   f.uncertainty
            FROM ml.feature AS f
            JOIN ml.member AS m
              ON m.sample_id = %s
             AND m.object_id = f.object_id
            JOIN core.object AS o USING (object_id)
            JOIN core.record AS origin
              ON origin.record_id = o.origin_record_id
            JOIN core.catalog AS catalog
              ON catalog.catalog_id = origin.catalog_id
            WHERE f.feature_set_id = %s
            ORDER BY catalog.code,
                     (origin.source_key::jsonb ->> 1)::bigint,
                     f.name
            """,
            (sample_id, feature_set_id),
        )
        for row in cursor:
            values: list[str] = []
            for value in row:
                if isinstance(value, float):
                    if not isfinite(value):
                        raise ValueError("Feature digest encountered a nonfinite value")
                    values.append(value.hex())
                else:
                    values.append("" if value is None else str(value))
            digest.update("\t".join(values).encode("ascii"))
            digest.update(b"\n")
    return digest.hexdigest()


def _config_file(path: Path, root: Path) -> dict[str, str]:
    return {
        "path": str(path.relative_to(root)),
        "sha256": file_sha256(path),
    }
