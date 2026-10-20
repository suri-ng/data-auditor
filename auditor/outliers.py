import pandas as pd

from auditor.profiler import _missing_series_mask


def detect_outliers_iqr(df, confirmed_types):
    results = []

    for column in df.columns:
        series = df[column]
        selected_type = confirmed_types[column]

        if selected_type not in {"integer", "float"}:
            results.append({
                "column": column,
                "check_performed": False,
                "values_tested": 0,
                "outlier_count": 0,
                "classification": "not_numeric_skipped",
                "reason": "IQR outlier detection applies only to confirmed integer or float columns."
            })
            continue

        converted = pd.to_numeric(series.mask(_missing_series_mask(series)), errors="coerce")
        if selected_type == "integer":
            converted = converted.where(converted % 1 == 0)
        non_missing_series = converted.dropna()
        values_tested = len(non_missing_series)

        if values_tested == 0:
            results.append({
                "column": column,
                "check_performed": False,
                "values_tested": 0,
                "outlier_count": 0,
                "classification": "no_nonmissing_values",
                "reason": "No nonmissing values are available for IQR outlier detection."
            })
            continue

        q1 = non_missing_series.quantile(0.25)
        q3 = non_missing_series.quantile(0.75)
        iqr = q3 - q1
        lower_bound = q1 - (1.5 * iqr)
        upper_bound = q3 + (1.5 * iqr)
        outlier_mask = (converted < lower_bound) | (converted > upper_bound)
        outlier_series = series[outlier_mask]
        outlier_count = int(outlier_mask.sum())

        if outlier_count == 0:
            classification = "no_outliers_detected"
            reason = "No nonmissing values fall outside the IQR bounds."
        else:
            classification = "outliers_detected"
            reason = "Values fall below the lower IQR bound or above the upper IQR bound."

        results.append({
            "column": column,
            "check_performed": True,
            "values_tested": values_tested,
            "q1": q1,
            "q3": q3,
            "iqr": iqr,
            "lower_bound": lower_bound,
            "upper_bound": upper_bound,
            "outlier_count": outlier_count,
            "outlier_percentage": round((outlier_count / values_tested) * 100, 2),
            "outlier_values": outlier_series.tolist(),
            "outlier_records": {
                value: {
                    "count": int(count),
                    "rows": outlier_series[outlier_series == value].index.tolist()
                }
                for value, count in outlier_series.value_counts().items()
            },
            "classification": classification,
            "reason": reason
        })

    return results
