from pathlib import Path

from glob_umap.config import DatasetConfig, load_dataset_config
from glob_umap.source import PreflightResult, preflight


def check_dataset(
    config_path: str | Path,
) -> tuple[DatasetConfig, list[PreflightResult]]:
    config = load_dataset_config(config_path)
    results = [
        preflight(config.project_root, source) for source in config.sources
    ]
    return config, results
