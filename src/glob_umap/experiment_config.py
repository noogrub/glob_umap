from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from glob_umap.feature_config import FeatureConfig, load_feature_config


@dataclass(frozen=True)
class Representation:
    name: str
    stage: str
    method: str
    feature_group: str
    dimensions: tuple[int, ...]
    parameters: dict[str, Any]


@dataclass(frozen=True)
class Classifier:
    name: str
    role: str
    parameters: dict[str, Any]


@dataclass(frozen=True)
class ExperimentConfig:
    name: str
    project_root: Path
    config_path: Path
    sample_name: str
    feature_set_name: str
    features: FeatureConfig
    report_path: Path
    task_type: str
    classes: tuple[str, ...]
    focal_class: str
    development_split: str
    final_test_split: str
    final_test_policy: str
    preprocessing: dict[str, Any]
    cross_validation: dict[str, Any]
    selection_metric: str
    selection_target: str
    representations: tuple[Representation, ...]
    classifiers: tuple[Classifier, ...]
    target_recall: float
    threshold_source: str
    threshold_application: str
    metrics: tuple[str, ...]
    uncertainty: dict[str, Any]
    comparisons: tuple[str, ...]
    resolved: dict[str, Any]


def load_experiment_config(path: str | Path) -> ExperimentConfig:
    config_path = Path(path).resolve()
    root = _project_root(config_path)
    data = _read_yaml(config_path)
    experiment = _mapping(data, "experiment", config_path)
    task = _mapping(data, "task", config_path)
    partition = _mapping(data, "partition", config_path)
    preprocessing = _mapping(data, "preprocessing", config_path)
    development = _mapping(data, "development", config_path)
    cross_validation = _mapping(development, "cross_validation", config_path)
    operating = _mapping(data, "operating_point", config_path)
    evaluation = _mapping(data, "evaluation", config_path)
    uncertainty = _mapping(evaluation, "uncertainty", config_path)

    task_type = _text(task, "type", config_path)
    if task_type != "multiclass":
        raise ValueError(f"task.type must be multiclass: {config_path}")
    classes = _text_list(task, "classes", config_path)
    focal = _text(task, "focal_class", config_path)
    if focal not in classes:
        raise ValueError(f"focal_class must occur in task.classes: {config_path}")

    development_split = _split(partition, "development_split", config_path)
    final_test_split = _split(partition, "final_test_split", config_path)
    if development_split == final_test_split:
        raise ValueError(f"Development and final-test splits must differ: {config_path}")
    final_policy = _text(partition, "final_test_policy", config_path)
    if final_policy != "locked_until_model_selection_complete":
        raise ValueError(f"Unsupported final_test_policy: {config_path}")

    expected_preprocessing = {
        "missing_values": "reject",
        "scaling": "standard",
        "fit_scope": "fold_training_only",
    }
    if preprocessing != expected_preprocessing:
        raise ValueError(
            f"preprocessing must explicitly equal {expected_preprocessing}: {config_path}"
        )
    _validate_cross_validation(cross_validation, config_path)

    feature_path = root / _text(experiment, "feature_config", config_path)
    features = load_feature_config(feature_path)
    sample_name = _text(experiment, "sample", config_path)
    if features.sample_name != sample_name:
        raise ValueError("Experiment and feature configurations name different samples")
    feature_set_name = _text(experiment, "feature_set", config_path)
    if features.name != feature_set_name:
        raise ValueError("Experiment feature_set does not match the feature configuration")

    representation_values = data.get("representations")
    if not isinstance(representation_values, list) or not representation_values:
        raise ValueError(f"representations must be a nonempty list: {config_path}")
    representations = tuple(
        _representation(value, features, config_path)
        for value in representation_values
    )
    _unique_names(representations, "representations", config_path)
    primary_methods = {
        item.method for item in representations if item.stage == "primary"
    }
    if primary_methods != {"identity", "pca", "umap"}:
        raise ValueError(
            "Primary representations must include identity, pca, and umap"
        )

    classifier_values = data.get("classifiers")
    if not isinstance(classifier_values, list) or not classifier_values:
        raise ValueError(f"classifiers must be a nonempty list: {config_path}")
    classifiers = tuple(_classifier(value, config_path) for value in classifier_values)
    _unique_names(classifiers, "classifiers", config_path)
    if sum(item.role == "primary" for item in classifiers) != 1:
        raise ValueError(f"Exactly one classifier must be primary: {config_path}")

    target_recall = _fraction(operating, "target_recall", config_path)
    threshold_source = _text(operating, "threshold_source", config_path)
    threshold_application = _text(operating, "application", config_path)
    if threshold_source != "out_of_fold_development_predictions":
        raise ValueError(f"Unsupported threshold_source: {config_path}")
    if threshold_application != "fixed_threshold_on_final_test":
        raise ValueError(f"Unsupported operating-point application: {config_path}")

    metrics = _text_list(evaluation, "metrics", config_path)
    required_metrics = {
        "average_precision",
        "precision_recall_curve",
        "contamination_at_recall",
        "precision_at_locked_threshold",
        "recall_at_locked_threshold",
        "f1_at_locked_threshold",
        "confusion_matrix",
    }
    if set(metrics) != required_metrics:
        raise ValueError(f"evaluation.metrics is incomplete: {config_path}")
    _validate_uncertainty(uncertainty, config_path)

    return ExperimentConfig(
        name=_text(experiment, "name", config_path),
        project_root=root,
        config_path=config_path,
        sample_name=sample_name,
        feature_set_name=feature_set_name,
        features=features,
        report_path=root / _text(experiment, "report_path", config_path),
        task_type=task_type,
        classes=classes,
        focal_class=focal,
        development_split=development_split,
        final_test_split=final_test_split,
        final_test_policy=final_policy,
        preprocessing=dict(preprocessing),
        cross_validation=dict(cross_validation),
        selection_metric=_text(development, "selection_metric", config_path),
        selection_target=_text(development, "selection_target", config_path),
        representations=representations,
        classifiers=classifiers,
        target_recall=target_recall,
        threshold_source=threshold_source,
        threshold_application=threshold_application,
        metrics=metrics,
        uncertainty=dict(uncertainty),
        comparisons=_text_list(evaluation, "final_comparisons", config_path),
        resolved=data,
    )


