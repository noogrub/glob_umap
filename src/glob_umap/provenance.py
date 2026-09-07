import json
import platform
import subprocess
from dataclasses import asdict
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from typing import Any

from glob_umap.config import DatasetConfig
from glob_umap.source import PreflightResult, file_sha256


def build_manifest(
    config: DatasetConfig,
    results: list[PreflightResult],
) -> dict[str, Any]:
    project_root = config.project_root
    return {
        "dataset": config.name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git_commit(project_root),
        "configuration": {
            "dataset": _config_file(config.config_path, project_root),
            "sources": [
                _config_file(path, project_root)
                for path in config.source_config_paths
            ],
            "resolved": {
                "dataset": {"name": config.name},
                "ingest": {
                    "on_existing": config.on_existing,
                    "manifest_path": str(
                        config.manifest_path.relative_to(project_root)
                    ),
                    "progress_interval_seconds": (
                        config.progress_interval_seconds
                    ),
                },
                "sources": list(config.sources),
            },
        },
        "software": {
            "python": platform.python_version(),
            "psycopg": version("psycopg"),
            "PyYAML": version("PyYAML"),
        },
        "sources": [
            {
                **asdict(result),
                "path": str(result.path.relative_to(project_root)),
                "rejected_rows": 0,
            }
            for result in results
        ],
    }


def _config_file(path: Path, project_root: Path) -> dict[str, str]:
    return {
        "path": str(path.relative_to(project_root)),
        "sha256": file_sha256(path),
    }


def write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="ascii") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
        handle.write("\n")
    temporary.replace(path)


def _git_commit(project_root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=project_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()
