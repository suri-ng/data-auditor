# Data Auditor

Data Auditor profiles CSV files, suggests types for review, then checks the data against confirmed types. It includes a Streamlit web app and a command-line interface.

**Try the live app:** [dataset-quality-auditor.onrender.com](https://dataset-quality-auditor.onrender.com)

## Use the web app

1. Upload a CSV file.
2. Review the dataset preview, summary, column profile, and suggested data types.
3. Confirm or change the type for every column, then select **Confirm types and run audit**.
4. Review the findings, numeric statistics, and checks. Download the report as JSON or a PDF summary.

The audit checks data types, missing values, duplicate rows, rare categories, and numeric outliers. Category and outlier results are warnings for review; they do not prove that a value is wrong.

**Privacy:** The public app has no login. Uploaded CSV data is processed in memory and is not saved as durable app data, but avoid uploading sensitive or confidential files. The app runs on Render's free instance, which may spin down after inactivity; the first visit after that can take longer to load.

## Run the Streamlit app

Install dependencies from `requirements.txt`, then run:

```powershell
streamlit run streamlit_app.py
```

Open the local URL shown by Streamlit, upload a CSV, review the suggested column types, and confirm them to run the audit.

## Run with Docker

Install Docker Desktop, then from the repository root:

```powershell
docker build -t data-auditor:local .
docker run --rm -p 8501:8501 data-auditor:local
```

Open <http://localhost:8501>. Stop the app with Ctrl+C.

## Run the CLI

Install the dependencies from `requirements.txt`, then run:

```powershell
python app.py examples/clean_index_beers.csv
```

The application shows the dataset summary and all suggested types first. You can accept the suggestions together or change selected columns. Once every column has a confirmed type, it runs type validation, missing-value and duplicate-row checks, rare-category detection, numeric summaries, and IQR outlier detection.

Supported types are `string`, `integer`, `float`, `boolean`, and `date`. The CLI does not load rule files.

## Use the backend from Python or Streamlit

```python
from auditor.pipeline import prepare_audit, run_auditor
from auditor.export import to_export_json, to_export_pdf

preview = prepare_audit(df)
# Present preview["type_suggestions"] for review.
confirmed_types = {"amount": "float", "label": "string"}
report = run_auditor(df, confirmed_types)
json_download = to_export_json(report)
pdf_download = to_export_pdf(report)
```

The confirmed mapping must include every column. `report["checks"]` groups type, missing, duplicate, category, and IQR results. `report["missing_totals"]` provides overall and per-column missing counts. `report["numeric_summary"]` includes count, mean, standard deviation, min, Q1, median/Q2, Q3, and max for confirmed numeric columns. Each check result has `check`, `column`, `status`, `classification`, `reason`, `metrics`, and `findings`. Every finding includes a stable `row_position` for `df.iloc` drill-down. JSON export preserves the structured checks; PDF export gives a readable summary without source row identifiers. See [AUDIT_RETURN_SCHEMA.md](AUDIT_RETURN_SCHEMA.md) for the complete return contract and branch descriptions.

## Benchmarks

The bundled benchmarks compare dirty and clean flight or beer data with fixed type labels for those sample datasets:

```powershell
python benchmark_flights.py
python benchmark_beers.py
```

Missing and type benchmarks use check-specific ground truth. The category and IQR benchmarks still compare warnings against all changed cells, so their precision and recall are not direct measures of whether those warnings are useful.

## Current limits

- Type validation catches incompatible representations; a validly formatted but factually wrong value needs a domain-specific check.
- Boolean and date values are normalized internally for validation, but the app does not produce a cleaned CSV with standardized values.
- Numeric-only date values such as `20260101` are rejected as dates; use a delimited date value such as `2026-01-01`.
- Rare categories and IQR outliers are warnings. They do not establish that a value is erroneous.
- Duplicate column names are not handled explicitly.
- The Python report contains pandas DataFrames and source values; use `to_export_json` for a portable download.
- The app does not include user accounts or authentication. Do not use it for confidential data unless access controls are added.
- The project dependencies are not pinned to exact versions yet, so rebuilds may install newer releases.
