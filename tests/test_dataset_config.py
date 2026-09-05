import unittest
from pathlib import Path

from glob_umap.config import load_dataset_config
from glob_umap.source import target_columns


class DatasetConfigTest(unittest.TestCase):
    def test_fornax_sources_have_unique_database_targets(self) -> None:
        root = Path(__file__).resolve().parents[1]
        config = load_dataset_config(root / "config/datasets/fornax.yaml")
        expected_counts = {
            "raw.fds": 51,
            "raw.des": 27,
            "raw.gc_master": 24,
            "raw.spec": 19,
        }

        self.assertEqual(
            {source["table"] for source in config.sources},
            set(expected_counts),
        )
        for source in config.sources:
            columns = target_columns(source)
            self.assertEqual(len(columns), expected_counts[source["table"]])
            self.assertEqual(len(columns), len(set(columns)))


if __name__ == "__main__":
    unittest.main()
