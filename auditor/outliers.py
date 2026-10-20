"""IQR outlier detection for confirmed numeric columns."""

from auditor.data_type import convert_confirmed_values
from auditor.profiler import _missing_series_mask
from auditor.results import check_result, findings_for_mask


def detect_outliers_iqr(df, confirmed_types):
    results = []

    for column in df.columns:
        series = df[column]
        values_present = int((~_missing_series_mask(series)).sum())
        extra_metrics = {
            "q1": None,
            "q3": None,
            "iqr": None,
            "lower_bound": None,
            "upper_bound": None,
        }

        if confirmed_types[column] not in {"integer", "float"}:
            results.append(check_result(
                "iqr", column, "skipped", "not_numeric",
                "IQR detection applies to confirmed integer and float columns.",
                values_total=len(series), values_present=values_present,
                values_tested=0, extra_metrics=extra_metrics,
            ))
            continue

        converted = convert_confirmed_values(series, confirmed_types[column])
        valid_values = converted.dropna()
        values_tested = len(valid_values)
        if values_tested == 0:
            classification = (
                "no_nonmissing_values" if values_present == 0 else "no_valid_numeric_values"
            )
            reason = (
                "No nonmissing values are available for IQR detection."
                if values_present == 0
                else "All nonmissing values failed confirmed-type numeric validation."
            )
            results.append(check_result(
                "iqr", column, "skipped", classification, reason,
                values_total=len(series), values_present=values_present,
                values_tested=0, extra_metrics=extra_metrics,
            ))
            continue

        q1 = valid_values.quantile(0.25)
        q3 = valid_values.quantile(0.75)
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        outlier_mask = (converted < lower_bound) | (converted > upper_bound)
        findings = findings_for_mask(
            series, outlier_mask, check="iqr", severity="warning",
            message="Value falls outside the IQR bounds.",
        )
        extra_metrics.update({
            "q1": q1,
            "q3": q3,
            "iqr": iqr,
            "lower_bound": lower_bound,
            "upper_bound": upper_bound,
        })
        results.append(check_result(
            "iqr", column, "complete",
            "outliers_detected" if findings else "no_outliers_detected",
            "Values fall outside the IQR bounds." if findings else "No values fall outside the IQR bounds.",
            values_total=len(series), values_present=values_present,
            values_tested=values_tested, findings=findings,
            extra_metrics=extra_metrics,
        ))

    return results
