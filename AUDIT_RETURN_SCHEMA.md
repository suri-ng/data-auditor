# Audit return schema

The backend has two stages. `prepare_audit(df)` returns a dataset summary and type suggestions for review. Once every column has a confirmed type, `run_auditor(df, confirmed_types)` returns the completed audit.

## Preparation result

```python
{
    "dataset_summary": {
        "number_of_rows": int,
        "number_of_columns": int,
        "duplicate_rows": int,
    },
    "column_profile": pandas.DataFrame,
    "type_suggestions": list[dict],
}
```

`column_profile` has one row per column: `column`, current pandas `data_type`, `non_missing_count`, `missing_count`, and `unique_count`. The type is not yet confirmed. Missing values include nulls, blank strings, and the text markers `nan`, `none`, `null`, `n/a`, and `empty`, ignoring case and surrounding whitespace.

Each type suggestion contains `column`, `current_pandas_type`, `suggested_type`, `confidence`, `values_tested`, compatibility counts and values, `candidates`, `multiple_candidates`, `classification`, and `reason`. These are inference results, not audit checks. Their cases are:

| Case | Suggested type / classification | Distinct return values |
|---|---|---|
| All values missing | `unknown` / `unknown` | Confidence is `None`; lists are empty; counts are zero. |
| Identifier name or leading-zero value | `string` / `safeguarded suggestion` | Returns early. `values_tested=0` and zero counts are placeholders even when values exist. |
| No candidate reaches 60% | `string` / `fallback string` | Actual nonmissing `values_tested`; no confidence or candidates; compatibility counts are placeholders. |
| Multiple candidates without a safe winner | `ambiguous` / `ambiguous` | `candidates` lists alternatives; `confidence` is the best candidate's score, not a selected-type confidence. Incompatible count, rows, and values are `None`. |
| A candidate wins | `boolean`, `integer`, `float`, or `date` | Compatibility counts, incompatible rows/values, confidence, and candidates describe the selected type. Classification is `strong suggestion`, `suggestion with exception`, or `low-confidence suggestion`. |

`unknown` and `ambiguous` require the user to select a supported type. The supported confirmed types are `string`, `integer`, `float`, `boolean`, and `date`.

## Final audit result

```python
{
    "dataset_summary": {...},
    "column_profile": pandas.DataFrame,
    "numeric_summary": pandas.DataFrame,
    "missing_totals": {
        "total": int,
        "by_column": {"column_name": int, ...},
    },
    "confirmed_types": {"column_name": "type_name", ...},
    "finding_totals": {
        "total": int,
        "by_severity": {"error": int, "warning": int},
        "by_check": {"type": int, "missing": int, "duplicates": int,
                     "category": int, "iqr": int},
    },
    "checks": {
        "type": [check_result, ...],
        "missing": [check_result, ...],
        "duplicates": [check_result],
        "category": [check_result, ...],
        "iqr": [check_result, ...],
    },
}
```

The `type`, `missing`, `category`, and `iqr` lists have one result per column in DataFrame order. `duplicates` contains one dataset-level result with `column=None`. The final `column_profile` adds `confirmed_type`. `numeric_summary` uses valid converted values from confirmed integer and float columns; it is empty when there are no confirmed numeric columns. `missing_totals.total` counts missing cells across the dataset, and `by_column` gives each column's missing-cell count. These counts use the same missing markers as the missing-value check.

`finding_totals` is ready for overview cards and a by-check chart. `total` counts finding events, so a cell or row flagged by multiple checks contributes once per check. Skipped and zero-finding checks have a count of zero. The severity and check counts each sum to `total`.

An incomplete, extra, or unsupported confirmed type mapping raises `ValueError` before a final report is returned. An invalid cell value is a finding in a completed type check; it does not abort the audit.

## Standard check result

Every object in `checks` has **exactly these outer keys**, whether complete or skipped:

```python
{
    "check": "type" | "missing" | "duplicates" | "category" | "iqr",
    "column": str | None,
    "status": "complete" | "skipped",
    "classification": str,
    "reason": str,
    "metrics": {
        "values_total": int,
        "values_present": int,
        "values_tested": int,
        "finding_count": int,
        "finding_percentage": float,
        # Fixed extra keys for the particular check type, described below.
    },
    "findings": [finding, ...],
}
```

`values_total` is the number of source rows. `values_present` excludes auditor-defined missing values. `values_tested` counts values used by the particular check; it can be zero even when values are present, such as when a confirmed numeric column contains only invalid numbers. `finding_percentage` divides `finding_count` by `values_tested`, or is `0.0` when nothing was tested. Skipped checks have an empty `findings` list.

Every finding has the same keys:

```python
{
    "check": str,
    "column": str | None,
    "row_position": int,
    "row_index": object,
    "value": object,
    "severity": "error" | "warning",
    "message": str,
}
```