def _representation(
    value: Any, features: FeatureConfig, path: Path
) -> Representation:
    if not isinstance(value, dict):
        raise ValueError(f"Every representation must be a mapping: {path}")
    method = _text(value, "method", path)
    if method not in {"identity", "pca", "umap"}:
        raise ValueError(f"Unsupported representation method {method}: {path}")
    group = _text(value, "feature_group", path)
    if group not in features.groups:
        raise ValueError(f"Unknown feature group {group}: {path}")
    dimensions = _positive_int_list(value, "dimensions", path)
    if any(item > len(features.groups[group]) for item in dimensions):
        raise ValueError(f"Representation dimension exceeds input dimension: {path}")
    parameters = value.get("parameters")
    if not isinstance(parameters, dict):
        raise ValueError(f"representation.parameters must be a mapping: {path}")
    if method == "identity" and (parameters or dimensions != (len(features.groups[group]),)):
        raise ValueError(f"Identity representation must preserve its input: {path}")
    if method == "umap":
        required = {
            "n_neighbors",
            "min_dist",
            "metric",
            "tuning_seed",
            "stability_seeds",
        }
        if set(parameters) != required:
            raise ValueError(f"UMAP parameters must explicitly define {required}: {path}")
        if not _positive_int_values(parameters["n_neighbors"]):
            raise ValueError(f"UMAP n_neighbors is invalid: {path}")
        if not _bounded_number_values(parameters["min_dist"], 0.0, 1.0):
            raise ValueError(f"UMAP min_dist is invalid: {path}")
        if not _nonempty_text_values(parameters["metric"]):
            raise ValueError(f"UMAP metric is invalid: {path}")
        if not _nonnegative_int(parameters["tuning_seed"]):
            raise ValueError(f"UMAP tuning_seed is invalid: {path}")
        if not _nonnegative_int_values(parameters["stability_seeds"]):
            raise ValueError(f"UMAP stability_seeds is invalid: {path}")
    return Representation(
        name=_text(value, "name", path),
        stage=_text(value, "stage", path),
        method=method,
        feature_group=group,
        dimensions=dimensions,
        parameters=dict(parameters),
    )


