"""Automatic rare-category detection for confirmed string columns."""

from auditor.profiler import _missing_series_mask
from auditor.results import check_result, findings_for_mask


CARDINALITY_THRESHOLD = 0.05
RARE_THRESHOLD = 0.01


def detect_category_issues(df, confirmed_types):
    results = []

    for column in df.columns:
        series = df[column]
        present_mask = ~_missing_series_mask(series)
        values_present = int(present_mask.sum())
        extra_metrics = {
            "unique_count": None,
            "cardinality_ratio": None,
            "cardinality_threshold": CARDINALITY_THRESHOLD,
            "rare_threshold": RARE_THRESHOLD,
        }

        if confirmed_types[column] != "string":
            results.append(check_result(
                "category", column, "skipped", "not_string",
                "Rare-category detection applies to confirmed string columns.",
                values_total=len(series), values_present=values_present,
                values_tested=0, extra_metrics=extra_metrics,
            ))
            continue

        if values_present == 0:
            results.append(check_result(
                "category", column, "skipped", "no_nonmissing_values",
                "No nonmissing values are available for category detection.",
                values_total=len(series), values_present=0,
                values_tested=0, extra_metrics=extra_metrics,
            ))
            continue

        normalized = series[present_mask].astype("string").str.strip().str.casefold()
        unique_count = int(normalized.nunique())
        cardinality_ratio = unique_count / values_present
        extra_metrics.update({
            "unique_count": unique_count,
            "cardinality_ratio": round(cardinality_ratio, 4),
        })

        if cardinality_ratio >= CARDINALITY_THRESHOLD:
            results.append(check_result(
                "category", column, "skipped", "high_cardinality",
                "Rare-category detection was skipped because the column has many distinct values.",
                values_total=len(series), values_present=values_present,
                values_tested=values_present, extra_metrics=extra_metrics,
            ))
            continue

        proportions = normalized.value_counts(normalize=True)
        rare_categories = proportions[proportions < RARE_THRESHOLD].index
        rare_mask = present_mask & (
            series.astype("string").str.strip().str.casefold().isin(rare_categories)
        )
        findings = findings_for_mask(
            series, rare_mask, check="category", severity="warning",
            message="Value belongs to a category occurring in less than 1% of nonmissing rows.",
        )
        results.append(check_result(
            "category", column, "complete",
            "rare_categories_detected" if findings else "no_rare_categories",
            "Rare categories were found." if findings else "No rare categories were found.",
            values_total=len(series), values_present=values_present,
            values_tested=values_present, findings=findings,
            extra_metrics=extra_metrics,
        ))

    return results
