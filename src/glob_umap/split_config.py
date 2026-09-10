from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class SplitConfig:
    name: str
    project_root: Path
    config_path: Path
    sample_name: str
    source_split: str
    development_split: str
    test_split: str
    test_fraction: float
    seed: int
    report_path: Path
    resolved: dict[str, Any]


def load_split_config(path: str | Path) -> SplitConfig:
    config_path = Path(path).resolve()
    root = _project_root(config_path)
    data = _read_yaml(config_path)
    split = _mapping(data, "split", config_path)
    if split.get("on_existing") != "fail":
        raise ValueError(f"split.on_existing must be fail: {config_path}")

    split_names = {
        key: _split_name(split, key, config_path)
        for key in ("source", "development", "test")
    }
    if len(set(split_names.values())) != len(split_names):
        raise ValueError(
            f"source, development, and test splits must differ: {config_path}"
        )

    fraction = _number(split, "test_fraction", config_path)
    if not 0 < fraction < 1:
        raise ValueError(f"split.test_fraction must be between 0 and 1: {config_path}")

    seed = split.get("seed")
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError(f"split.seed must be a nonnegative integer: {config_path}")

    return SplitConfig(
        name=_text(split, "name", config_path),
        project_root=root,
        config_path=config_path,
        sample_name=_text(split, "sample", config_path),
        source_split=split_names["source"],
        development_split=split_names["development"],
        test_split=split_names["test"],
        test_fraction=fraction,
        seed=seed,
        report_path=root / _text(split, "report_path", config_path),
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


def _split_name(data: dict[str, Any], key: str, path: Path) -> str:
    value = _text(data, key, path)
    if value not in {"train", "validation", "test", "unassigned"}:
        raise ValueError(f"split.{key} is not supported: {value}")
    return value


def _number(data: dict[str, Any], key: str, path: Path) -> float:
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"split.{key} must be numeric: {path}")
    return float(value)
