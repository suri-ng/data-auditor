"""Automatic rare-category detection for confirmed string columns."""

from auditor.profiler import _missing_series_mask


def detect_category_issues(df, confirmed_types):
    results = []

    for column in df.columns:
        if confirmed_types[column] != "string":
            results.append({
                "column": column,
                "is_categorical": {
                    "classification": "not_selected_as_categorical",
                    "reason": "Rare-category detection applies to confirmed string columns."
                }
            })
            continue

        series = df[column]
        normalized = series[~_missing_series_mask(series)].astype("string").str.strip().str.casefold()
        values_tested = len(normalized)
        if values_tested == 0:
            results.append({
                "column": column,
                "classification": "no_nonmissing_values",
                "reason": "No nonmissing values are available for category detection."
            })
            continue

        unique_count = normalized.nunique()
        cardinality_ratio = unique_count / values_tested
        if cardinality_ratio >= 0.05:
            results.append({
                "column": column,
                "high_cardinality": {
                    "classification": "high_cardinality_skipped",
                    "reason": "Rare-category detection was skipped because the column has many distinct values.",
                    "unique_count": unique_count,
                    "values_tested": values_tested,
                    "cardinality_ratio": cardinality_ratio
                }
            })
            continue

        proportions = normalized.value_counts(normalize=True)
        rare_values = proportions[proportions < 0.01].index
        rare_records = {}
        for value in rare_values:
            rows = normalized.index[normalized == value].tolist()
            rare_records[value] = {"count": len(rows), "rows": rows}

        rare_mask = normalized.isin(rare_values)
        rare_rows = normalized.index[rare_mask].tolist()
        results.append({
            "column": column,
            "rare_categories": {
                "check_performed": True,
                "rare_category_count": len(rare_rows),
                "rare_values": series[~_missing_series_mask(series)][rare_mask].tolist(),
                "rare_records": rare_records,
                "classification": "rare_categories_detected" if rare_records else "no_rare_categories",
                "reason": (
                    "Some categories occur below the 1% threshold. These are warnings, not necessarily errors."
                    if rare_records else "No category occurs below the 1% threshold."
                )
            }
        })

    return results
