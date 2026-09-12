import inspect
import unittest

from glob_umap.phot import _phot_sha256


class PhotQueryTest(unittest.TestCase):
    def test_digest_orders_by_source_key_row_expression(self) -> None:
        source = inspect.getsource(_phot_sha256)

        self.assertIn("(r.source_key::jsonb ->> 1)::bigint", source)
        self.assertNotIn("source_row::bigint", source)


if __name__ == "__main__":
    unittest.main()
