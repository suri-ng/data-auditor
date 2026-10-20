import json
import math
from datetime import date, datetime, time, timedelta
from decimal import Decimal

import numpy as np
import pandas as pd


def _json_safe(value):
    """Convert supported pandas and source scalar values without repr fallbacks."""
    if value is None or value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, (pd.Timestamp, datetime, date, time)):
        return value.isoformat()
    if isinstance(value, (pd.Timedelta, timedelta)):
        return value.isoformat()
    if isinstance(value, np.datetime64):
        return None if np.isnat(value) else pd.Timestamp(value).isoformat()
    if isinstance(value, np.timedelta64):
        return None if np.isnat(value) else pd.Timedelta(value).isoformat()
    if isinstance(value, np.generic):
        return _json_safe(value.item())
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, Decimal):
        return str(value) if value.is_finite() else None
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, np.ndarray)):
        return [_json_safe(item) for item in value]
    raise TypeError(f"Cannot export value of type {type(value).__name__} to JSON")


def to_export_dict(report):
    """Build a JSON-safe snapshot of a completed report for download."""
    numeric_summary = report["numeric_summary"]
    export = {
        "dataset_summary": report["dataset_summary"],
        "column_profile": report["column_profile"].to_dict(orient="records"),
        "numeric_summary": [
            {"statistic": statistic, "values": row.to_dict()}
            for statistic, row in numeric_summary.iterrows()
        ],
        "confirmed_types": report["confirmed_types"],
        "missing_totals": report["missing_totals"],
        "finding_totals": report["finding_totals"],
        "checks": report["checks"],
    }
    return _json_safe(export)


def to_export_json(report):
    """Serialize an audit report to strict, readable JSON."""
    return json.dumps(to_export_dict(report), allow_nan=False, ensure_ascii=False, indent=2)
