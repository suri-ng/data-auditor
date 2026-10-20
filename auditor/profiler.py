import pandas as pd

from auditor.results import check_result, findings_for_mask


MISSING_MARKERS = {"nan", "none", "null", "n/a", "empty"}


def _missing_series_mask(series):
    """Return values that are null or use a common text missing marker."""
    normalized = series.astype("string").str.strip().str.casefold()
    return series.isna() | normalized.eq("") | normalized.isin(MISSING_MARKERS)


def _missing_mask(df):
    """Return cells that are null or use a common text missing-value marker."""
    return df.apply(_missing_series_mask)


def profile_dataset(df):
    """Create a basic profile of a pandas DataFrame."""
    missing = _missing_mask(df)
    column_profile = pd.DataFrame({
        "column": df.columns,
        "data_type": df.dtypes.astype(str).values,
        "non_missing_count": (~missing).sum().values,
        "missing_count": missing.sum().values,
        "unique_count": df.mask(missing).nunique(dropna=True).values
    })
    dataset_summary = {
        "number_of_rows": df.shape[0],
        "number_of_columns": df.shape[1],
        "duplicate_rows": int(df.duplicated().sum())
    }
    return dataset_summary, column_profile


def detect_missing_values(df):
    """Return one standardized missing-value check per column."""
    missing = _missing_mask(df)
    results = []
    for column in df.columns:
        series = df[column]
        findings = findings_for_mask(
            series, missing[column], check="missing", severity="warning",
            message="Value is missing or matches a configured missing marker.",
        )
        results.append(check_result(
            "missing", column, "complete",
            "missing_values_detected" if findings else "no_missing_values",
            "Some values are missing." if findings else "No missing values were found.",
            values_total=len(series),
            values_present=len(series) - len(findings),
            values_tested=len(series),
            findings=findings,
        ))
    return results


def detect_duplicate_rows(df):
    """Return a dataset-level check for rows duplicated after the first copy."""
    duplicate_mask = df.duplicated()
    findings = [
        {
            "check": "duplicates",
            "column": None,
            "row_position": position,
            "row_index": df.index[position],
            "value": None,
            "severity": "warning",
            "message": "Row duplicates an earlier row in the dataset.",
        }
        for position, duplicated in enumerate(duplicate_mask.tolist())
        if duplicated
    ]
    return check_result(
        "duplicates", None, "complete",
        "duplicate_rows_detected" if findings else "no_duplicate_rows",
        "Some rows duplicate earlier rows." if findings else "No duplicate rows were found.",
        values_total=len(df),
        values_present=len(df),
        values_tested=len(df),
        findings=findings,
    )
