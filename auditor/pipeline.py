import pandas as pd

from auditor.category import detect_category_issues
from auditor.data_type import convert_confirmed_values, detect_type_issues, suggest_types
from auditor.outliers import detect_outliers_iqr
from auditor.profiler import (
    detect_duplicate_rows,
    detect_missing_values,
    profile_dataset,
)
from auditor.results import finding_totals


def prepare_audit(df):
    """Return the summary and type suggestions for user review."""
    dataset_summary, column_profile = profile_dataset(df)
    return {
        "dataset_summary": dataset_summary,
        "column_profile": column_profile,
        "type_suggestions": suggest_types(df),
    }


def run_auditor(df, confirmed_types):
    """Run checks after every column has a confirmed type."""
    type_report = detect_type_issues(df, confirmed_types)
    dataset_summary, column_profile = profile_dataset(df)
    column_profile["confirmed_type"] = column_profile["column"].map(confirmed_types)
    numeric_columns = {
        column: convert_confirmed_values(df[column], confirmed_types[column])
        for column in df.columns
        if confirmed_types[column] in {"integer", "float"}
    }
    numeric_summary = (
        pd.DataFrame(numeric_columns).describe().round(2).rename(index={
            "25%": "q1",
            "50%": "median_q2",
            "75%": "q3",
        })
        if numeric_columns else pd.DataFrame()
    )
    checks = {
        "type": type_report,
        "missing": detect_missing_values(df),
        "duplicates": [detect_duplicate_rows(df)],
        "category": detect_category_issues(df, confirmed_types),
        "iqr": detect_outliers_iqr(df, confirmed_types),
    }
    missing_by_column = {
        result["column"]: result["metrics"]["finding_count"]
        for result in checks["missing"]
    }

    return {
        "dataset_summary": dataset_summary,
        "column_profile": column_profile,
        "numeric_summary": numeric_summary,
        "missing_totals": {
            "total": sum(missing_by_column.values()),
            "by_column": missing_by_column,
        },
        "confirmed_types": confirmed_types.copy(),
        "checks": checks,
        "finding_totals": finding_totals(checks),
    }
