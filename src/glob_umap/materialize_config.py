from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from glob_umap.sample_config import SampleConfig, load_sample_config


@dataclass(frozen=True)
class MaterializationConfig:
    project_root: Path
    config_path: Path
    sample: SampleConfig
    initial_split: str
    member_weight: float
    gc_target_class: str
    galaxy_target_class: str
    star_target_class: str
    report_path: Path
    resolved: dict[str, Any]


def load_materialization_config(path: str | Path) -> MaterializationConfig:
    config_path = Path(path).resolve()
    root = _project_root(config_path)
    data = _read_yaml(config_path)
    materialization = _mapping(data, "materialization", config_path)
    sample_path = root / _text(materialization, "sample_config", config_path)
    sample = load_sample_config(sample_path)
    target_classes = _mapping(materialization, "target_classes", config_path)
    class_names = {
        key: _text(target_classes, key, config_path)
        for key in ("globular_cluster", "galaxy", "star")
    }
    if len(set(class_names.values())) != len(class_names):
        raise ValueError(f"materialization target classes must be unique: {config_path}")
    initial_split = _text(materialization, "initial_split", config_path)
    if initial_split != "unassigned":
        raise ValueError(f"initial_split must be unassigned: {config_path}")
    weight = _number(materialization, "member_weight", config_path)
    if weight <= 0:
        raise ValueError(f"member_weight must be positive: {config_path}")
    return MaterializationConfig(
        project_root=root,
        config_path=config_path,
        sample=sample,
        initial_split=initial_split,
        member_weight=weight,
        gc_target_class=class_names["globular_cluster"],
        galaxy_target_class=class_names["galaxy"],
        star_target_class=class_names["star"],
        report_path=root / _text(materialization, "report_path", config_path),
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


def _number(data: dict[str, Any], key: str, path: Path) -> float:
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{key} must be numeric: {path}")
    return float(value)
