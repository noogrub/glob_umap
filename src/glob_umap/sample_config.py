from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class Measurement:
    band: str
    source: str
    magnitude_column: str
    error_column: str


@dataclass(frozen=True)
class ClassRule:
    extended_class_value: int
    magnitude_column: str
    magnitude_min: float
    magnitude_max: float


@dataclass(frozen=True)
class SampleConfig:
    name: str
    description: str
    project_root: Path
    config_path: Path
    match_run: str
    match_policy: str
    reference_catalog: str
    target_catalog: str
    reference_table: str
    target_table: str
    master_table: str
    spec_table: str
    measurements: tuple[Measurement, ...]
    max_magnitude_error: float
    master_source_column: str
    master_probability_column: str
    master_probability_min: float
    master_photometric_column: str
    master_spectroscopic_column: str
    master_yes_value: str
    spec_source_column: str
    spec_snr_column: str
    spec_snr_min: float
    spec_class_column: str
    spec_classes: tuple[str, ...]
    reference_source_column: str
    extended_class_column: str
    galaxy: ClassRule
    star: ClassRule
    report_path: Path
    paper_counts: dict[str, int]
    resolved: dict[str, Any]


def load_sample_config(path: str | Path) -> SampleConfig:
    config_path = Path(path).resolve()
    root = _project_root(config_path)
    data = _read_yaml(config_path)
    sample = _mapping(data, "sample", config_path)
    sources = _mapping(data, "sources", config_path)
    quality = _mapping(data, "quality", config_path)
    labels = _mapping(data, "labels", config_path)
    master = _mapping(labels, "master", config_path)
    spec = _mapping(labels, "spec", config_path)
    contaminants = _mapping(labels, "contaminants", config_path)

    policy = _text(sample, "match_policy", config_path)
    if policy not in {"reference_nearest", "reciprocal_nearest"}:
        raise ValueError(
            "sample.match_policy must be reference_nearest or reciprocal_nearest"
        )

    measurement_values = quality.get("measurements")
    if not isinstance(measurement_values, list) or not measurement_values:
        raise ValueError(f"quality.measurements must be a nonempty list: {config_path}")
    measurements = tuple(
        _measurement(value, config_path) for value in measurement_values
    )
    if {item.band for item in measurements} != {"u", "g", "r", "i", "z", "y"}:
        raise ValueError("quality.measurements must define u, g, r, i, z, and y")

    spec_classes = spec.get("accepted_classes")
    if not isinstance(spec_classes, list) or not spec_classes or not all(
        isinstance(value, str) and value for value in spec_classes
    ):
        raise ValueError(f"labels.spec.accepted_classes is invalid: {config_path}")

    paper_counts = data.get("paper_counts", {})
    if not isinstance(paper_counts, dict) or not all(
        isinstance(key, str)
        and isinstance(value, int)
        and not isinstance(value, bool)
        and value >= 0
        for key, value in paper_counts.items()
    ):
        raise ValueError(f"paper_counts must map names to nonnegative integers: {config_path}")

    return SampleConfig(
        name=_text(sample, "name", config_path),
        description=_text(sample, "description", config_path),
        project_root=root,
        config_path=config_path,
        match_run=_text(sample, "match_run", config_path),
        match_policy=policy,
        reference_catalog=_text(sample, "reference_catalog", config_path),
        target_catalog=_text(sample, "target_catalog", config_path),
        reference_table=_table(sources, "reference_table", config_path),
        target_table=_table(sources, "target_table", config_path),
        master_table=_table(sources, "master_table", config_path),
        spec_table=_table(sources, "spec_table", config_path),
        measurements=measurements,
        max_magnitude_error=_nonnegative_number(
            quality, "max_magnitude_error", config_path
        ),
        master_source_column=_identifier(master, "source_column", config_path),
        master_probability_column=_identifier(
            master, "probability_column", config_path
        ),
        master_probability_min=_nonnegative_number(
            master, "probability_min_exclusive", config_path
        ),
        master_photometric_column=_identifier(
            master, "photometric_flag_column", config_path
        ),
        master_spectroscopic_column=_identifier(
            master, "spectroscopic_flag_column", config_path
        ),
        master_yes_value=_text(master, "yes_value", config_path),
        spec_source_column=_identifier(spec, "source_column", config_path),
        spec_snr_column=_identifier(spec, "snr_column", config_path),
        spec_snr_min=_nonnegative_number(spec, "snr_min", config_path),
        spec_class_column=_identifier(spec, "class_column", config_path),
        spec_classes=tuple(spec_classes),
        reference_source_column=_identifier(
            labels, "reference_source_column", config_path
        ),
        extended_class_column=_identifier(
            contaminants, "extended_class_column", config_path
        ),
        galaxy=_class_rule(contaminants, "galaxy", config_path),
        star=_class_rule(contaminants, "star", config_path),
        report_path=root / _text(sample, "report_path", config_path),
        paper_counts=paper_counts,
        resolved=data,
    )


def _measurement(value: Any, path: Path) -> Measurement:
    if not isinstance(value, dict):
        raise ValueError(f"Every measurement must be a mapping: {path}")
    source = _text(value, "source", path)
    if source not in {"reference", "target"}:
        raise ValueError(f"measurement source must be reference or target: {path}")
    return Measurement(
        band=_text(value, "band", path).lower(),
        source=source,
        magnitude_column=_identifier(value, "magnitude_column", path),
        error_column=_identifier(value, "error_column", path),
    )


def _class_rule(data: dict[str, Any], key: str, path: Path) -> ClassRule:
    value = _mapping(data, key, path)
    extended = value.get("extended_class_value")
    if not isinstance(extended, int) or isinstance(extended, bool):
        raise ValueError(f"{key}.extended_class_value must be an integer: {path}")
    lower = _number(value, "magnitude_min", path)
    upper = _number(value, "magnitude_max", path)
    if lower > upper:
        raise ValueError(f"{key} magnitude range is reversed: {path}")
    return ClassRule(
        extended_class_value=extended,
        magnitude_column=_identifier(value, "magnitude_column", path),
        magnitude_min=lower,
        magnitude_max=upper,
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


def _identifier(data: dict[str, Any], key: str, path: Path) -> str:
    value = _text(data, key, path)
    if not value.isidentifier():
        raise ValueError(f"{key} must be a SQL identifier: {path}")
    return value


def _table(data: dict[str, Any], key: str, path: Path) -> str:
    value = _text(data, key, path)
    parts = value.split(".")
    if len(parts) != 2 or not all(part.isidentifier() for part in parts):
        raise ValueError(f"{key} must be schema.table: {path}")
    return value


def _number(data: dict[str, Any], key: str, path: Path) -> float:
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{key} must be numeric: {path}")
    return float(value)


def _nonnegative_number(data: dict[str, Any], key: str, path: Path) -> float:
    value = _number(data, key, path)
    if value < 0:
        raise ValueError(f"{key} must be nonnegative: {path}")
    return value
