import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from glob_umap.config import DatasetConfig
from glob_umap.provenance import build_manifest
from glob_umap.source import PreflightResult


class ProvenanceTest(unittest.TestCase):
    def test_manifest_captures_resolved_configuration_and_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dataset_path = root / "dataset.yaml"
            source_config_path = root / "source.yaml"
            source_path = root / "source.csv"
            dataset_path.write_text("dataset: test\n", encoding="ascii")
            source_config_path.write_text("name: source\n", encoding="ascii")
            source_path.write_text("id\n1\n", encoding="ascii")
            source = {
                "name": "source",
                "path": "source.csv",
                "table": "raw.source",
            }
            config = DatasetConfig(
                name="test",
                project_root=root,
                config_path=dataset_path,
                on_existing="fail",
                manifest_path=root / "manifest.json",
                progress_interval_seconds=10.0,
                source_config_paths=(source_config_path,),
                sources=(source,),
            )
            result = PreflightResult(
                name="source",
                path=source_path,
                sha256=hashlib.sha256(source_path.read_bytes()).hexdigest(),
                row_count=1,
            )

            with (
                patch("glob_umap.provenance._git_commit", return_value="abc123"),
                patch("glob_umap.provenance.version", return_value="test-version"),
            ):
                manifest = build_manifest(config, [result])

            self.assertEqual(
                manifest["configuration"]["resolved"]["sources"], [source]
            )
            expected_hash = hashlib.sha256(dataset_path.read_bytes()).hexdigest()
            self.assertEqual(
                manifest["configuration"]["dataset"]["sha256"], expected_hash
            )


if __name__ == "__main__":
    unittest.main()
