import unittest

import pandas as pd

from auditor.export import to_export_pdf
from auditor.pipeline import run_auditor


class PdfExportTest(unittest.TestCase):
    def test_completed_report_exports_pdf_bytes(self):
        df = pd.DataFrame({
            "amount": ["10", "bad", None, "10"],
            "label": ["a", "a", "a", "a"],
        })
        report = run_auditor(df, {"amount": "integer", "label": "string"})

        pdf = to_export_pdf(report)

        self.assertIsInstance(pdf, bytes)
        self.assertTrue(pdf.startswith(b"%PDF-"))
        self.assertIn(b"%%EOF", pdf[-32:])
        self.assertGreater(len(pdf), 1000)


if __name__ == "__main__":
    unittest.main()