Use `row_position` with `df.iloc` for Streamlit drill-down. It remains unique when source index labels are duplicated. `row_index` retains the original label for display. Duplicate-row findings have `column=None` and `value=None` because they refer to a whole row.

## Cases by check

### Confirmed type (`checks["type"]`)

The metrics always add `current_pandas_type` and `expected_type`. Missing values are handled by the missing check and excluded from type validation.

| Case | Status / classification | Findings |
|---|---|---|
| No nonmissing values | `skipped` / `no_nonmissing_values` | Empty. |
| All nonmissing values convert to the confirmed type | `complete` / `all_values_valid` | Empty. |
| One or more nonmissing values fail conversion | `complete` / `invalid_values_detected` | One error finding per invalid cell, with original value and row position. |

`integer` accepts finite whole numbers; `float` accepts finite numbers; Boolean and date scalar values fail both numeric types. `boolean` accepts case-insensitive true/false, yes/no, and 1/0 representations. `date` rejects numeric-only values such as `20240101`. `string` accepts any nonmissing value converted to text.

### Missing values (`checks["missing"]`)

| Case | Status / classification | Findings |
|---|---|---|
| No missing values | `complete` / `no_missing_values` | Empty. |
| One or more missing values | `complete` / `missing_values_detected` | One warning finding per missing cell. |

The missing check always tests every row. `finding_count` is the missing count for that column, and `finding_percentage` is the missing percentage.

### Duplicate rows (`checks["duplicates"]`)

| Case | Status / classification | Findings |
|---|---|---|
| No duplicate rows | `complete` / `no_duplicate_rows` | Empty. |
| Rows duplicate earlier rows | `complete` / `duplicate_rows_detected` | One warning finding for each duplicate after the first copy. |

This dataset-level result always has `column=None`. Its finding count matches `dataset_summary["duplicate_rows"]`.

### Rare categories (`checks["category"]`)

The metrics always add `unique_count`, `cardinality_ratio`, `cardinality_threshold` (5%), and `rare_threshold` (1%). `unique_count` and `cardinality_ratio` are `None` if the check ends before calculating them.

| Case | Status / classification | Findings |
|---|---|---|
| Confirmed type is not string | `skipped` / `not_string` | Empty. `values_present` still reflects source data; `values_tested=0`. |
| Confirmed string, all values missing | `skipped` / `no_nonmissing_values` | Empty. |
| At least 5% as many unique categories as nonmissing values | `skipped` / `high_cardinality` | Empty. The cardinality calculation examined the present values, so `values_tested=values_present`. |
| Low cardinality, no category appears below 1% | `complete` / `no_rare_categories` | Empty. |
| Low cardinality, at least one category appears below 1% | `complete` / `rare_categories_detected` | One warning finding per row in a rare category. |

Category comparisons trim whitespace and ignore case. Findings retain original source values.

### IQR outliers (`checks["iqr"]`)

The metrics always add `q1`, `q3`, `iqr`, `lower_bound`, and `upper_bound`. These are `None` when the check is skipped.

| Case | Status / classification | Findings |
|---|---|---|
| Confirmed type is not integer or float | `skipped` / `not_numeric` | Empty. `values_present` can be positive while `values_tested=0`. |
| Numeric type, all values missing | `skipped` / `no_nonmissing_values` | Empty. |
| Numeric type, present values all fail conversion | `skipped` / `no_valid_numeric_values` | Empty. The failures appear in `checks["type"]`. |
| Valid numbers, no IQR outliers | `complete` / `no_outliers_detected` | Empty. Quartiles and bounds are present. |
| Valid numbers with IQR outliers | `complete` / `outliers_detected` | One warning finding per outlier. Quartiles and bounds are present. |

Only valid converted numeric values enter quartiles and bounds. Findings show original values. The confirmed type decides whether IQR runs, even when the original pandas dtype is text.

## Streamlit access and export

A generic results screen can read `result["status"]`, `result["classification"]`, `result["reason"]`, `result["metrics"]["finding_count"]`, and `result["findings"]` for every check without `.get()`. Each check type also guarantees its own extra metric keys, including on skipped branches. When an extra metric is `None`, the UI should show “not calculated.”

The report remains a Python object with pandas DataFrames and original source values. Use `auditor.export.to_export_dict(report)` for a JSON-safe snapshot or `to_export_json(report)` for a downloadable JSON string. Export turns `column_profile` into records and `numeric_summary` into `{statistic, values}` records. It converts timestamps and dates to ISO 8601 strings, NumPy scalars to Python values, and missing or nonfinite numeric values to JSON `null`. Unsupported source-value types raise `TypeError` rather than silently becoming strings. The export contains `missing_totals`, not a cell-level missing mask. Isolation Forest is not yet part of `checks`.
