import unittest
from pathlib import Path

from glob_umap.audit_config import load_audit_config


class AuditConfigTest(unittest.TestCase):
    def test_raw_audit_covers_each_loaded_table(self) -> None:
        root = Path(__file__).resolve().parents[1]
        config = load_audit_config(root / "config/audits/raw.yaml")
        self.assertEqual(
            {table.table for table in config.tables},
            {"raw.fds", "raw.des", "raw.gc_master", "raw.spec"},
        )
        for table in config.tables:
            self.assertTrue(table.key_columns)
            self.assertEqual(len(table.coordinate_columns), 2)
        spec = next(table for table in config.tables if table.table == "raw.spec")
        self.assertEqual(spec.key_columns, ("source_file", "source_row"))


if __name__ == "__main__":
    unittest.main()
