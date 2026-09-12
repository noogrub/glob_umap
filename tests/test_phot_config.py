import shutil
import tempfile
import unittest
from pathlib import Path

from glob_umap.cli import _parser
from glob_umap.phot import _insert_measurement
from glob_umap.phot_config import load_phot_config


class _Cursor:
    def __init__(self, results):
        self.results = results
        self.rowcount = 0

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
        result = self.results.pop(0)
        self._row = result.get("row")
        self.rowcount = result.get("rowcount", 0)

    def fetchone(self):
        return self._row


class _Connection:
    def __init__(self, results):
        self.results = results

    def cursor(self):
        return _Cursor(self.results)


class PhotConfigTest(unittest.TestCase):
    def test_project_photometry_config_loads(self) -> None:
        root = Path(__file__).resolve().parents[1]
        config = load_phot_config(root / "config/core/phot.yaml")

        self.assertEqual(config.name, "clean_observed_photometry")
        self.assertEqual(config.sample_name, "clean_reciprocal")
        self.assertEqual(config.reddening_mode, "observed")
        self.assertEqual(sum(len(item.measurements) for item in config.sources), 6)

    def test_cli_accepts_phot_command(self) -> None:
        args = _parser().parse_args(
            ["phot", "--config", "config/core/phot.yaml"]
        )
        self.assertEqual(args.command, "phot")

    def test_coefficient_mode_requires_every_coefficient(self) -> None:
        source_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "pyproject.toml").write_text("[project]\n", encoding="ascii")
            (root / "config/core").mkdir(parents=True)
            shutil.copy(
                source_root / "config/core/phot.yaml",
                root / "config/core/phot.yaml",
            )
            path = root / "config/core/phot.yaml"
            contents = path.read_text(encoding="utf-8").replace(
                "mode: observed", "mode: coefficient"
            )
            path.write_text(contents, encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "extinction_coefficient"):
                load_phot_config(path)

    def test_measurement_queries_have_matching_parameters(self) -> None:
        root = Path(__file__).resolve().parents[1]
        config = load_phot_config(root / "config/core/phot.yaml")
        source = config.sources[0]
        measurement = source.measurements[0]
        connection = _Connection(
            [
                {"row": (0,)},
                {"rowcount": 17},
                {"row": (17,)},
            ]
        )

        result = _insert_measurement(
            connection, config, source, measurement, sample_id=3
        )

        self.assertEqual(result["inserted"], 17)
        self.assertEqual(connection.results, [])


if __name__ == "__main__":
    unittest.main()
