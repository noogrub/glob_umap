from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from glob_umap.materialize_config import (
    MaterializationConfig,
    load_materialization_config,
)


@dataclass(frozen=True)
class LabelConfig:
    name: str
    project_root: Path
    config_path: Path
    materialization: MaterializationConfig
    master_catalog: str
    spec_catalog: str
    master_photometric_evidence: str
    master_spectroscopic_evidence: str
    spec_spectroscopic_evidence: str
    des_morphology_evidence: str
    master_provenance: str
    spec_provenance: str
    des_provenance: str
    report_path: Path
    resolved: dict[str, Any]


def load_label_config(path: str | Path) -> LabelConfig:
    config_path = Path(path).resolve()
    root = _project_root(config_path)
    data = _read_yaml(config_path)
    labels = _mapping(data, "labels", config_path)
    catalogs = _mapping(data, "catalogs", config_path)
    evidence = _mapping(data, "evidence", config_path)
    provenance = _mapping(data, "provenance", config_path)
    if labels.get("on_existing") != "fail":
        raise ValueError(f"labels.on_existing must be fail: {config_path}")

    materialization_path = root / _text(
        labels, "materialization_config", config_path
    )
    materialization = load_materialization_config(materialization_path)
    evidence_names = {
        key: _text(evidence, key, config_path)
        for key in (
            "master_photometric",
            "master_spectroscopic",
            "spec_spectroscopic",
            "des_morphology",
        )
    }
    if len(set(evidence_names.values())) != len(evidence_names):
        raise ValueError(f"Evidence names must be unique: {config_path}")

    return LabelConfig(
        name=_text(labels, "name", config_path),
        project_root=root,
        config_path=config_path,
        materialization=materialization,
        master_catalog=_text(catalogs, "master", config_path),
        spec_catalog=_text(catalogs, "spec", config_path),
        master_photometric_evidence=evidence_names["master_photometric"],
        master_spectroscopic_evidence=evidence_names["master_spectroscopic"],
        spec_spectroscopic_evidence=evidence_names["spec_spectroscopic"],
        des_morphology_evidence=evidence_names["des_morphology"],
        master_provenance=_text(provenance, "master", config_path),
        spec_provenance=_text(provenance, "spec", config_path),
        des_provenance=_text(provenance, "des", config_path),
        report_path=root / _text(labels, "report_path", config_path),
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
