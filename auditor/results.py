"""Shared result shape for checks in the final audit report."""


def findings_for_mask(series, mask, *, check, severity, message):
    """Keep row positions for reliable drill-down even with duplicate index labels."""
    return [
        {
            "check": check,
            "column": series.name,
            "row_position": position,
            "row_index": series.index[position],
            "value": series.iloc[position],
            "severity": severity,
            "message": message,
        }
        for position, selected in enumerate(mask.fillna(False).tolist())
        if selected
    ]


def check_result(
    check,
    column,
    status,
    classification,
    reason,
    *,
    values_total,
    values_present,
    values_tested,
    findings=None,
    extra_metrics=None,
):
    """Build the fields shared by every completed or skipped check."""
    if status not in {"complete", "skipped"}:
        raise ValueError(f"Unsupported check status: {status}")

    findings = [] if findings is None else findings
    finding_count = len(findings)
    metrics = {
        "values_total": int(values_total),
        "values_present": int(values_present),
        "values_tested": int(values_tested),
        "finding_count": finding_count,
        "finding_percentage": (
            round(finding_count / values_tested * 100, 2) if values_tested else 0.0
        ),
    }
    if extra_metrics:
        metrics.update(extra_metrics)

    return {
        "check": check,
        "column": column,
        "status": status,
        "classification": classification,
        "reason": reason,
        "metrics": metrics,
        "findings": findings,
    }


def finding_totals(checks):
    """Count finding events across every check for the report overview."""
    by_check = {}
    by_severity = {"error": 0, "warning": 0}

    for check_name, results in checks.items():
        by_check[check_name] = sum(
            result["metrics"]["finding_count"] for result in results
        )
        for result in results:
            for finding in result["findings"]:
                by_severity[finding["severity"]] += 1

    return {
        "total": sum(by_check.values()),
        "by_severity": by_severity,
        "by_check": by_check,
    }
