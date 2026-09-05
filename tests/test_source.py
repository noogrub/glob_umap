import hashlib
import tempfile
import unittest
from pathlib import Path

from glob_umap.source import preflight, rows


class SourceTest(unittest.TestCase):
    def test_csv_preserves_sentinel_and_maps_empty_to_none(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "source.csv"
            path.write_text("id,value\n1,99\n2,\n", encoding="ascii")
            source = {
                "name": "test",
                "path": "source.csv",
                "format": "csv",
                "columns": [["id", "source_id"], ["value", "value"]],
            }
            self.assertEqual(
                list(rows(root, source)),
                [(1, ["1", "99"]), (2, ["2", None])],
            )

    def test_fixed_width_uses_one_based_inclusive_ranges(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "source.dat"
            path.write_text("ABC 12  \n", encoding="ascii")
            source = {
                "name": "test",
                "path": "source.dat",
                "format": "fixed_width",
                "fields": [["name", 1, 3], ["value", 5, 6], ["empty", 8, 9]],
            }
            self.assertEqual(list(rows(root, source)), [(1, ["ABC", "12", None])])

    def test_preflight_verifies_hash_and_count(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "source.csv"
            content = b"id\n1\n2\n"
            path.write_bytes(content)
            source = {
                "name": "test",
                "path": "source.csv",
                "format": "csv",
                "columns": [["id", "source_id"]],
                "expected_rows": 2,
                "sha256": hashlib.sha256(content).hexdigest(),
            }
            result = preflight(root, source)
            self.assertEqual(result.row_count, 2)


if __name__ == "__main__":
    unittest.main()
