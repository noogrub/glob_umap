import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from glob_umap.cli import _parser
from glob_umap.label import (
    _insert_des_class,
    _insert_master_photometric,
    _insert_master_spectroscopic,
    _insert_spec_spectroscopic,
)
from glob_umap.label_config import load_label_config


class LabelConfigTest(unittest.TestCase):
    def test_project_label_config_loads(self) -> None:
        root = Path(__file__).resolve().parents[1]
        config = load_label_config(root / "config/core/labels.yaml")

        self.assertEqual(config.name, "fornax_label_evidence")
        self.assertEqual(config.materialization.sample.name, "clean_reciprocal")
        self.assertEqual(config.master_catalog, "fds_gc_master")
        self.assertEqual(config.spec_catalog, "chaturvedi_aa_657_a93")
        self.assertEqual(
            {
                config.master_photometric_evidence,
                config.master_spectroscopic_evidence,
                config.spec_spectroscopic_evidence,
                config.des_morphology_evidence,
            },
            {
                "acsfcs_photometric",
                "catalogue_spectroscopic",
                "chaturvedi_spectroscopic",
                "des_extended_class",
            },
        )

    def test_rejects_duplicate_evidence_names(self) -> None:
        source_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "pyproject.toml").write_text("[project]\n", encoding="ascii")
            shutil.copytree(source_root / "config", root / "config")
            path = root / "config/core/labels.yaml"
            contents = path.read_text(encoding="utf-8").replace(
                "spec_spectroscopic: chaturvedi_spectroscopic",
                "spec_spectroscopic: catalogue_spectroscopic",
            )
            path.write_text(contents, encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Evidence names"):
                load_label_config(path)

    def test_cli_accepts_labels_command(self) -> None:
        args = _parser().parse_args(
            ["labels", "--config", "config/core/labels.yaml"]
        )
        self.assertEqual(args.command, "labels")

    def test_insert_queries_have_matching_parameters(self) -> None:
        root = Path(__file__).resolve().parents[1]
        config = load_label_config(root / "config/core/labels.yaml")
        functions = (
            lambda: _insert_master_photometric(None, config),
            lambda: _insert_master_spectroscopic(None, config),
            lambda: _insert_spec_spectroscopic(None, config),
            lambda: _insert_des_class(
                None,
                config,
                config.materialization.sample.galaxy,
                config.materialization.galaxy_target_class,
            ),
        )
        for function in functions:
            with patch("glob_umap.label._execute_insert", return_value=0) as execute:
                function()
            query, parameters = execute.call_args.args[1:]
            sql_text = query.as_string()
            self.assertEqual(sql_text.count("%s"), len(parameters))
            if "jsonb_build_object" in sql_text and "match_run" in sql_text:
                self.assertIn("'match_run', %s::text", sql_text)
                self.assertIn("'match_policy', %s::text", sql_text)


if __name__ == "__main__":
    unittest.main()
