import shutil
import tempfile
import unittest
from pathlib import Path

from glob_umap.cli import _parser
from glob_umap.feature import _insert_color, _insert_magnitude
from glob_umap.feature_config import load_feature_config


class _Cursor:
    rowcount = 17

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, query, parameters):
        text = query.as_string() if hasattr(query, "as_string") else query
        if text.count("%s") != len(parameters):
            raise AssertionError(
                f"{text.count('%s')} placeholders for {len(parameters)} parameters"
            )


class _Connection:
    def cursor(self):
        return _Cursor()


class FeatureConfigTest(unittest.TestCase):
    def test_project_feature_config_loads(self) -> None:
        root = Path(__file__).resolve().parents[1]
        config = load_feature_config(root / "config/features/clean.yaml")

        self.assertEqual(config.name, "clean_observed")
        self.assertEqual(config.color_order, ("u", "g", "r", "i", "z", "y"))
        self.assertEqual(len(config.color_pairs), 15)
        self.assertEqual(len(config.groups["adjacent_colors"]), 5)

    def test_cli_accepts_features_command(self) -> None:
        args = _parser().parse_args(
            ["features", "--config", "config/features/clean.yaml"]
        )
        self.assertEqual(args.command, "features")

    def test_rejects_inconsistent_all_color_group(self) -> None:
        source_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "pyproject.toml").write_text("[project]\n", encoding="ascii")
            shutil.copytree(source_root / "config", root / "config")
            path = root / "config/features/clean.yaml"
            contents = path.read_text(encoding="utf-8").replace(
                "    - z_y\n", "    - z_i\n"
            )
            path.write_text(contents, encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "all_colors"):
                load_feature_config(path)

    def test_insert_queries_have_matching_parameters(self) -> None:
        root = Path(__file__).resolve().parents[1]
        config = load_feature_config(root / "config/features/clean.yaml")
        by_band = {item.band: item for item in config.bands}

        magnitude_count = _insert_magnitude(
            _Connection(), 2, 3, "mag_u", by_band["u"]
        )
        color_count = _insert_color(
            _Connection(), 2, 3, "u_g", by_band["u"], by_band["g"]
        )

        self.assertEqual(magnitude_count, 17)
        self.assertEqual(color_count, 17)


if __name__ == "__main__":
    unittest.main()
