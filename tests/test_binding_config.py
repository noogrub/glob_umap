import shutil
import tempfile
import unittest
from pathlib import Path

from glob_umap.binding import _target_query
from glob_umap.binding_config import load_binding_config
from glob_umap.cli import _parser


class BindingConfigTest(unittest.TestCase):
    def test_project_binding_config_loads(self) -> None:
        root = Path(__file__).resolve().parents[1]
        config = load_binding_config(root / "config/bindings/clean.yaml")

        self.assertEqual(config.name, "clean_catalogue_records")
        self.assertEqual(
            config.materialization.sample.name, "clean_reciprocal"
        )
        self.assertEqual(
            config.materialization.sample.match_policy, "reciprocal_nearest"
        )

        query, parameters = _target_query(config, sample_id=17)
        sql_text = query.as_string()
        self.assertIn("reference_rank = 1 AND target_rank = 1", sql_text)
        self.assertIn("INSERT INTO ml.member_record", sql_text)
        self.assertEqual(sql_text.count("%s"), len(parameters))

    def test_cli_accepts_bind_command(self) -> None:
        args = _parser().parse_args(
            ["bind", "--config", "config/bindings/clean.yaml"]
        )
        self.assertEqual(args.command, "bind")

    def test_rejects_replacement_policy(self) -> None:
        source_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "pyproject.toml").write_text("[project]\n", encoding="ascii")
            shutil.copytree(source_root / "config", root / "config")
            path = root / "config/bindings/clean.yaml"
            contents = path.read_text(encoding="utf-8").replace(
                "on_existing: fail", "on_existing: replace"
            )
            path.write_text(contents, encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "on_existing"):
                load_binding_config(path)


if __name__ == "__main__":
    unittest.main()
