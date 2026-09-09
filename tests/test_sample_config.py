import tempfile
import unittest
from pathlib import Path

from glob_umap.funnel import _count_query
from glob_umap.materialize_config import load_materialization_config
from glob_umap.sample import _member_query
from glob_umap.sample_config import load_sample_config


class SampleConfigTest(unittest.TestCase):
    def test_project_sample_configs_load(self) -> None:
        root = Path(__file__).resolve().parents[1]
        clean = load_sample_config(root / "config/samples/clean.yaml")
        paper = load_sample_config(root / "config/samples/paper.yaml")

        self.assertEqual(clean.match_policy, "reciprocal_nearest")
        self.assertEqual(paper.match_policy, "reference_nearest")
        self.assertEqual(
            {measurement.band for measurement in clean.measurements},
            {"u", "g", "r", "i", "z", "y"},
        )
        self.assertEqual(clean.max_magnitude_error, 0.5)
        self.assertEqual(clean.measurements[0].missing_magnitude_values, ())
        self.assertTrue(
            all(
                measurement.missing_magnitude_values == (99.0,)
                for measurement in clean.measurements
                if measurement.source == "target"
            )
        )
        self.assertEqual(clean.galaxy.extended_class_value, 3)
        self.assertEqual(clean.star.extended_class_value, 0)

        clean_query, clean_parameters = _count_query(clean)
        paper_query, paper_parameters = _count_query(paper)
        clean_sql = clean_query.as_string()
        paper_sql = paper_query.as_string()
        self.assertIn("target_rank = 1", clean_sql)
        self.assertNotIn("target_rank = 1", paper_sql)
        self.assertEqual(clean_sql.count("<> %s"), 5)
        self.assertEqual(clean_sql.count("%s"), len(clean_parameters))
        self.assertEqual(paper_sql.count("%s"), len(paper_parameters))

        materialization = load_materialization_config(
            root / "config/materialize/clean.yaml"
        )
        self.assertEqual(materialization.sample.name, clean.name)
        self.assertEqual(materialization.initial_split, "unassigned")
        self.assertEqual(materialization.member_weight, 1.0)
        member_query, member_parameters = _member_query(
            materialization, sample_id=17
        )
        member_sql = member_query.as_string()
        self.assertIn("INSERT INTO ml.member", member_sql)
        self.assertIn("GROUP BY target_class", member_sql)
        self.assertEqual(member_sql.count("%s"), len(member_parameters))

    def test_rejects_unknown_match_policy(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "pyproject.toml").write_text("[project]\n", encoding="ascii")
            source = Path(__file__).resolve().parents[1] / "config/samples/clean.yaml"
            contents = source.read_text(encoding="utf-8").replace(
                "match_policy: reciprocal_nearest", "match_policy: guessed"
            )
            path = root / "sample.yaml"
            path.write_text(contents, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "match_policy"):
                load_sample_config(path)

    def test_rejects_duplicate_target_classes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "pyproject.toml").write_text("[project]\n", encoding="ascii")
            source = (
                Path(__file__).resolve().parents[1]
                / "config/materialize/clean.yaml"
            )
            contents = source.read_text(encoding="utf-8").replace(
                "    star: star", "    star: galaxy"
            )
            sample_source = (
                Path(__file__).resolve().parents[1] / "config/samples/clean.yaml"
            )
            sample_path = root / "config/samples/clean.yaml"
            sample_path.parent.mkdir(parents=True)
            sample_path.write_text(sample_source.read_text(encoding="utf-8"))
            path = root / "materialize.yaml"
            path.write_text(contents, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "target classes"):
                load_materialization_config(path)


if __name__ == "__main__":
    unittest.main()
