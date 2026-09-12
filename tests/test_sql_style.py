import re
import unittest
from pathlib import Path


class SqlStyleTest(unittest.TestCase):
    def test_project_queries_use_explicit_join_keys(self) -> None:
        source_root = Path(__file__).resolve().parents[1] / "src/glob_umap"
        forbidden = re.compile(r"\bNATURAL\s+JOIN\b|\bUSING\s*\(", re.IGNORECASE)

        violations = []
        for path in sorted(source_root.glob("*.py")):
            if forbidden.search(path.read_text(encoding="utf-8")):
                violations.append(path.name)

        self.assertEqual(violations, [])


if __name__ == "__main__":
    unittest.main()