def _classifier(value: Any, path: Path) -> Classifier:
    if not isinstance(value, dict):
        raise ValueError(f"Every classifier must be a mapping: {path}")
    parameters = value.get("parameters")
    if not isinstance(parameters, dict) or not parameters:
        raise ValueError(f"classifier.parameters must be a nonempty mapping: {path}")
    return Classifier(
        name=_text(value, "name", path),
        role=_text(value, "role", path),
        parameters=dict(parameters),
    )


def _validate_cross_validation(value: dict[str, Any], path: Path) -> None:
    if _text(value, "method", path) != "stratified_k_fold":
        raise ValueError(f"cross_validation.method is unsupported: {path}")
    folds = value.get("folds")
    repeats = value.get("repeats")
    seeds = value.get("seeds")
    if not isinstance(folds, int) or isinstance(folds, bool) or folds < 2:
        raise ValueError(f"cross_validation.folds must be at least two: {path}")
    if not isinstance(repeats, int) or isinstance(repeats, bool) or repeats < 1:
        raise ValueError(f"cross_validation.repeats must be positive: {path}")
    if not _nonnegative_int_values(seeds) or len(seeds) != repeats:
        raise ValueError(f"cross_validation seeds must match repeats: {path}")
    if value.get("shuffle") is not True:
        raise ValueError(f"cross_validation.shuffle must be true: {path}")


def _validate_uncertainty(value: dict[str, Any], path: Path) -> None:
    if _text(value, "method", path) != "paired_stratified_bootstrap":
        raise ValueError(f"uncertainty.method is unsupported: {path}")
    replicates = value.get("replicates")
    seed = value.get("seed")
    if not isinstance(replicates, int) or isinstance(replicates, bool) or replicates < 1:
        raise ValueError(f"uncertainty.replicates must be positive: {path}")
    _fraction(value, "confidence_level", path)
    if not _nonnegative_int(seed):
        raise ValueError(f"uncertainty.seed must be nonnegative: {path}")


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
    if not _nonempty_text_values(value):
        raise ValueError(f"{key} must be a nonempty list of text: {path}")
    if len(value) != len(set(value)):
        raise ValueError(f"{key} must not contain duplicates: {path}")
    return tuple(value)


def _positive_int_list(
    data: dict[str, Any], key: str, path: Path
) -> tuple[int, ...]:
    value = data.get(key)
    if not _positive_int_values(value):
        raise ValueError(f"{key} must be a nonempty list of positive integers: {path}")
    if len(value) != len(set(value)):
        raise ValueError(f"{key} must not contain duplicates: {path}")
    return tuple(value)


def _split(data: dict[str, Any], key: str, path: Path) -> str:
    value = _text(data, key, path)
    if value not in {"train", "validation", "test", "unassigned"}:
        raise ValueError(f"Unsupported split {value}: {path}")
    return value


def _fraction(data: dict[str, Any], key: str, path: Path) -> float:
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 < value < 1:
        raise ValueError(f"{key} must be between zero and one: {path}")
    return float(value)


def _unique_names(values: tuple[Any, ...], label: str, path: Path) -> None:
    names = [item.name for item in values]
    if len(names) != len(set(names)):
        raise ValueError(f"{label} names must be unique: {path}")


def _positive_int_values(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(
        isinstance(item, int) and not isinstance(item, bool) and item > 0
        for item in value
    )


def _nonnegative_int_values(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(
        _nonnegative_int(item) for item in value
    )


def _nonnegative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _bounded_number_values(value: Any, lower: float, upper: float) -> bool:
    return isinstance(value, list) and bool(value) and all(
        not isinstance(item, bool)
        and isinstance(item, (int, float))
        and lower <= item <= upper
        for item in value
    )


def _nonempty_text_values(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(
        isinstance(item, str) and item for item in value
    )
