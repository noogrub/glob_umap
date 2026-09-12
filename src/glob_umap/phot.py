from datetime import datetime, timezone
from hashlib import sha256
from math import isfinite
from pathlib import Path
from typing import Any, Callable

from psycopg import sql
from psycopg.types.json import Jsonb

from glob_umap.db import connect
from glob_umap.phot_config import (
    PhotConfig,
    PhotMeasurement,
    PhotSource,
    load_phot_config,
)
from glob_umap.provenance import git_commit, software_versions, write_manifest
from glob_umap.source import file_sha256


def normalize_photometry(
    config_path: str | Path, report: Callable[[str], None]
) -> None:
    config = load_phot_config(config_path)
    with connect() as connection:
        sample_id, member_count = _sample(connection, config.sample_name)
        _require_bindings(connection, sample_id, member_count)
        _require_absent(connection, config, sample_id)
        counts: list[dict[str, Any]] = []
        report(f"Normalizing photometry for {member_count} sample members")
        for source in config.sources:
            for measurement in source.measurements:
                item = _insert_measurement(
                    connection, config, source, measurement, sample_id
                )
                counts.append(item)
                report(
                    f"  {item['catalog']} {item['band']} {item['measure']}: "
                    f"{item['inserted']} rows"
                )
        report("Computing normalized-photometry digest")
        phot_sha256 = _phot_sha256(connection, config, sample_id)
        _record_definition(
            connection, config, sample_id, counts, phot_sha256
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
        "sample": {
            "name": config.sample_name,
            "sample_id": sample_id,
            "members": member_count,
        },
        "reddening": {
            "mode": config.reddening_mode,
            "uncertainty": config.reddening_uncertainty,
        },
        "measurements": counts,
        "photometry_sha256": phot_sha256,
        "software": software_versions("psycopg", "PyYAML"),
    }
    write_manifest(config.report_path, output)
    report(f"Normalized photometry complete: {member_count} sample members")
    report(f"Photometry sha256: {phot_sha256}")
    report(f"Manifest: {config.report_path.relative_to(config.project_root)}")


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


def _require_bindings(connection: Any, sample_id: int, members: int) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT source_role, count(*)
            FROM ml.member_record
            WHERE sample_id = %s
            GROUP BY source_role
            ORDER BY source_role
            """,
            (sample_id,),
        )
        counts = {role: int(count) for role, count in cursor.fetchall()}
    expected = {"reference": members, "target": members}
    if counts != expected:
        raise ValueError(
            "Exact reference/target record bindings are incomplete: "
            f"expected {expected}, found {counts}"
        )


def _require_absent(
    connection: Any, config: PhotConfig, sample_id: int
) -> None:
    clauses: list[sql.Composed] = []
    parameters: list[Any] = [sample_id]
    for source in config.sources:
        clauses.append(sql.SQL("(c.code = %s AND p.measure = %s AND p.dereddened = %s)"))
        parameters.extend(
            [source.catalog, source.measure, config.reddening_mode == "coefficient"]
        )
    predicate = sql.SQL(" OR ").join(clauses)
    query = sql.SQL(
        """
        SELECT count(*)
        FROM core.phot AS p
        JOIN core.record AS r USING (record_id)
        JOIN core.catalog AS c USING (catalog_id)
        JOIN ml.member_record AS mr USING (record_id)
        WHERE mr.sample_id = %s AND ({predicate})
        """
    ).format(predicate=predicate)
    with connection.cursor() as cursor:
        cursor.execute(query, parameters)
        count = int(cursor.fetchone()[0])
    if count:
        raise ValueError(f"Configured photometry already exists: {count} rows")


def _insert_measurement(
    connection: Any,
    config: PhotConfig,
    source: PhotSource,
    measurement: PhotMeasurement,
    sample_id: int,
) -> dict[str, Any]:
    table = sql.Identifier(*source.table.split("."))
    magnitude = sql.Identifier(measurement.magnitude_column)
    error = sql.Identifier(measurement.error_column)
    reddening = sql.Identifier(source.reddening_column)
    missing = list(measurement.missing_magnitude_values)
    corrected = config.reddening_mode == "coefficient"
    coefficient = measurement.extinction_coefficient or 0.0

    invalid_query = sql.SQL(
        """
        SELECT count(*)
        FROM {table} AS source
        JOIN core.record AS r ON r.raw_ingest_id = source.ingest_id
        JOIN core.catalog AS c USING (catalog_id)
        JOIN ml.member_record AS mr USING (record_id)
        WHERE mr.sample_id = %s
          AND mr.source_role = %s
          AND c.code = %s
          AND source.{magnitude} IS NOT NULL
          AND source.{magnitude} <> ALL(%s::double precision[])
          AND (
              source.{error} IS NULL
              OR source.{error} < 0
              OR source.{magnitude} IN (
                  'NaN'::double precision,
                  'Infinity'::double precision,
                  '-Infinity'::double precision
              )
              OR source.{error} IN (
                  'NaN'::double precision,
                  'Infinity'::double precision,
                  '-Infinity'::double precision
              )
              OR (%s AND (
                  source.{reddening} IS NULL
                  OR source.{reddening} IN (
                      'NaN'::double precision,
                      'Infinity'::double precision,
                      '-Infinity'::double precision
                  )
              ))
          )
        """
    ).format(
        table=table,
        magnitude=magnitude,
        error=error,
        reddening=reddening,
    )
    with connection.cursor() as cursor:
        cursor.execute(
            invalid_query,
            (
                sample_id,
                source.source_role,
                source.catalog,
                missing,
                corrected,
            ),
        )
        invalid = int(cursor.fetchone()[0])
    if invalid:
        raise ValueError(
            f"{source.catalog} {measurement.band} contains {invalid} invalid "
            "sample measurements"
        )

    magnitude_expression = sql.SQL("source.{magnitude}").format(magnitude=magnitude)
    if corrected:
        magnitude_expression = sql.SQL(
            "source.{magnitude} - %s * source.{reddening}"
        ).format(magnitude=magnitude, reddening=reddening)

    insert_query = sql.SQL(
        """
        INSERT INTO core.phot (
            record_id, band, measure, mag, mag_err, dereddened, aperture_px
        )
        SELECT r.record_id,
               %s,
               %s,
               {magnitude_expression},
               source.{error},
               %s,
               %s
        FROM {table} AS source
        JOIN core.record AS r ON r.raw_ingest_id = source.ingest_id
        JOIN core.catalog AS c USING (catalog_id)
        JOIN ml.member_record AS mr USING (record_id)
        WHERE mr.sample_id = %s
          AND mr.source_role = %s
          AND c.code = %s
          AND source.{magnitude} IS NOT NULL
          AND source.{magnitude} <> ALL(%s::double precision[])
        ORDER BY r.record_id
        """
    ).format(
        table=table,
        magnitude=magnitude,
        error=error,
        magnitude_expression=magnitude_expression,
    )
    parameters: list[Any] = [
        measurement.band,
        source.measure,
    ]
    if corrected:
        parameters.append(coefficient)
    parameters.extend(
        [
            corrected,
            source.aperture_diameter_px,
            sample_id,
            source.source_role,
            source.catalog,
            missing,
        ]
    )
    with connection.cursor() as cursor:
        cursor.execute(insert_query, parameters)
        inserted = int(cursor.rowcount)

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT count(*)
            FROM ml.member_record
            WHERE sample_id = %s AND source_role = %s
            """,
            (sample_id, source.source_role),
        )
        eligible = int(cursor.fetchone()[0])
    return {
        "catalog": source.catalog,
        "source_role": source.source_role,
        "band": measurement.band,
        "measure": source.measure,
        "dereddened": corrected,
        "aperture_diameter_px": source.aperture_diameter_px,
        "eligible_records": eligible,
        "inserted": inserted,
        "missing_or_sentinel": eligible - inserted,
        "extinction_coefficient": measurement.extinction_coefficient,
    }


