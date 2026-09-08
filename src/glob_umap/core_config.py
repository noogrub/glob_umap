from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class RecordSource:
    catalog_code: str
    raw_table: str
    raw_ingest_column: str
    key_columns: tuple[str, ...]
    ra_column: str
    dec_column: str


@dataclass(frozen=True)
class RecordConfig:
    name: str
    project_root: Path
    config_path: Path
    on_existing: str
    manifest_path: Path
    sources: tuple[RecordSource, ...]
    resolved: dict[str, Any]


@dataclass(frozen=True)
class MatchConfig:
    name: str
    project_root: Path
    config_path: Path
    method: str
    reference_catalog: str
    target_catalog: str
    search_radius_arcsec: float
    selection: str
    on_existing: str
    chunk_rows: int
    workers: int
    progress_interval_seconds: float
    report_path: Path
    resolved: dict[str, Any]


def load_record_config(path: str | Path) -> RecordConfig:
    config_path = Path(path).resolve()
    root = _project_root(config_path)
    data = _read_yaml(config_path)
    records = _mapping(data, "records", config_path)
    values = data.get("sources")
    if not isinstance(values, list) or not values:
        raise ValueError(f"sources must be a nonempty list: {config_path}")
    sources = tuple(_record_source(value, config_path) for value in values)
    if len({source.catalog_code for source in sources}) != len(sources):
        raise ValueError(f"catalog_code values must be unique: {config_path}")
    if len({source.raw_table for source in sources}) != len(sources):
        raise ValueError(f"raw_table values must be unique: {config_path}")
    _fail_policy(records, config_path)
    return RecordConfig(
        name=_text(records, "name", config_path),
        project_root=root,
        config_path=config_path,
        on_existing="fail",
        manifest_path=root / _text(records, "manifest_path", config_path),
        sources=sources,
        resolved=data,
    )


def load_match_config(path: str | Path) -> MatchConfig:
    config_path = Path(path).resolve()
    root = _project_root(config_path)
    data = _read_yaml(config_path)
    match = _mapping(data, "match", config_path)
    method = _text(match, "method", config_path)
    if method != "unit_sphere_ckdtree":
        raise ValueError("match.method must be unit_sphere_ckdtree")
    selection = _text(match, "selection", config_path)
    if selection != "none":
        raise ValueError("match.selection must be none for candidate generation")
    _fail_policy(match, config_path)
    chunk_rows = match.get("chunk_rows")
    if (
        not isinstance(chunk_rows, int)
        or isinstance(chunk_rows, bool)
        or chunk_rows <= 0
    ):
        raise ValueError(
            f"match.chunk_rows must be a positive integer: {config_path}"
        )
    workers = match.get("workers")
    if (
        not isinstance(workers, int)
        or isinstance(workers, bool)
        or workers == 0
        or workers < -1
    ):
        raise ValueError(
            f"match.workers must be -1 or a positive integer: {config_path}"
        )
    reference = _text(match, "reference_catalog", config_path)
    target = _text(match, "target_catalog", config_path)
    if reference == target:
        raise ValueError("reference_catalog and target_catalog must differ")
    return MatchConfig(
        name=_text(match, "name", config_path),
        project_root=root,
        config_path=config_path,
        method=method,
        reference_catalog=reference,
        target_catalog=target,
        search_radius_arcsec=_positive_number(
            match, "search_radius_arcsec", config_path
        ),
        selection=selection,
        on_existing="fail",
        chunk_rows=chunk_rows,
        workers=workers,
        progress_interval_seconds=_positive_number(
            match, "progress_interval_seconds", config_path
        ),
        report_path=root / _text(match, "report_path", config_path),
        resolved=data,
    )


def _record_source(value: Any, path: Path) -> RecordSource:
    if not isinstance(value, dict):
        raise ValueError(f"Every record source must be a mapping: {path}")
    keys = value.get("key_columns")
    if not isinstance(keys, list) or not keys:
        raise ValueError(f"key_columns must be a nonempty list: {path}")
    if not all(_valid_identifier(key) for key in keys):
        raise ValueError(f"key_columns must contain SQL identifiers: {path}")
    table = _text(value, "raw_table", path)
    parts = table.split(".")
    if len(parts) != 2 or not all(_valid_identifier(part) for part in parts):
        raise ValueError(f"Expected schema.table identifier: {table}")
    identifiers = {
        key: _text(value, key, path)
        for key in ("raw_ingest_column", "ra_column", "dec_column")
    }
    if not all(_valid_identifier(item) for item in identifiers.values()):
        raise ValueError(f"Configured columns must be SQL identifiers: {path}")
    return RecordSource(
        catalog_code=_text(value, "catalog_code", path),
        raw_table=table,
        raw_ingest_column=identifiers["raw_ingest_column"],
        key_columns=tuple(keys),
        ra_column=identifiers["ra_column"],
        dec_column=identifiers["dec_column"],
    )


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return value


def _project_root(path: Path) -> Path:
    for parent in (path.parent, *path.parents):
        if (parent / "pyproject.toml").is_file():
            return parent
    raise ValueError(f"Cannot locate pyproject.toml above {path}")


def _mapping(data: dict[str, Any], key: str, path: Path) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{key} must be a mapping: {path}")
    return value


def _text(data: dict[str, Any], key: str, path: Path) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must be nonempty text: {path}")
    return value


def _positive_number(data: dict[str, Any], key: str, path: Path) -> float:
    value = data.get(key)
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or value <= 0
    ):
        raise ValueError(f"{key} must be positive: {path}")
    return float(value)


def _fail_policy(data: dict[str, Any], path: Path) -> None:
    if data.get("on_existing") != "fail":
        raise ValueError(f"on_existing must be fail: {path}")


def _valid_identifier(value: Any) -> bool:
    return isinstance(value, str) and value.isidentifier()
