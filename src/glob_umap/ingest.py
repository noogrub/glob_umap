from pathlib import Path

from glob_umap.check import check_dataset
from glob_umap.db import (
    connect,
    copy_rows,
    ensure_empty,
    register_catalog,
    validate_columns,
)
from glob_umap.provenance import build_manifest, write_manifest
from glob_umap.source import rows, target_columns


def ingest(config_path: str | Path) -> None:
    config, checks = check_dataset(config_path)

    with connect() as connection:
        for source, check in zip(config.sources, checks, strict=True):
            columns = target_columns(source)
            validate_columns(connection, source["table"], columns)
            ensure_empty(connection, source["table"])
            loaded = copy_rows(
                connection,
                source["table"],
                Path(source["path"]),
                columns,
                rows(config.project_root, source),
            )
            if loaded != check.row_count:
                raise RuntimeError(
                    f"Loaded-row mismatch for {source['name']}: "
                    f"expected {check.row_count}, loaded {loaded}"
                )
            register_catalog(connection, source, loaded)

    manifest = build_manifest(config.name, config.project_root, checks)
    write_manifest(config.manifest_path, manifest)
