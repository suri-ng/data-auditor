import unittest

import pandas as pd

from auditor.outliers import detect_outliers_iqr


class IqrOutlierTest(unittest.TestCase):
    def test_flags_values_outside_iqr_bounds_with_source_position(self):
        df = pd.DataFrame({"amount": [1, 1, 1, 1, 100]}, index=[4, 4, 5, 6, 6])

        result = detect_outliers_iqr(df, {"amount": "integer"})[0]

        self.assertEqual(result["classification"], "outliers_detected")
        self.assertEqual(result["metrics"]["finding_count"], 1)
        self.assertEqual(result["findings"][0]["row_position"], 4)
        self.assertEqual(result["findings"][0]["row_index"], 6)
        self.assertEqual(result["metrics"]["upper_bound"], 1)

    def test_non_numeric_column_is_skipped(self):
        result = detect_outliers_iqr(
            pd.DataFrame({"value": ["1", "100"]}), {"value": "string"}
        )[0]

        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["classification"], "not_numeric")
        self.assertEqual(result["metrics"]["values_tested"], 0)

    def test_invalid_and_missing_numeric_columns_are_distinguished(self):
        df = pd.DataFrame({"invalid": ["bad"], "missing": [None]})

        invalid, missing = detect_outliers_iqr(
            df, {"invalid": "float", "missing": "integer"}
        )

        self.assertEqual(invalid["classification"], "no_valid_numeric_values")
        self.assertEqual(invalid["metrics"]["values_present"], 1)
        self.assertEqual(missing["classification"], "no_nonmissing_values")
        self.assertEqual(missing["metrics"]["values_present"], 0)

    def test_valid_data_without_outliers_is_complete(self):
        result = detect_outliers_iqr(
            pd.DataFrame({"value": [1, 2, 3, 4, 5]}), {"value": "float"}
        )[0]

        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["classification"], "no_outliers_detected")
        self.assertEqual(result["findings"], [])


if __name__ == "__main__":
    unittest.main()