def _phot_sha256(connection: Any, config: PhotConfig, sample_id: int) -> str:
    identities = [
        (source.catalog, source.measure, config.reddening_mode == "coefficient")
        for source in config.sources
    ]
    clauses = [
        "(c.code = %s AND p.measure = %s AND p.dereddened = %s)"
        for _ in identities
    ]
    parameters: list[Any] = [sample_id]
    for identity in identities:
        parameters.extend(identity)
    query = """
        SELECT c.code,
               r.source_key::jsonb ->> 1 AS source_row,
               p.band,
               p.measure,
               p.dereddened,
               p.mag,
               p.mag_err,
               p.aperture_px
        FROM core.phot AS p
        JOIN core.record AS r USING (record_id)
        JOIN core.catalog AS c USING (catalog_id)
        JOIN ml.member_record AS mr USING (record_id)
        WHERE mr.sample_id = %s AND (
    """ + " OR ".join(clauses) + ") ORDER BY c.code, source_row::bigint, p.band, p.measure"
    digest = sha256()
    with connection.cursor() as cursor:
        cursor.execute(query, parameters)
        for row in cursor:
            encoded: list[str] = []
            for value in row:
                if isinstance(value, float):
                    if not isfinite(value):
                        raise ValueError("Normalized photometry contains a nonfinite value")
                    encoded.append(value.hex())
                else:
                    encoded.append("" if value is None else str(value))
            digest.update("\t".join(encoded).encode("ascii"))
            digest.update(b"\n")
    return digest.hexdigest()


def _record_definition(
    connection: Any,
    config: PhotConfig,
    sample_id: int,
    counts: list[dict[str, Any]],
    phot_sha256: str,
) -> None:
    definition = {
        "configuration": {
            "path": str(config.config_path.relative_to(config.project_root)),
            "sha256": file_sha256(config.config_path),
            "resolved": config.resolved,
        },
        "measurements": counts,
        "photometry_sha256": phot_sha256,
    }
    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE ml.sample
            SET definition = jsonb_set(definition, '{photometry}', %s, true)
            WHERE sample_id = %s
              AND NOT definition ? 'photometry'
            """,
            (Jsonb(definition), sample_id),
        )
        if cursor.rowcount != 1:
            raise ValueError("Sample definition already contains photometry")
