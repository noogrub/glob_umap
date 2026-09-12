from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import Any

import yaml

from glob_umap.phot_config import BANDS, ROLES, PhotConfig, load_phot_config


@dataclass(frozen=True)
class BandSource:
    band: str
    source_role: str
    measure: str
    dereddened: bool


@dataclass(frozen=True)
class FeatureConfig:
    name: str
    project_root: Path
    config_path: Path
    sample_name: str
    on_existing: str
    photometry: PhotConfig
    report_path: Path
    bands: tuple[BandSource, ...]
    magnitude_prefix: str
    color_order: tuple[str, ...]
    color_separator: str
    color_uncertainty: str
    groups: dict[str, tuple[str, ...]]
    algebraic_tolerance: float
    expected_color_rank: int
    resolved: dict[str, Any]

    @property
    def color_pairs(self) -> tuple[tuple[str, str], ...]:
        return tuple(combinations(self.color_order, 2))

    @property
    def color_names(self) -> tuple[str, ...]:
        return tuple(
            f"{left}{self.color_separator}{right}"
            for left, right in self.color_pairs
        )


def load_feature_config(path: str | Path) -> FeatureConfig:
    config_path = Path(path).resolve()
    root = _project_root(config_path)
    data = _read_yaml(config_path)
    features = _mapping(data, "features", config_path)
    construction = _mapping(data, "construction", config_path)
    audit = _mapping(data, "audit", config_path)
    on_existing = _text(features, "on_existing", config_path)
    if on_existing != "fail":
        raise ValueError(f"features.on_existing must be fail: {config_path}")

    band_values = data.get("bands")
    if not isinstance(band_values, list) or not band_values:
        raise ValueError(f"bands must be a nonempty list: {config_path}")
    bands = tuple(_band(value, config_path) for value in band_values)
    band_names = [item.band for item in bands]
    if set(band_names) != BANDS or len(band_names) != len(BANDS):
        raise ValueError(f"bands must define u, g, r, i, z, and y once: {config_path}")

    color_order = _text_list(construction, "color_order", config_path)
    if set(color_order) != BANDS or len(color_order) != len(BANDS):
        raise ValueError(f"color_order must contain all six bands once: {config_path}")
    if _text(construction, "colors", config_path) != "all_pairs":
        raise ValueError(f"construction.colors must be all_pairs: {config_path}")
    uncertainty = _text(construction, "color_uncertainty", config_path)
    if uncertainty != "independent_quadrature":
        raise ValueError(
            f"color_uncertainty must be independent_quadrature: {config_path}"
        )
    prefix = _text(construction, "magnitude_prefix", config_path)
    separator = _text(construction, "color_separator", config_path)
    color_names = tuple(
        f"{left}{separator}{right}" for left, right in combinations(color_order, 2)
    )
    magnitude_names = tuple(f"{prefix}{band}" for band in color_order)

    group_values = _mapping(data, "groups", config_path)
    groups = {
        name: _text_list(group_values, name, config_path)
        for name in ("magnitudes", "adjacent_colors", "all_colors")
    }
    if groups["magnitudes"] != magnitude_names:
        raise ValueError(f"groups.magnitudes does not match construction: {config_path}")
    adjacent = tuple(
        f"{color_order[index]}{separator}{color_order[index + 1]}"
        for index in range(len(color_order) - 1)
    )
    if groups["adjacent_colors"] != adjacent:
        raise ValueError(
            f"groups.adjacent_colors does not match construction: {config_path}"
        )
    if groups["all_colors"] != color_names:
        raise ValueError(f"groups.all_colors does not match construction: {config_path}")

    tolerance = _nonnegative_number(audit, "algebraic_tolerance", config_path)
    rank = audit.get("expected_color_rank")
    if isinstance(rank, bool) or not isinstance(rank, int) or rank <= 0:
        raise ValueError(f"expected_color_rank must be a positive integer: {config_path}")

    phot_path = root / _text(features, "photometry_config", config_path)
    photometry = load_phot_config(phot_path)
    sample_name = _text(features, "sample", config_path)
    if photometry.sample_name != sample_name:
        raise ValueError("Feature and photometry configurations name different samples")

    return FeatureConfig(
        name=_text(features, "name", config_path),
        project_root=root,
        config_path=config_path,
        sample_name=sample_name,
        on_existing=on_existing,
        photometry=photometry,
        report_path=root / _text(features, "report_path", config_path),
        bands=bands,
        magnitude_prefix=prefix,
        color_order=color_order,
        color_separator=separator,
        color_uncertainty=uncertainty,
        groups=groups,
        algebraic_tolerance=tolerance,
        expected_color_rank=rank,
        resolved=data,
    )


def _band(value: Any, path: Path) -> BandSource:
    if not isinstance(value, dict):
        raise ValueError(f"Every band source must be a mapping: {path}")
    band = _text(value, "band", path).lower()
    role = _text(value, "source_role", path)
    if band not in BANDS:
        raise ValueError(f"Unsupported band {band}: {path}")
    if role not in ROLES:
        raise ValueError(f"source_role must be reference or target: {path}")
    dereddened = value.get("dereddened")
    if not isinstance(dereddened, bool):
        raise ValueError(f"dereddened must be boolean: {path}")
    return BandSource(
        band=band,
        source_role=role,
        measure=_text(value, "measure", path),
        dereddened=dereddened,
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


def _text_list(data: dict[str, Any], key: str, path: Path) -> tuple[str, ...]:
    value = data.get(key)
    if not isinstance(value, list) or not value or not all(
        isinstance(item, str) and item for item in value
    ):
        raise ValueError(f"{key} must be a nonempty list of text: {path}")
    if len(value) != len(set(value)):
        raise ValueError(f"{key} must not contain duplicates: {path}")
    return tuple(value)


def _nonnegative_number(data: dict[str, Any], key: str, path: Path) -> float:
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        raise ValueError(f"{key} must be a nonnegative number: {path}")
    return float(value)
