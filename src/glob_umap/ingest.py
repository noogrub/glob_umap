from pathlib import Path
from typing import Callable

from glob_umap.check import check_dataset
from glob_umap.db import (
    connect,
    copy_rows,
    ensure_catalog_codes_available,
    ensure_empty,
    register_catalog,
    validate_columns,
)
from glob_umap.provenance import build_manifest, write_manifest
from glob_umap.source import rows, target_columns


def ingest(config_path: str | Path, report: Callable[[str], None]) -> None:
    config, checks = check_dataset(config_path)

    with connect() as connection:
        for source in config.sources:
            columns = target_columns(source)
            validate_columns(connection, source["table"], columns)
            ensure_empty(connection, source["table"])
        ensure_catalog_codes_available(connection, config.sources)

        for source, check in zip(config.sources, checks, strict=True):
            columns = target_columns(source)
            report(
                f"Loading {source['name']} into {source['table']} "
                f"({check.row_count} rows)"
            )
            loaded = copy_rows(
                connection,
                source["table"],
                Path(source["path"]),
                columns,
                rows(config.project_root, source),
                config.progress_interval_seconds,
                lambda count, name=source["name"]: report(
                    f"  {name}: {count} rows"
                ),
            )
            if loaded != check.row_count:
                raise RuntimeError(
                    f"Loaded-row mismatch for {source['name']}: "
                    f"expected {check.row_count}, loaded {loaded}"
                )
            register_catalog(connection, source, loaded)
            report(f"Loaded {source['name']}: {loaded} rows")

    manifest = build_manifest(config, checks)
    write_manifest(config.manifest_path, manifest)
    total = sum(check.row_count for check in checks)
    report(f"Ingestion complete: {total} rows across {len(checks)} catalogues")
    report(f"Manifest: {config.manifest_path.relative_to(config.project_root)}")
