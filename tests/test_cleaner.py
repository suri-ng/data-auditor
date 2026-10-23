import unittest

import pandas as pd

from auditor.data_type import convert_confirmed_values


class ConfirmedValueConversionTest(unittest.TestCase):
    def test_converts_each_supported_type_and_keeps_missing_values_null(self):
        values = pd.Series(["1", "", " n/a "], name="value", dtype="object")

        integer = convert_confirmed_values(values, "integer")
        floating = convert_confirmed_values(pd.Series(["1.5", "bad"]), "float")
        boolean = convert_confirmed_values(
            pd.Series([" YES ", "no", "maybe"]), "boolean"
        )
        text = convert_confirmed_values(values, "string")

        self.assertEqual(integer.iloc[0], 1)
        self.assertTrue(pd.isna(integer.iloc[1]))
        self.assertTrue(pd.isna(integer.iloc[2]))
        self.assertEqual(floating.iloc[0], 1.5)
        self.assertTrue(pd.isna(floating.iloc[1]))
        self.assertEqual(boolean.iloc[:2].tolist(), [True, False])
        self.assertTrue(pd.isna(boolean.iloc[2]))
        self.assertEqual(text.iloc[0], "1")
        self.assertTrue(pd.isna(text.iloc[1]))

    def test_integer_conversion_rejects_fractional_boolean_and_infinite_values(self):
        source = pd.Series(["2.0", "2.5", True, "inf"], dtype="object")

        converted = convert_confirmed_values(source, "integer")

        self.assertEqual(converted.iloc[0], 2)
        self.assertTrue(converted.iloc[1:].isna().all())
        self.assertEqual(source.tolist(), ["2.0", "2.5", True, "inf"])

    def test_unsupported_type_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unsupported confirmed type"):
            convert_confirmed_values(pd.Series(["x"]), "currency")


if __name__ == "__main__":
    unittest.main()
