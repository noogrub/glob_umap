from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


BANDS = {"u", "g", "r", "i", "z", "y"}
ROLES = {"reference", "target"}


@dataclass(frozen=True)
class PhotMeasurement:
    band: str
    magnitude_column: str
    error_column: str
    missing_magnitude_values: tuple[float, ...]
    extinction_coefficient: float | None


@dataclass(frozen=True)
class PhotSource:
    catalog: str
    source_role: str
    table: str
    measure: str
    aperture_diameter_px: float | None
    reddening_column: str
    measurements: tuple[PhotMeasurement, ...]


@dataclass(frozen=True)
class PhotConfig:
    name: str
    project_root: Path
    config_path: Path
    sample_name: str
    on_existing: str
    report_path: Path
    reddening_mode: str
    reddening_uncertainty: str
    sources: tuple[PhotSource, ...]
    resolved: dict[str, Any]


def load_phot_config(path: str | Path) -> PhotConfig:
    config_path = Path(path).resolve()
    root = _project_root(config_path)
    data = _read_yaml(config_path)
    phot = _mapping(data, "photometry", config_path)
    reddening = _mapping(phot, "reddening_policy", config_path)
    mode = _text(reddening, "mode", config_path)
    if mode not in {"observed", "coefficient"}:
        raise ValueError(
            f"reddening_policy.mode must be observed or coefficient: {config_path}"
        )
    on_existing = _text(phot, "on_existing", config_path)
    if on_existing != "fail":
        raise ValueError(f"photometry.on_existing must be fail: {config_path}")

    source_values = data.get("sources")
    if not isinstance(source_values, list) or not source_values:
        raise ValueError(f"sources must be a nonempty list: {config_path}")
    sources = tuple(_source(value, mode, config_path) for value in source_values)
    identities = [
        (source.catalog, source.measure, measurement.band)
        for source in sources
        for measurement in source.measurements
    ]
    if len(identities) != len(set(identities)):
        raise ValueError(f"Photometric measurement identities must be unique: {config_path}")
    if {source.source_role for source in sources} != ROLES:
        raise ValueError(f"sources must include reference and target roles: {config_path}")

    return PhotConfig(
        name=_text(phot, "name", config_path),
        project_root=root,
        config_path=config_path,
        sample_name=_text(phot, "sample", config_path),
        on_existing=on_existing,
        report_path=root / _text(phot, "report_path", config_path),
        reddening_mode=mode,
        reddening_uncertainty=_text(reddening, "uncertainty", config_path),
        sources=sources,
        resolved=data,
    )


def _source(value: Any, mode: str, path: Path) -> PhotSource:
    if not isinstance(value, dict):
        raise ValueError(f"Every photometry source must be a mapping: {path}")
    role = _text(value, "source_role", path)
    if role not in ROLES:
        raise ValueError(f"source_role must be reference or target: {path}")
    aperture = value.get("aperture_diameter_px")
    if aperture is not None:
        aperture = _positive_number(value, "aperture_diameter_px", path)
    measurements = value.get("measurements")
    if not isinstance(measurements, list) or not measurements:
        raise ValueError(f"source.measurements must be a nonempty list: {path}")
    parsed = tuple(_measurement(item, mode, path) for item in measurements)
    bands = [item.band for item in parsed]
    if len(bands) != len(set(bands)):
        raise ValueError(f"A source cannot repeat a band: {path}")
    return PhotSource(
        catalog=_text(value, "catalog", path),
        source_role=role,
        table=_table(value, "table", path),
        measure=_text(value, "measure", path),
        aperture_diameter_px=aperture,
        reddening_column=_identifier(value, "reddening_column", path),
        measurements=parsed,
    )


def _measurement(value: Any, mode: str, path: Path) -> PhotMeasurement:
    if not isinstance(value, dict):
        raise ValueError(f"Every measurement must be a mapping: {path}")
    band = _text(value, "band", path).lower()
    if band not in BANDS:
        raise ValueError(f"Unsupported photometric band {band}: {path}")
    coefficient = value.get("extinction_coefficient")
    if mode == "coefficient":
        coefficient = _positive_number(value, "extinction_coefficient", path)
    elif coefficient is not None:
        raise ValueError(
            f"Observed photometry must not specify extinction coefficients: {path}"
        )
    return PhotMeasurement(
        band=band,
        magnitude_column=_identifier(value, "magnitude_column", path),
        error_column=_identifier(value, "error_column", path),
        missing_magnitude_values=_number_list(
            value, "missing_magnitude_values", path
        ),
        extinction_coefficient=coefficient,
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


def _number_list(
    data: dict[str, Any], key: str, path: Path
) -> tuple[float, ...]:
    value = data.get(key)
    if not isinstance(value, list) or any(
        isinstance(item, bool) or not isinstance(item, (int, float))
        for item in value
    ):
        raise ValueError(f"{key} must be a list of numbers: {path}")
    return tuple(float(item) for item in value)


def _positive_number(data: dict[str, Any], key: str, path: Path) -> float:
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise ValueError(f"{key} must be a positive number: {path}")
    return float(value)
