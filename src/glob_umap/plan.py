from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from glob_umap.db import connect
from glob_umap.experiment_config import load_experiment_config
from glob_umap.provenance import git_commit, software_versions, write_manifest
from glob_umap.source import file_sha256


def freeze_plan(config_path: str | Path, report: Callable[[str], None]) -> None:
    config = load_experiment_config(config_path)
    with connect() as connection:
        sample = _sample_contract(connection, config.sample_name)
        features = _feature_contract(connection, config.feature_set_name)
        if features["sample_id"] != sample["sample_id"]:
            raise ValueError("Feature set belongs to a different sample")
        population = _population_contract(
            connection,
            sample["sample_id"],
            config.classes,
            config.development_split,
            config.final_test_split,
        )

    output = {
        "stage": config.name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit(config.project_root),
        "configuration": {
            "experiment": _config_file(config.config_path, config.project_root),
            "features": _config_file(
                config.features.config_path, config.project_root
            ),
            "resolved": config.resolved,
        },
        "sample": sample,
        "feature_set": features,
        "population": population,
        "test_lock": {
            "split": config.final_test_split,
            "policy": config.final_test_policy,
            "threshold_source": config.threshold_source,
            "threshold_application": config.threshold_application,
        },
        "software": software_versions("psycopg", "PyYAML"),
    }
    write_manifest(config.report_path, output)
    report(f"Frozen evaluation plan: {config.name}")
    report(
        f"  development={population['development_members']}, "
        f"final_test={population['final_test_members']}"
    )
    report(f"  feature sha256={features['feature_sha256']}")
    report(f"Manifest: {config.report_path.relative_to(config.project_root)}")


def _sample_contract(connection: Any, name: str) -> dict[str, Any]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT sample_id,
                   config_sha256,
                   definition #>> '{split,assignment_sha256}' AS split_sha256,
                   definition #>> '{records,binding_sha256}' AS binding_sha256,
                   definition #>> '{photometry,photometry_sha256}' AS photometry_sha256
            FROM ml.sample
            WHERE name = %s
            """,
            (name,),
        )
        row = cursor.fetchone()
    if row is None:
        raise ValueError(f"Materialized sample does not exist: {name}")
    missing = [
        label
        for label, value in zip(
            ("split", "record binding", "photometry"), row[2:], strict=True
        )
        if value is None
    ]
    if missing:
        raise ValueError(f"Sample provenance is incomplete: {', '.join(missing)}")
    return {
        "name": name,
        "sample_id": int(row[0]),
        "config_sha256": row[1],
        "split_sha256": row[2],
        "binding_sha256": row[3],
        "photometry_sha256": row[4],
    }


def _feature_contract(connection: Any, name: str) -> dict[str, Any]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT feature_set_id, sample_id, config_sha256, feature_sha256
            FROM ml.feature_set
            WHERE name = %s
            """,
            (name,),
        )
        row = cursor.fetchone()
    if row is None:
        raise ValueError(f"Feature set does not exist: {name}")
    if row[3] is None:
        raise ValueError(f"Feature set is incomplete: {name}")
    return {
        "name": name,
        "feature_set_id": int(row[0]),
        "sample_id": int(row[1]),
        "config_sha256": row[2],
        "feature_sha256": row[3],
    }


def _population_contract(
    connection: Any,
    sample_id: int,
    classes: tuple[str, ...],
    development_split: str,
    final_test_split: str,
) -> dict[str, Any]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT split, target_class, count(*)
            FROM ml.member
            WHERE sample_id = %s
            GROUP BY split, target_class
            ORDER BY split, target_class
            """,
            (sample_id,),
        )
        rows = cursor.fetchall()
    observed_splits = {row[0] for row in rows}
    if observed_splits != {development_split, final_test_split}:
        raise ValueError(
            f"Sample splits are {sorted(observed_splits)}; expected "
            f"{sorted({development_split, final_test_split})}"
        )
    for split in (development_split, final_test_split):
        observed_classes = {row[1] for row in rows if row[0] == split}
        if observed_classes != set(classes):
            raise ValueError(
                f"Split {split} classes are {sorted(observed_classes)}; "
                f"expected {sorted(classes)}"
            )
    counts = [
        {"split": row[0], "target_class": row[1], "members": int(row[2])}
        for row in rows
    ]
    return {
        "counts": counts,
        "development_members": sum(
            item["members"] for item in counts if item["split"] == development_split
        ),
        "final_test_members": sum(
            item["members"] for item in counts if item["split"] == final_test_split
        ),
    }


def _config_file(path: Path, root: Path) -> dict[str, str]:
    return {
        "path": str(path.relative_to(root)),
        "sha256": file_sha256(path),
    }
