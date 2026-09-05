import json
import platform
import subprocess
from dataclasses import asdict
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from typing import Any

from glob_umap.source import PreflightResult


def build_manifest(
    dataset_name: str,
    project_root: Path,
    results: list[PreflightResult],
) -> dict[str, Any]:
    return {
        "dataset": dataset_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git_commit(project_root),
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
