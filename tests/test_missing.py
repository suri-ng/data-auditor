import unittest

import pandas as pd

from auditor.profiler import detect_missing_values, profile_dataset


class MissingValueTest(unittest.TestCase):
    def test_null_empty_and_common_text_markers_are_detected(self):
        df = pd.DataFrame({
            "value": [None, float("nan"), "", "  ", " N/A ", "NULL", "none", "empty", "ok"]
        })

        results = detect_missing_values(df)
        summary, profile = profile_dataset(df)
        result = results[0]

        self.assertEqual(
            [finding["row_position"] for finding in result["findings"]],
            list(range(8)),
        )
        self.assertEqual(result["metrics"]["values_present"], 1)
        self.assertEqual(result["metrics"]["finding_percentage"], 88.89)
        self.assertEqual(summary["number_of_rows"], 9)
        self.assertEqual(profile.loc[0, "missing_count"], 8)
        self.assertEqual(profile.loc[0, "non_missing_count"], 1)

    def test_clean_column_has_zero_missing_findings(self):
        result = detect_missing_values(pd.DataFrame({"value": [0, False, "text"]}))[0]

        self.assertEqual(result["classification"], "no_missing_values")
        self.assertEqual(result["metrics"]["finding_count"], 0)

    def test_empty_dataframe_returns_empty_profile(self):
        summary, profile = profile_dataset(pd.DataFrame())

        self.assertEqual(summary, {
            "number_of_rows": 0,
            "number_of_columns": 0,
            "duplicate_rows": 0,
        })
        self.assertEqual(len(profile), 0)


if __name__ == "__main__":
    unittest.main()
