import json
import os
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import psycopg
from psycopg.types.json import Jsonb

from glob_umap.binding import bind_records
from glob_umap.feature import build_features
from glob_umap.phot import normalize_photometry
from glob_umap.plan import freeze_plan
from glob_umap.source import file_sha256


ROOT = Path(__file__).resolve().parents[1]
TEST_DATABASE = "gc_ml_test"
SCHEMA_FILES = (
    "10_schemas.sql",
    "20_raw.sql",
    "30_core.sql",
    "31_object_origin.sql",
    "32_label_evidence.sql",
    "40_ml.sql",
    "41_member_record.sql",
    "42_feature.sql",
)


class PipelineIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        requested = os.environ.get("GC_ML_TEST_DATABASE")
        if requested is None:
            raise unittest.SkipTest(
                "Set GC_ML_TEST_DATABASE=gc_ml_test to run PostgreSQL integration tests"
            )
        if requested != TEST_DATABASE:
            raise RuntimeError(
                f"Integration tests may use only {TEST_DATABASE}; received {requested}"
            )

        cls.previous_database = os.environ.get("PGDATABASE")
        try:
            with psycopg.connect("", dbname=requested) as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT current_database(), current_user")
                    database, user = cursor.fetchone()
                if database != TEST_DATABASE:
                    raise RuntimeError(
                        f"Refusing to reset unexpected database {database}"
                    )
                if user != "gc":
                    raise RuntimeError(
                        f"Integration database must be accessed as gc; received {user}"
                    )
                cls._reset_schema(connection)
                cls._seed_fixture(connection)
        except Exception:
            cls._restore_database_environment()
            raise

        os.environ["PGDATABASE"] = TEST_DATABASE

    @classmethod
    def tearDownClass(cls) -> None:
        cls._restore_database_environment()

    @classmethod
    def _restore_database_environment(cls) -> None:
        previous = getattr(cls, "previous_database", None)
        if previous is None:
            os.environ.pop("PGDATABASE", None)
        else:
            os.environ["PGDATABASE"] = previous

    @classmethod
    def _reset_schema(cls, connection: psycopg.Connection) -> None:
        with connection.cursor() as cursor:
            cursor.execute("DROP SCHEMA IF EXISTS ml CASCADE")
            cursor.execute("DROP SCHEMA IF EXISTS core CASCADE")
            cursor.execute("DROP SCHEMA IF EXISTS raw CASCADE")
            for name in SCHEMA_FILES:
                cursor.execute((ROOT / "sql" / name).read_text(encoding="utf-8"))

    @classmethod
    def _seed_fixture(cls, connection: psycopg.Connection) -> None:
        source_files = {
            "fds_aa_639_a136": "integration_fds.csv",
            "des_dr2_fornax": "integration_des.csv",
        }
        catalogue_ids: dict[str, int] = {}
        with connection.cursor() as cursor:
            for index, (code, source_file) in enumerate(source_files.items(), start=1):
                cursor.execute(
                    """
                    INSERT INTO core.catalog (
                        code, title, release, source_url, local_path, sha256,
                        expected_rows, loaded_rows, loaded_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, 6, 6, CURRENT_TIMESTAMP)
                    RETURNING catalog_id
                    """,
                    (
                        code,
                        f"Integration fixture {code}",
                        "test",
                        "https://example.invalid/integration-fixture",
                        source_file,
                        str(index) * 64,
                    ),
                )
                catalogue_ids[code] = int(cursor.fetchone()[0])

            fds_records: list[int] = []
            des_records: list[int] = []
            for source_row in range(1, 7):
                magnitudes = [20.0] * 6
                if source_row > 1:
                    position = source_row - 2
                    magnitudes[position] += source_row / 10.0
                u, g, r, i, z, y = magnitudes
                ra = 54.60 + source_row / 1000.0
                dec = -35.45 + source_row / 1000.0

                cursor.execute(
                    """
                    INSERT INTO raw.fds (
                        source_file, source_row, source_id, ra_j2000,
                        dec_j2000, u_mag, u_mag_err, ebv
                    ) VALUES (%s, %s, %s, %s, %s, %s, 0.01, 0.02)
                    RETURNING ingest_id
                    """,
                    (
                        source_files["fds_aa_639_a136"],
                        source_row,
                        f"FDS_TEST_{source_row}",
                        ra,
                        dec,
                        u,
                    ),
                )
                fds_ingest_id = int(cursor.fetchone()[0])
                cursor.execute(
                    """
                    INSERT INTO core.record (
                        catalog_id, source_key, ra_deg, dec_deg, raw_ingest_id
                    ) VALUES (%s, %s, %s, %s, %s)
                    RETURNING record_id
                    """,
                    (
                        catalogue_ids["fds_aa_639_a136"],
                        json.dumps(
                            [source_files["fds_aa_639_a136"], source_row]
                        ),
                        ra,
                        dec,
                        fds_ingest_id,
                    ),
                )
                fds_records.append(int(cursor.fetchone()[0]))

                cursor.execute(
                    """
                    INSERT INTO raw.des (
                        source_file, source_row, coadd_object_id, ra, dec,
                        ra_window, dec_window, ebv_sfd98,
                        g_mag_ap5, g_mag_ap5_err,
                        r_mag_ap5, r_mag_ap5_err,
                        i_mag_ap5, i_mag_ap5_err,
                        z_mag_ap5, z_mag_ap5_err,
                        y_mag_ap5, y_mag_ap5_err
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, 0.02,
                        %s, 0.01, %s, 0.01, %s, 0.01,
                        %s, 0.01, %s, 0.01
                    )
                    RETURNING ingest_id
                    """,
                    (
                        source_files["des_dr2_fornax"],
                        source_row,
                        1000 + source_row,
                        ra,
                        dec,
                        ra,
                        dec,
                        g,
                        r,
                        i,
                        z,
                        y,
                    ),
                )
                des_ingest_id = int(cursor.fetchone()[0])
                cursor.execute(
                    """
                    INSERT INTO core.record (
                        catalog_id, source_key, ra_deg, dec_deg, raw_ingest_id
                    ) VALUES (%s, %s, %s, %s, %s)
                    RETURNING record_id
                    """,
                    (
                        catalogue_ids["des_dr2_fornax"],
                        json.dumps(
                            [source_files["des_dr2_fornax"], source_row]
                        ),
                        ra,
                        dec,
                        des_ingest_id,
                    ),
                )
                des_records.append(int(cursor.fetchone()[0]))

            object_ids: list[int] = []
            for record_id, source_row in zip(fds_records, range(1, 7), strict=True):
                cursor.execute(
                    """
                    INSERT INTO core.object (origin_record_id, ra_deg, dec_deg)
                    VALUES (%s, %s, %s)
                    RETURNING object_id
                    """,
                    (
                        record_id,
                        54.60 + source_row / 1000.0,
                        -35.45 + source_row / 1000.0,
                    ),
                )
                object_ids.append(int(cursor.fetchone()[0]))

            cursor.execute(
                """
                INSERT INTO core.match_run (
                    name, method, config_path, config_sha256, resolved_config
                ) VALUES (%s, %s, %s, %s, %s)
                RETURNING match_run_id
                """,
                (
                    "fds_des_1arcsec",
                    "unit_sphere_kdtree",
                    "config/matches/fds_des.yaml",
                    file_sha256(ROOT / "config/matches/fds_des.yaml"),
                    Jsonb({"integration_fixture": True}),
                ),
            )
            match_run_id = int(cursor.fetchone()[0])

            for object_id, record_id in zip(object_ids, des_records, strict=True):
                cursor.execute(
                    """
                    INSERT INTO core.match (
                        match_run_id, object_id, record_id,
                        angular_sep_arcsec, method, search_radius_arcsec,
                        candidate_count, candidate_rank, selected, ambiguous
                    ) VALUES (%s, %s, %s, 0.1, %s, 1.0, 1, 1, false, false)
                    """,
                    (
                        match_run_id,
                        object_id,
                        record_id,
                        "unit_sphere_kdtree",
                    ),
                )

            cursor.execute(
                """
                INSERT INTO ml.sample (
                    name, description, config_path, config_sha256, definition
                ) VALUES (%s, %s, %s, %s, %s)
                RETURNING sample_id
                """,
                (
                    "clean_reciprocal",
                    "Six-object PostgreSQL integration fixture",
                    "config/samples/clean.yaml",
                    file_sha256(ROOT / "config/samples/clean.yaml"),
                    Jsonb({"split": {"assignment_sha256": "a" * 64}}),
                ),
            )
            sample_id = int(cursor.fetchone()[0])
            memberships = (
                (object_ids[0], "train", "globular_cluster"),
                (object_ids[1], "test", "globular_cluster"),
                (object_ids[2], "train", "galaxy"),
                (object_ids[3], "test", "galaxy"),
                (object_ids[4], "train", "star"),
                (object_ids[5], "test", "star"),
            )
            for object_id, split, target_class in memberships:
                cursor.execute(
                    """
                    INSERT INTO ml.member (
                        sample_id, object_id, split, target_class, weight
                    ) VALUES (%s, %s, %s, %s, 1.0)
                    """,
                    (sample_id, object_id, split, target_class),
                )

    def test_bind_phot_features_and_plan(self) -> None:
        reports: list[str] = []
        with ExitStack() as patches:
            for module in ("binding", "phot", "feature", "plan"):
                patches.enter_context(
                    patch(f"glob_umap.{module}.write_manifest")
                )
            bind_records(ROOT / "config/bindings/clean.yaml", reports.append)
            normalize_photometry(ROOT / "config/core/phot.yaml", reports.append)
            build_features(ROOT / "config/features/clean.yaml", reports.append)
            freeze_plan(ROOT / "config/exp/core.yaml", reports.append)

        with psycopg.connect("") as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT count(*) FROM ml.member_record")
                self.assertEqual(cursor.fetchone()[0], 12)
                cursor.execute("SELECT count(*) FROM core.phot")
                self.assertEqual(cursor.fetchone()[0], 36)
                cursor.execute("SELECT count(*) FROM ml.feature")
                self.assertEqual(cursor.fetchone()[0], 126)
                cursor.execute(
                    """
                    SELECT feature_sha256,
                           definition #>> '{audit,color_matrix,numerical_rank}'
                    FROM ml.feature_set
                    WHERE name = 'clean_observed'
                    """
                )
                feature_sha256, numerical_rank = cursor.fetchone()
                self.assertEqual(len(feature_sha256), 64)
                self.assertEqual(numerical_rank, "5")
                cursor.execute(
                    """
                    SELECT definition ? 'records',
                           definition ? 'photometry'
                    FROM ml.sample
                    WHERE name = 'clean_reciprocal'
                    """
                )
                self.assertEqual(cursor.fetchone(), (True, True))

        self.assertTrue(
            any(line.startswith("Frozen evaluation plan:") for line in reports)
        )


if __name__ == "__main__":
    unittest.main()
