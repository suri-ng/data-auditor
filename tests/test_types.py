import unittest

import numpy as np
import pandas as pd

from auditor.data_type import (
    SUPPORTED_TYPES,
    detect_type_issues,
    suggest_types,
    validate_expected_type,
)


class TypeValidationTest(unittest.TestCase):
    def test_supported_confirmed_types_are_checked(self):
        df = pd.DataFrame({
            "label": ["alpha", None],
            "count": ["12", "bad"],
            "score": ["1.5", "2.0"],
            "active": ["yes", "perhaps"],
            "event_date": ["2024-01-01", "not-a-date"],
        })

        results = detect_type_issues(df, {
            "label": "string",
            "count": "integer",
            "score": "float",
            "active": "boolean",
            "event_date": "date",
        })

        self.assertEqual(SUPPORTED_TYPES, {
            "string", "integer", "float", "boolean", "date"
        })
        self.assertEqual([result["metrics"]["finding_count"] for result in results], [0, 1, 0, 1, 1])
        self.assertEqual([result["metrics"]["expected_type"] for result in results], [
            "string", "integer", "float", "boolean", "date"
        ])

    def test_incompatible_numeric_values_include_bool_nan_and_infinity(self):
        values = pd.Series(["2", "2.5", True, np.inf, "bad"], dtype="object")

        result = validate_expected_type(values, "integer")

        self.assertEqual(
            [finding["row_position"] for finding in result["findings"]], [1, 2, 3, 4]
        )
        self.assertEqual(result["metrics"]["finding_percentage"], 80.0)

    def test_confirmation_mapping_must_be_exact_and_use_supported_types(self):
        df = pd.DataFrame({"left": [1], "right": [2]})

        with self.assertRaisesRegex(ValueError, "missing columns"):
            detect_type_issues(df, {"left": "integer"})
        with self.assertRaisesRegex(ValueError, "unknown columns"):
            detect_type_issues(df, {
                "left": "integer", "right": "integer", "extra": "string"
            })
        with self.assertRaisesRegex(ValueError, "unsupported choices"):
            detect_type_issues(df, {"left": "integer", "right": "decimal"})
        with self.assertRaisesRegex(ValueError, "column-to-type dictionary"):
            detect_type_issues(df, [("left", "integer")])

    def test_type_suggestions_cover_empty_identifier_numeric_and_text_columns(self):
        df = pd.DataFrame({
            "empty": [None, ""],
            "customer_id": ["001", "002"],
            "amount": ["2", "3"],
            "description": ["blue", "green"],
        })

        suggestions = {item["column"]: item for item in suggest_types(df)}

        self.assertEqual(suggestions["empty"]["suggested_type"], "unknown")
        self.assertEqual(suggestions["customer_id"]["suggested_type"], "string")
        self.assertEqual(suggestions["customer_id"]["classification"], "safeguarded suggestion")
        self.assertEqual(suggestions["amount"]["suggested_type"], "integer")
        self.assertEqual(suggestions["description"]["suggested_type"], "string")

    def test_boolean_and_date_column_names_help_resolve_ambiguous_values(self):
        df = pd.DataFrame({
            "is_active": ["0", "1"],
            "event_date": ["2024-01-01", "2024-01-02"],
        })

        suggestions = {item["column"]: item for item in suggest_types(df)}

        self.assertEqual(suggestions["is_active"]["suggested_type"], "boolean")
        self.assertEqual(suggestions["event_date"]["suggested_type"], "date")


if __name__ == "__main__":
    unittest.main()
