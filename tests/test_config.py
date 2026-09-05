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
sources:
  - source.yaml
""".lstrip(),
                encoding="ascii",
            )
            with self.assertRaisesRegex(ValueError, "on_existing"):
                load_dataset_config(path)


if __name__ == "__main__":
    unittest.main()
