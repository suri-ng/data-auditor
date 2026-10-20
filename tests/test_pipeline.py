import json
import unittest

import numpy as np
import pandas as pd

from auditor.data_type import detect_type_issues, suggest_types
from auditor.export import to_export_json
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
        type_check = numeric["checks"]["type"][0]
        iqr_check = numeric["checks"]["iqr"][0]
        self.assertEqual([finding["value"] for finding in type_check["findings"]], ["bad"])
        self.assertEqual(iqr_check["status"], "complete")
        self.assertEqual(iqr_check["metrics"]["values_tested"], 4)
        self.assertEqual([finding["value"] for finding in iqr_check["findings"]], ["100"])
        self.assertEqual(numeric["numeric_summary"].loc["count", "amount"], 4)

        text = run_auditor(df, {"amount": "string"})
        self.assertEqual(text["checks"]["type"][0]["metrics"]["finding_count"], 0)
        self.assertEqual(text["checks"]["iqr"][0]["status"], "skipped")
        self.assertEqual(text["checks"]["iqr"][0]["metrics"]["values_present"], 5)
        self.assertTrue(text["numeric_summary"].empty)

    def test_numeric_values_are_invalid_in_a_confirmed_date_column(self):
        df = pd.DataFrame({
            "event_date": pd.Series(
                [20240101, "20240102", "2024-01-03", pd.Timestamp("2024-01-04")],
                dtype="object",
            )
        })

        report = run_auditor(df, {"event_date": "date"})
        self.assertEqual(
            [finding["row_position"] for finding in report["checks"]["type"][0]["findings"]],
            [0, 1],
        )
        self.assertEqual(report["checks"]["type"][0]["metrics"]["finding_count"], 2)
        self.assertEqual(report["checks"]["iqr"][0]["status"], "skipped")

    def test_nonfinite_and_boolean_values_are_invalid_for_numeric_types(self):
        df = pd.DataFrame({"value": pd.Series(["1.5", "inf", True], dtype="object")})

        report = run_auditor(df, {"value": "float"})
        self.assertEqual(
            [finding["row_position"] for finding in report["checks"]["type"][0]["findings"]],
            [1, 2],
        )
        self.assertEqual(report["checks"]["iqr"][0]["metrics"]["values_tested"], 1)
        self.assertEqual(report["numeric_summary"].loc["count", "value"], 1)

    def test_suggestions_are_separate_from_validation(self):
        df = pd.DataFrame({"amount": ["1", "2"]})
        preview = prepare_audit(df)
        self.assertEqual(preview["dataset_summary"]["number_of_rows"], 2)
        self.assertEqual(preview["type_suggestions"][0]["suggested_type"], "integer")
        self.assertEqual(suggest_types(df)[0]["suggested_type"], "integer")
        self.assertEqual(
            detect_type_issues(df, {"amount": "float"})[0]["metrics"]["expected_type"],
            "float",
        )
        ambiguous = prepare_audit(pd.DataFrame({"value": ["0", "1"]}))
        self.assertEqual(ambiguous["type_suggestions"][0]["classification"], "ambiguous")

    def test_category_detection_uses_confirmed_type_without_rules(self):
        df = pd.DataFrame({"code": ["1"] * 199 + ["2"]})

        text = run_auditor(df, {"code": "string"})
        self.assertEqual(text["checks"]["category"][0]["metrics"]["finding_count"], 1)

        numeric = run_auditor(df, {"code": "integer"})
        self.assertEqual(
            numeric["checks"]["category"][0]["classification"],
            "not_string",
        )

    def test_empty_numeric_cases_are_distinct_and_share_one_shape(self):
        df = pd.DataFrame({"invalid": ["bad", "worse"], "missing": [None, "n/a"]})
        checks = run_auditor(df, {"invalid": "float", "missing": "integer"})["checks"]
        invalid_iqr, missing_iqr = checks["iqr"]

        self.assertEqual(invalid_iqr["classification"], "no_valid_numeric_values")
        self.assertEqual(invalid_iqr["metrics"]["values_present"], 2)
        self.assertEqual(missing_iqr["classification"], "no_nonmissing_values")
        self.assertEqual(missing_iqr["metrics"]["values_present"], 0)
        self.assertEqual(invalid_iqr.keys(), missing_iqr.keys())
        self.assertEqual(invalid_iqr["metrics"].keys(), missing_iqr["metrics"].keys())

    def test_every_check_has_common_fields_and_stable_row_positions(self):
        df = pd.DataFrame({"value": ["bad", "bad"]}, index=["same", "same"])
        checks = run_auditor(df, {"value": "integer"})["checks"]
        expected_keys = {
            "check", "column", "status", "classification", "reason", "metrics", "findings"
        }
        common_metrics = {
            "values_total", "values_present", "values_tested",
            "finding_count", "finding_percentage",
        }
        for results in checks.values():
            for result in results:
                self.assertEqual(set(result), expected_keys)
                self.assertTrue(common_metrics <= set(result["metrics"]))
                for finding in result["findings"]:
                    self.assertEqual(set(finding), {
                        "check", "column", "row_position", "row_index",
                        "value", "severity", "message",
                    })
        self.assertEqual(
            [finding["row_position"] for finding in checks["type"][0]["findings"]],
            [0, 1],
        )
        self.assertEqual(checks["duplicates"][0]["findings"][0]["row_position"], 1)

    def test_report_has_streamlit_ready_finding_totals(self):
        df = pd.DataFrame({
            "amount": ["bad", None, "10", "10"],
            "label": ["a", "a", "a", "a"],
        })
        report = run_auditor(df, {"amount": "integer", "label": "string"})

        self.assertEqual(report["finding_totals"], {
            "total": 3,
            "by_severity": {"error": 1, "warning": 2},
            "by_check": {
                "type": 1,
                "missing": 1,
                "duplicates": 1,
                "category": 0,
                "iqr": 0,
            },
        })
        self.assertEqual(
            sum(report["finding_totals"]["by_check"].values()),
            report["finding_totals"]["total"],
        )

        clean = run_auditor(pd.DataFrame({"label": ["a"]}), {"label": "string"})
        self.assertEqual(clean["finding_totals"]["total"], 0)
        self.assertEqual(clean["finding_totals"]["by_severity"], {
            "error": 0, "warning": 0,
        })

    def test_export_has_missing_counts_and_json_safe_values(self):
        df = pd.DataFrame({
            "amount": [np.inf, None, np.float64(2.0)],
            "when": [pd.Timestamp("2024-01-01"), pd.NaT, pd.Timestamp("2024-01-03")],
        }, index=pd.date_range("2024-02-01", periods=3))
        report = run_auditor(df, {"amount": "float", "when": "date"})

        self.assertNotIn("missing_mask", report)
        self.assertEqual(report["missing_totals"], {
            "total": 2,
            "by_column": {"amount": 1, "when": 1},
        })

        exported = json.loads(to_export_json(report))
        self.assertEqual(exported["missing_totals"], report["missing_totals"])
        self.assertNotIn("missing_mask", exported)
        self.assertEqual(exported["numeric_summary"][0]["statistic"], "count")
        self.assertEqual(exported["numeric_summary"][0]["values"]["amount"], 1.0)
        invalid = exported["checks"]["type"][0]["findings"][0]
        self.assertIsNone(invalid["value"])
        self.assertEqual(invalid["row_index"], "2024-02-01T00:00:00")
        self.assertEqual(exported["checks"]["type"][0]["metrics"]["finding_count"], 1)


if __name__ == "__main__":
    unittest.main()
