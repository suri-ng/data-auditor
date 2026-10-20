import argparse
from pathlib import Path

import pandas as pd

from auditor.data_type import validate_expected_type
from auditor.loader import load_csv
from auditor.pipeline import run_auditor
from auditor.profiler import _missing_mask


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_DIRTY = PROJECT_ROOT / "examples" / "dirty_index_flights.csv"
DEFAULT_CLEAN = PROJECT_ROOT / "examples" / "clean_index_flights.csv"
CONFIRMED_TYPES = {
    "index": "integer",
    "src": "string",
    "flight": "string",
    "sched_dep_time": "date",
    "act_dep_time": "date",
    "sched_arr_time": "date",
    "act_arr_time": "date",
}


def _prepare_pair(dirty_df, clean_df, key_column):
    if list(dirty_df.columns) != list(clean_df.columns):
        raise ValueError("Dirty and clean datasets must have identical columns.")
    if key_column not in dirty_df.columns:
        raise ValueError(f"Key column not found: {key_column}")
    if dirty_df[key_column].duplicated().any() or clean_df[key_column].duplicated().any():
        raise ValueError(f"Key column must contain unique values: {key_column}")

    dirty_keys = set(dirty_df[key_column])
    clean_keys = set(clean_df[key_column])
    if dirty_keys != clean_keys:
        raise ValueError("Dirty and clean datasets must contain the same record keys.")

    return (
        dirty_df.set_index(key_column, drop=False).sort_index(),
        clean_df.set_index(key_column, drop=False).sort_index(),
    )


def _values_equal(dirty_value, clean_value):
    dirty_missing = pd.isna(dirty_value)
    clean_missing = pd.isna(clean_value)
    if dirty_missing or clean_missing:
        return dirty_missing and clean_missing
    return dirty_value == clean_value


def actual_dirty_cells(dirty_df, clean_df):
    """Return (row key, column) cells whose dirty and clean values differ."""
    cells = set()
    for column in dirty_df.columns:
        for row_key in dirty_df.index:
            if not _values_equal(dirty_df.at[row_key, column], clean_df.at[row_key, column]):
                cells.add((row_key, column))
    return cells


def actual_type_error_cells(dirty_df, clean_df, confirmed_types, changed_cells):
    """Return changed cells where dirty fails a confirmed type that clean passes."""
    cells = set()
    for column, confirmed_type in confirmed_types.items():
        if column not in dirty_df.columns:
            continue

        dirty_validation = validate_expected_type(dirty_df[column], confirmed_type)
        clean_validation = validate_expected_type(clean_df[column], confirmed_type)
        dirty_invalid_rows = {finding["row_index"] for finding in dirty_validation["findings"]}
        clean_invalid_rows = {finding["row_index"] for finding in clean_validation["findings"]}

        for row_key in dirty_invalid_rows - clean_invalid_rows:
            cell = (row_key, column)
            if cell in changed_cells:
                cells.add(cell)

    return cells


def actual_missing_error_cells(dirty_df, clean_df, changed_cells):
    """Return changed cells that are missing only in the dirty dataset."""
    dirty_missing = _missing_mask(dirty_df)
    clean_missing = _missing_mask(clean_df)

    return {
        (row_key, column)
        for column in dirty_df.columns
        for row_key in dirty_df.index
        if dirty_missing.at[row_key, column]
        and not clean_missing.at[row_key, column]
        and (row_key, column) in changed_cells
    }


def check_predictions(results):
    return {
        (finding["row_index"], finding["column"])
        for result in results
        for finding in result["findings"]
    }


def missing_predictions(results):
    return check_predictions(results)


def type_predictions(results):
    return check_predictions(results)


def category_predictions(results):
    return check_predictions(results)


def outlier_predictions(results):
    return check_predictions(results)


def calculate_metrics(predicted_cells, actual_cells):
    true_positives = len(predicted_cells & actual_cells)
    false_positives = len(predicted_cells - actual_cells)
    false_negatives = len(actual_cells - predicted_cells)

    precision = (
        true_positives / (true_positives + false_positives)
        if true_positives + false_positives else 0.0
    )
    recall = (
        true_positives / (true_positives + false_negatives)
        if true_positives + false_negatives else 0.0
    )
    f1_score = (
        2 * precision * recall / (precision + recall)
        if precision + recall else 0.0
    )

    return {
        "predicted": len(predicted_cells),
        "actual": len(actual_cells),
        "true_positives": true_positives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "precision": precision,
        "recall": recall,
        "f1_score": f1_score,
    }


def display_metrics(name, metrics):
    print(f"\n{name}")
    print("-" * 60)
    print(f"Predicted cells: {metrics['predicted']}")
    print(f"Actual positive cells: {metrics['actual']}")
    print(f"True positives: {metrics['true_positives']}")
    print(f"False positives: {metrics['false_positives']}")
    print(f"False negatives: {metrics['false_negatives']}")
    print(f"Precision: {metrics['precision']:.4f}")
    print(f"Recall: {metrics['recall']:.4f}")
    print(f"F1 score: {metrics['f1_score']:.4f}")


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark the auditor against clean flight data."
    )
    parser.add_argument("--dirty", default=DEFAULT_DIRTY, help="Dirty CSV path.")
    parser.add_argument("--clean", default=DEFAULT_CLEAN, help="Clean CSV path.")
    parser.add_argument("--key", default="index", help="Unique row-key column.")
    args = parser.parse_args()

    dirty_df, clean_df = _prepare_pair(
        load_csv(args.dirty), load_csv(args.clean), args.key
    )
    auditor_report = run_auditor(dirty_df, CONFIRMED_TYPES)
    actual = actual_dirty_cells(dirty_df, clean_df)
    actual_missing_errors = actual_missing_error_cells(
        dirty_df, clean_df, actual
    )
    actual_type_errors = actual_type_error_cells(
        dirty_df, clean_df, CONFIRMED_TYPES, actual
    )
    checks = auditor_report["checks"]
    predictions = {
        "Missing-value detection": missing_predictions(checks["missing"]),
        "Data-type detection": type_predictions(checks["type"]),
        "Category detection": category_predictions(checks["category"]),
        "IQR outlier detection": outlier_predictions(checks["iqr"]),
    }

    print("\nAUDITOR BENCHMARK: INDEX FLIGHTS")
    print("=" * 60)
    ground_truths = {
        "Missing-value detection": actual_missing_errors,
        "Data-type detection": actual_type_errors,
        "Category detection": actual,
        "IQR outlier detection": actual,
    }
    for name, predicted in predictions.items():
        display_metrics(name, calculate_metrics(predicted, ground_truths[name]))

    combined = set().union(*predictions.values())
    display_metrics("Combined auditor", calculate_metrics(combined, actual))


if __name__ == "__main__":
    main()
