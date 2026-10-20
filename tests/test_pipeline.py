import unittest

import pandas as pd

from auditor.data_type import detect_type_issues, suggest_types
from auditor.pipeline import prepare_audit, run_auditor


class ConfirmedTypesTest(unittest.TestCase):
    def test_every_column_requires_a_confirmed_type(self):
        df = pd.DataFrame({"amount": ["1", "bad"], "label": ["a", "b"]})

        with self.assertRaisesRegex(ValueError, "missing columns"):
            run_auditor(df, {"amount": "float"})
        with self.assertRaisesRegex(ValueError, "unsupported choices"):
            run_auditor(df, {"amount": "numeric", "label": "string"})

    def test_confirmation_controls_validation_and_iqr(self):
        df = pd.DataFrame({"amount": ["10", "10", "10", "100", "bad"]})

        numeric = run_auditor(df, {"amount": "integer"})
        self.assertEqual(numeric["type_report"][0]["invalid_values"], ["bad"])
        self.assertTrue(numeric["outliers_report"][0]["check_performed"])
        self.assertEqual(numeric["outliers_report"][0]["outlier_values"], ["100"])

        text = run_auditor(df, {"amount": "string"})
        self.assertEqual(text["type_report"][0]["invalid_count"], 0)
        self.assertFalse(text["outliers_report"][0]["check_performed"])

    def test_suggestions_are_separate_from_validation(self):
        df = pd.DataFrame({"amount": ["1", "2"]})
        preview = prepare_audit(df)
        self.assertEqual(preview["dataset_summary"]["number_of_rows"], 2)
        self.assertEqual(preview["type_suggestions"][0]["suggested_type"], "integer")
        self.assertEqual(suggest_types(df)[0]["suggested_type"], "integer")
        self.assertEqual(detect_type_issues(df, {"amount": "float"})[0]["expected_type"], "float")

    def test_category_detection_uses_confirmed_type_without_rules(self):
        df = pd.DataFrame({"code": ["1"] * 199 + ["2"]})

        text = run_auditor(df, {"code": "string"})
        self.assertEqual(text["category_report"][0]["rare_categories"]["rare_category_count"], 1)

        numeric = run_auditor(df, {"code": "integer"})
        self.assertEqual(
            numeric["category_report"][0]["is_categorical"]["classification"],
            "not_selected_as_categorical",
        )


if __name__ == "__main__":
    unittest.main()
