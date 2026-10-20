import argparse

from auditor.data_type import SUPPORTED_TYPES
from auditor.loader import load_csv
from auditor.pipeline import prepare_audit, run_auditor
from auditor.reporter import (
    display_category_issues,
    display_duplicate_report,
    display_missing_report,
    display_numeric_summary,
    display_outliers_report,
    display_profile,
    display_type_issues,
    display_type_suggestions,
)


def confirm_types_in_terminal(suggestions):
    """Collect changes to the backend's suggestions in the CLI."""
    confirmed = {
        result["column"]: result["suggested_type"]
        for result in suggestions
        if result["suggested_type"] in SUPPORTED_TYPES
    }
    unresolved = {result["column"] for result in suggestions} - confirmed.keys()
    if unresolved:
        print("\nChoose a type for unresolved columns: " + ", ".join(sorted(unresolved)))

    try:
        answer = input("\nAccept the suggested types? [Y/n]: ").strip().lower()
        if answer not in {"", "y", "yes", "n", "no"}:
            raise ValueError("Answer yes or no when confirming suggested types.")
        if answer in {"", "y", "yes"} and not unresolved:
            return confirmed

        print("Enter a column to change, then choose its type. Press Enter when finished.")
        while True:
            column = input("Column to change: ").strip()
            if not column:
                if unresolved:
                    print("A type is still required for: " + ", ".join(sorted(unresolved)))
                    continue
                return confirmed
            if column not in {result["column"] for result in suggestions}:
                print("Unknown column. Choose a column shown above.")
                continue
            selected_type = input(
                f"Type for {column} ({', '.join(sorted(SUPPORTED_TYPES))}): "
            ).strip().lower()
            if selected_type not in SUPPORTED_TYPES:
                print("Unsupported type. Choose one of the listed types.")
                continue
            confirmed[column] = selected_type
            unresolved.discard(column)
    except EOFError as error:
        raise ValueError("Type confirmation was not completed.") from error


def main():
    parser = argparse.ArgumentParser(
        description="Inspect the basic structure and quality of a CSV file."
    )
    parser.add_argument(
        "file_path",
        help="Path to the CSV file that you want to inspect."
    )
    args = parser.parse_args()

    try:
        df = load_csv(args.file_path)
        preliminary = prepare_audit(df)
        display_profile(df, preliminary["dataset_summary"], preliminary["column_profile"])
        display_type_suggestions(preliminary["type_suggestions"])
        confirmed_types = confirm_types_in_terminal(preliminary["type_suggestions"])
        report = run_auditor(df, confirmed_types)

        checks = report["checks"]
        display_missing_report(df, checks["missing"])
        display_duplicate_report(checks["duplicates"])
        display_type_issues(df, checks["type"])
        display_numeric_summary(report["numeric_summary"])
        display_category_issues(df, checks["category"])
        display_outliers_report(df, checks["iqr"])
    except (FileNotFoundError, ValueError) as error:
        print(f"\nError: {error}")


if __name__ == "__main__":
    main()
