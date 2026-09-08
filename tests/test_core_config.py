import tempfile
import unittest
from pathlib import Path

from glob_umap.core_config import load_match_config, load_record_config


class CoreConfigTest(unittest.TestCase):
    def test_project_configs_load(self) -> None:
        root = Path(__file__).resolve().parents[1]
        records = load_record_config(root / "config/core/records.yaml")
        match = load_match_config(root / "config/matches/fds_des.yaml")
        self.assertEqual(
            {source.catalog_code for source in records.sources},
            {
                "fds_aa_639_a136",
                "des_dr2_fornax",
                "fds_gc_master",
                "chaturvedi_aa_657_a93",
            },
        )
        self.assertEqual(match.search_radius_arcsec, 1.0)
        self.assertEqual(match.selection, "none")
        self.assertEqual(match.workers, -1)

    def test_match_rejects_automatic_selection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "pyproject.toml").write_text("[project]\n", encoding="ascii")
            path = root / "match.yaml"
            path.write_text(
                """
match:
  name: test
  method: unit_sphere_ckdtree
  reference_catalog: left
  target_catalog: right
  search_radius_arcsec: 1.0
  selection: nearest
  on_existing: fail
  chunk_rows: 10
  workers: 1
  progress_interval_seconds: 10
  report_path: report.json
""".lstrip(),
                encoding="ascii",
            )
            with self.assertRaisesRegex(ValueError, "selection"):
                load_match_config(path)


if __name__ == "__main__":
    unittest.main()
