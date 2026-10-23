import unittest

import pandas as pd

from auditor.profiler import detect_duplicate_rows, profile_dataset


class DuplicateRowsTest(unittest.TestCase):
    def test_only_repeated_copies_are_reported_with_positions(self):
        df = pd.DataFrame(
            {"item": ["a", "b", "a", "a"], "quantity": [1, 2, 1, 1]},
            index=[7, 7, 9, 7],
        )

        result = detect_duplicate_rows(df)
        summary, _ = profile_dataset(df)

        self.assertEqual(
            [finding["row_position"] for finding in result["findings"]], [2, 3]
        )
        self.assertEqual(
            [finding["row_index"] for finding in result["findings"]], [9, 7]
        )
        self.assertEqual(result["metrics"]["finding_count"], 2)
        self.assertEqual(summary["duplicate_rows"], 2)

    def test_unique_rows_have_no_duplicate_findings(self):
        df = pd.DataFrame({"item": ["a", "b"], "quantity": [1, 2]})

        result = detect_duplicate_rows(df)

        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["classification"], "no_duplicate_rows")
        self.assertEqual(result["findings"], [])


if __name__ == "__main__":
    unittest.main()
