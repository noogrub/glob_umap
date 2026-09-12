import shutil
import tempfile
import unittest
from pathlib import Path

from glob_umap.cli import _parser
from glob_umap.experiment_config import load_experiment_config


class ExperimentConfigTest(unittest.TestCase):
    def test_project_experiment_config_loads(self) -> None:
        root = Path(__file__).resolve().parents[1]
        config = load_experiment_config(root / "config/exp/core.yaml")

        self.assertEqual(config.name, "clean_representation_comparison")
        self.assertEqual(config.focal_class, "globular_cluster")
        self.assertEqual(config.target_recall, 0.30)
        self.assertEqual(
            {item.method for item in config.representations},
            {"identity", "pca", "umap"},
        )

    def test_cli_accepts_plan_command(self) -> None:
        args = _parser().parse_args(
            ["plan", "--config", "config/exp/core.yaml"]
        )
        self.assertEqual(args.command, "plan")

    def test_rejects_test_selected_threshold(self) -> None:
        source_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "pyproject.toml").write_text("[project]\n", encoding="ascii")
            shutil.copytree(source_root / "config", root / "config")
            path = root / "config/exp/core.yaml"
            contents = path.read_text(encoding="utf-8").replace(
                "threshold_source: out_of_fold_development_predictions",
                "threshold_source: final_test_predictions",
            )
            path.write_text(contents, encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "threshold_source"):
                load_experiment_config(path)


if __name__ == "__main__":
    unittest.main()
