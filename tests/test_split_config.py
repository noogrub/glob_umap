import shutil
import tempfile
import unittest
from pathlib import Path

from glob_umap.cli import _parser
from glob_umap.split import _split_query
from glob_umap.split_config import load_split_config


class SplitConfigTest(unittest.TestCase):
    def test_project_split_config_loads(self) -> None:
        root = Path(__file__).resolve().parents[1]
        config = load_split_config(root / "config/splits/clean.yaml")

        self.assertEqual(config.sample_name, "clean_reciprocal")
        self.assertEqual(config.source_split, "unassigned")
        self.assertEqual(config.development_split, "train")
        self.assertEqual(config.test_split, "test")
        self.assertEqual(config.test_fraction, 0.20)
        self.assertEqual(config.seed, 20260910)

        query, parameters = _split_query(config, sample_id=17)
        sql_text = query.as_string()
        self.assertIn("PARTITION BY m.target_class", sql_text)
        self.assertIn("origin.source_key::jsonb ->> 1", sql_text)
        self.assertIn("floor(", sql_text)
        self.assertEqual(sql_text.count("%s"), len(parameters))

    def test_cli_accepts_split_command(self) -> None:
        args = _parser().parse_args(
            ["split", "--config", "config/splits/clean.yaml"]
        )
        self.assertEqual(args.command, "split")

    def test_rejects_invalid_fraction(self) -> None:
        path = self._copy_config("test_fraction: 0.20", "test_fraction: 1.0")
        with self.assertRaisesRegex(ValueError, "test_fraction"):
            load_split_config(path)

    def test_rejects_reused_split_name(self) -> None:
        path = self._copy_config("development: train", "development: test")
        with self.assertRaisesRegex(ValueError, "must differ"):
            load_split_config(path)

    def _copy_config(self, old: str, new: str) -> Path:
        source_root = Path(__file__).resolve().parents[1]
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        (root / "pyproject.toml").write_text("[project]\n", encoding="ascii")
        source = source_root / "config/splits/clean.yaml"
        path = root / "config/splits/clean.yaml"
        path.parent.mkdir(parents=True)
        shutil.copy(source, path)
        contents = path.read_text(encoding="utf-8").replace(old, new)
        path.write_text(contents, encoding="utf-8")
        return path


if __name__ == "__main__":
    unittest.main()
