import unittest
import numpy as np
from glob_umap.compute.types import MatrixData, StableKey


class TestStableKey(unittest.TestCase):
    """Verify stable keys sort by catalogue, file, and row."""

    def test_stable_key_order(self):
        expected = (
            StableKey("a", "file_a", 1),
            StableKey("a", "file_a", 2),
            StableKey("a", "file_b", 1),
            StableKey("b", "file_a", 1),
        )

        unordered = (
            expected[3],
            expected[1],
            expected[2],
            expected[0],
        )

        self.assertEqual(tuple(sorted(unordered)), expected)


class TestMatrixData(unittest.TestCase):
    """Verify the basic structure of a small feature matrix."""

    def test_matrix_data_properties(self):
        feature_names = ("u_g", "g_r", "r_i", "i_z", "z_y")

        stable_keys = (
            StableKey("fds_aa_639_a136", "fds.csv", 1),
            StableKey("fds_aa_639_a136", "fds.csv", 2),
        )

        matrix_data = MatrixData(
            object_ids=np.array([101, 102], dtype=np.int64),
            stable_keys=stable_keys,
            labels=np.array(["galaxy", "star"], dtype=np.str_),
            values=np.zeros((2, 5), dtype=np.float64),
            feature_names=feature_names,
        )

        self.assertEqual(matrix_data.object_ids.shape, (2,))
        self.assertEqual(len(matrix_data.stable_keys), 2)
        self.assertEqual(matrix_data.labels.shape, (2,))
        self.assertEqual(matrix_data.values.shape, (2, 5))
        self.assertEqual(matrix_data.feature_names, feature_names)


if __name__ == "__main__":
    unittest.main()
