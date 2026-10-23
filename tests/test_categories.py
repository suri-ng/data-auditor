import unittest

import pandas as pd

from auditor.category import detect_category_issues


class RareCategoryTest(unittest.TestCase):
    def test_category_occurring_below_one_percent_is_reported(self):
        df = pd.DataFrame({"group": ["common"] * 199 + ["rare"]})

        result = detect_category_issues(df, {"group": "string"})[0]

        self.assertEqual(result["classification"], "rare_categories_detected")
        self.assertEqual(result["metrics"]["finding_count"], 1)
        self.assertEqual(result["findings"][0]["row_position"], 199)
        self.assertEqual(result["findings"][0]["value"], "rare")

    def test_category_at_one_percent_is_not_rare(self):
        df = pd.DataFrame({"group": ["common"] * 198 + ["rare"] * 2})

        result = detect_category_issues(df, {"group": "string"})[0]

        self.assertEqual(result["classification"], "no_rare_categories")
        self.assertEqual(result["metrics"]["finding_count"], 0)

    def test_missing_values_do_not_change_category_frequency(self):
        df = pd.DataFrame({"group": ["common"] * 100 + ["rare", None]})

        result = detect_category_issues(df, {"group": "string"})[0]

        self.assertEqual(result["metrics"]["values_present"], 101)
        self.assertEqual(result["findings"][0]["row_position"], 100)

    def test_non_string_and_high_cardinality_columns_are_skipped(self):
        df = pd.DataFrame({
            "number": ["1"] * 20,
            "many": [f"item-{index}" for index in range(20)],
        })

        results = detect_category_issues(
            df, {"number": "integer", "many": "string"}
        )

        self.assertEqual(results[0]["classification"], "not_string")
        self.assertEqual(results[1]["classification"], "high_cardinality")
        self.assertEqual(results[1]["metrics"]["cardinality_ratio"], 1.0)

    def test_all_missing_string_column_is_skipped(self):
        result = detect_category_issues(
            pd.DataFrame({"group": [None, " n/a "]}), {"group": "string"}
        )[0]

        self.assertEqual(result["classification"], "no_nonmissing_values")
        self.assertEqual(result["metrics"]["values_tested"], 0)


if __name__ == "__main__":
    unittest.main()
