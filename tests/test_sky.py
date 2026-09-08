import unittest

import numpy as np

from glob_umap.sky import candidate_batches, unit_vectors


class SkyTest(unittest.TestCase):
    def test_unit_vectors_wrap_right_ascension(self) -> None:
        vectors = unit_vectors(np.array([0.0, 360.0]), np.array([0.0, 0.0]))
        np.testing.assert_allclose(vectors[0], vectors[1], atol=1e-14)

    def test_candidate_search_keeps_and_ranks_all_candidates(self) -> None:
        batches = list(
            candidate_batches(
                reference_ids=np.array([10, 20]),
                reference_ra_deg=np.array([359.9999, 359.9999]),
                reference_dec_deg=np.array([0.0, 0.0]),
                target_ids=np.array([30]),
                target_ra_deg=np.array([0.0001]),
                target_dec_deg=np.array([0.0]),
                radius_arcsec=1.0,
                chunk_rows=1,
                workers=1,
            )
        )
        rows = batches[0][2]
        self.assertEqual([(row[0], row[1]) for row in rows], [(30, 10), (30, 20)])
        self.assertEqual([row[3] for row in rows], [2, 2])
        self.assertEqual([row[4] for row in rows], [1, 2])
        self.assertAlmostEqual(rows[0][2], 0.72, places=3)

    def test_candidate_search_preserves_empty_chunks(self) -> None:
        batches = list(
            candidate_batches(
                reference_ids=np.array([10]),
                reference_ra_deg=np.array([10.0]),
                reference_dec_deg=np.array([0.0]),
                target_ids=np.array([20, 30]),
                target_ra_deg=np.array([20.0, 30.0]),
                target_dec_deg=np.array([0.0, 0.0]),
                radius_arcsec=1.0,
                chunk_rows=1,
                workers=1,
            )
        )
        self.assertEqual(
            [(start, stop) for start, stop, _ in batches],
            [(0, 1), (1, 2)],
        )
        self.assertEqual([rows for _, _, rows in batches], [[], []])


if __name__ == "__main__":
    unittest.main()
