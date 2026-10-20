# Data Auditor

Data Auditor profiles CSV files, suggests types for review, then checks the data against confirmed types. The current interface is a command-line application. The backend has separate preparation and audit stages so a Streamlit interface can use the same workflow.

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
from auditor.export import to_export_json

preview = prepare_audit(df)
# Present preview["type_suggestions"] for review.
confirmed_types = {"amount": "float", "label": "string"}
report = run_auditor(df, confirmed_types)
json_download = to_export_json(report)
```

The confirmed mapping must include every column. `report["checks"]` groups type, missing, duplicate, category, and IQR results. `report["missing_totals"]` provides overall and per-column missing counts. Each check result has `check`, `column`, `status`, `classification`, `reason`, `metrics`, and `findings`. Every finding includes a stable `row_position` for `df.iloc` drill-down. See [AUDIT_RETURN_SCHEMA.md](AUDIT_RETURN_SCHEMA.md) for the complete return contract and branch descriptions.

## Benchmarks

The bundled benchmarks compare dirty and clean flight or beer data with fixed type labels for those sample datasets:

```powershell
python benchmark_flights.py
python benchmark_beers.py
```

Missing and type benchmarks use check-specific ground truth. The category and IQR benchmarks still compare warnings against all changed cells, so their precision and recall are not direct measures of whether those warnings are useful.

## Current limits

- Type validation catches incompatible representations; a validly formatted but factually wrong value needs a domain-specific check.
- Rare categories and IQR outliers are warnings. They do not establish that a value is erroneous.
- Duplicate column names are not handled explicitly.
- The Python report contains pandas DataFrames and source values; use `to_export_json` for a portable download.
- Isolation Forest and the Streamlit interface are not implemented yet.
