import unittest

import pandas as pd

from auditor.data_type import convert_confirmed_values, validate_expected_type


class DateValidationTest(unittest.TestCase):
    def test_parses_supported_date_strings_and_marks_invalid_values(self):
        values = pd.Series(
            ["2024-02-29", " 2024/03/01 ", "not-a-date", "", "20240229"],
            name="event_date",
        )

        converted = convert_confirmed_values(values, "date")
        result = validate_expected_type(values, "date")

        self.assertEqual(converted.iloc[0], pd.Timestamp("2024-02-29"))
        self.assertEqual(converted.iloc[1], pd.Timestamp("2024-03-01"))
        self.assertTrue(converted.iloc[2:].isna().all())
        self.assertEqual(
            [finding["row_position"] for finding in result["findings"]], [2, 4]
        )
        self.assertEqual(result["metrics"]["values_present"], 4)

    def test_all_missing_dates_are_skipped(self):
        result = validate_expected_type(
            pd.Series([None, "", " n/a "]), "date"
        )

        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["classification"], "no_nonmissing_values")
        self.assertEqual(result["metrics"]["finding_count"], 0)

    def test_datetime_values_are_supported_but_numeric_date_codes_are_not(self):
        values = pd.Series(
            [pd.Timestamp("2024-01-01"), "2024-01-02", 20240103], dtype="object"
        )

        result = validate_expected_type(values, "date")

        self.assertEqual([finding["row_position"] for finding in result["findings"]], [2])


if __name__ == "__main__":
    unittest.main()
