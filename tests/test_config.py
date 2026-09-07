import tempfile
import unittest
from pathlib import Path

from glob_umap.config import load_dataset_config


class ConfigTest(unittest.TestCase):
    def test_rejects_unknown_existing_policy(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "pyproject.toml").write_text("[project]\n", encoding="ascii")
            config_dir = root / "config" / "datasets"
            config_dir.mkdir(parents=True)
            path = config_dir / "test.yaml"
            path.write_text(
                """
dataset:
  name: test
ingest:
  on_existing: replace
  manifest_path: manifest.json
  progress_interval_seconds: 10
sources:
  - source.yaml
""".lstrip(),
                encoding="ascii",
            )
            with self.assertRaisesRegex(ValueError, "on_existing"):
                load_dataset_config(path)

    def test_rejects_nonpositive_progress_interval(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "pyproject.toml").write_text("[project]\n", encoding="ascii")
            path = root / "test.yaml"
            path.write_text(
                """
dataset:
  name: test
ingest:
  on_existing: fail
  manifest_path: manifest.json
  progress_interval_seconds: 0
sources:
  - source.yaml
""".lstrip(),
                encoding="ascii",
            )
            with self.assertRaisesRegex(ValueError, "progress_interval"):
                load_dataset_config(path)


if __name__ == "__main__":
    unittest.main()
