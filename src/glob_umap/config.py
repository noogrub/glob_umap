from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class DatasetConfig:
    name: str
    project_root: Path
    on_existing: str
    manifest_path: Path
    sources: tuple[dict[str, Any], ...]


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return value


def _project_root(config_path: Path) -> Path:
    for parent in (config_path.parent, *config_path.parents):
        if (parent / "pyproject.toml").is_file():
            return parent
    raise ValueError(f"Cannot locate pyproject.toml above {config_path}")


def load_dataset_config(path: str | Path) -> DatasetConfig:
    config_path = Path(path).resolve()
    root = _project_root(config_path)
    data = _read_yaml(config_path)

    dataset = _required_mapping(data, "dataset", config_path)
    ingest = _required_mapping(data, "ingest", config_path)
    source_paths = data.get("sources")
    if not isinstance(source_paths, list) or not source_paths:
        raise ValueError(f"sources must be a nonempty list: {config_path}")

    on_existing = ingest.get("on_existing")
    if on_existing != "fail":
        raise ValueError("ingest.on_existing must be fail")

    sources = []
    for source_path in source_paths:
        if not isinstance(source_path, str):
            raise ValueError("Every source config path must be a string")
        source = _read_yaml(root / source_path)
        _validate_source(source, root / source_path)
        sources.append(source)

    return DatasetConfig(
        name=_required_text(dataset, "name", config_path),
        project_root=root,
        on_existing=on_existing,
        manifest_path=root / _required_text(ingest, "manifest_path", config_path),
        sources=tuple(sources),
    )


def _required_mapping(
    data: dict[str, Any], key: str, path: Path
) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{key} must be a mapping: {path}")
    return value


def _required_text(data: dict[str, Any], key: str, path: Path) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must be nonempty text: {path}")
    return value


def _validate_source(source: dict[str, Any], path: Path) -> None:
    for key in ("name", "table", "path", "format", "sha256"):
        _required_text(source, key, path)
    rows = source.get("expected_rows")
    if not isinstance(rows, int) or rows < 0:
        raise ValueError(f"expected_rows must be a nonnegative integer: {path}")
    if source["format"] == "csv" and not source.get("columns"):
        raise ValueError(f"CSV source requires columns: {path}")
    if source["format"] == "fixed_width" and not source.get("fields"):
        raise ValueError(f"Fixed-width source requires fields: {path}")
    if source["format"] not in {"csv", "fixed_width"}:
        raise ValueError(f"Unsupported source format: {source['format']}")
    _required_mapping(source, "catalog", path)
