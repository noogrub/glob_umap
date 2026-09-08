from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class TableAudit:
    table: str
    key_columns: tuple[str, ...]
    coordinate_columns: tuple[str, str]


@dataclass(frozen=True)
class AuditConfig:
    name: str
    project_root: Path
    config_path: Path
    dataset_config_path: Path
    output_path: Path
    bounds: dict[str, float]
    tables: tuple[TableAudit, ...]


def load_audit_config(path: str | Path) -> AuditConfig:
    config_path = Path(path).resolve()
    root = _project_root(config_path)
    data = _read_yaml(config_path)
    audit = _mapping(data, "audit", config_path)
    bounds = _mapping(data, "coordinate_bounds", config_path)
    table_values = data.get("tables")
    if not isinstance(table_values, list) or not table_values:
        raise ValueError(f"tables must be a nonempty list: {config_path}")

    tables = tuple(_table(value, config_path) for value in table_values)
    if len({table.table for table in tables}) != len(tables):
        raise ValueError(f"Audit table names must be unique: {config_path}")

    required_bounds = ("ra_min_deg", "ra_max_deg", "dec_min_deg", "dec_max_deg")
    parsed_bounds = {}
    for key in required_bounds:
        value = bounds.get(key)
        if not isinstance(value, (int, float)):
            raise ValueError(f"{key} must be numeric: {config_path}")
        parsed_bounds[key] = float(value)

    return AuditConfig(
        name=_text(audit, "name", config_path),
        project_root=root,
        config_path=config_path,
        dataset_config_path=root / _text(audit, "dataset_config", config_path),
        output_path=root / _text(audit, "output_path", config_path),
        bounds=parsed_bounds,
        tables=tables,
    )


def _table(value: Any, path: Path) -> TableAudit:
    if not isinstance(value, dict):
        raise ValueError(f"Every table audit must be a mapping: {path}")
    table = _text(value, "table", path)
    parts = table.split(".")
    if len(parts) != 2 or any(not part.isidentifier() for part in parts):
        raise ValueError(f"Expected schema.table identifier: {table}")
    keys = value.get("key_columns")
    coordinates = value.get("coordinate_columns")
    if not _identifier_list(keys) or not keys:
        raise ValueError(f"key_columns must contain identifiers: {path}")
    if not _identifier_list(coordinates) or len(coordinates) != 2:
        raise ValueError(f"coordinate_columns must contain RA and Dec: {path}")
    return TableAudit(table, tuple(keys), tuple(coordinates))


def _identifier_list(value: Any) -> bool:
    return isinstance(value, list) and all(
        isinstance(item, str) and item.isidentifier() for item in value
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
