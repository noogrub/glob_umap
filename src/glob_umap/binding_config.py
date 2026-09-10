from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from glob_umap.materialize_config import (
    MaterializationConfig,
    load_materialization_config,
)


@dataclass(frozen=True)
class BindingConfig:
    name: str
    project_root: Path
    config_path: Path
    materialization: MaterializationConfig
    report_path: Path
    resolved: dict[str, Any]


def load_binding_config(path: str | Path) -> BindingConfig:
    config_path = Path(path).resolve()
    root = _project_root(config_path)
    data = _read_yaml(config_path)
    binding = _mapping(data, "binding", config_path)
    if binding.get("on_existing") != "fail":
        raise ValueError(f"binding.on_existing must be fail: {config_path}")

    materialization_path = root / _text(
        binding, "materialization_config", config_path
    )
    return BindingConfig(
        name=_text(binding, "name", config_path),
        project_root=root,
        config_path=config_path,
        materialization=load_materialization_config(materialization_path),
        report_path=root / _text(binding, "report_path", config_path),
        resolved=data,
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
