"""Terminal views of the structured audit results."""


def display_profile(df, dataset_summary, column_profile):
    print("\nDATASET PREVIEW")
    print("=" * 60)
    print(df.head())

    print("\nDATASET SUMMARY")
    print("=" * 60)
    print(f"Rows: {dataset_summary['number_of_rows']}")
    print(f"Columns: {dataset_summary['number_of_columns']}")
    print(f"Duplicate rows: {dataset_summary['duplicate_rows']}")

    print("\nCOLUMN PROFILE")
    print("=" * 60)
    print(column_profile.to_string(index=False))


def display_type_suggestions(type_suggestions):
    print("\nSUGGESTED DATA TYPES")
    print("=" * 60)
    for result in type_suggestions:
        confidence = result["confidence"]
        confidence_text = f" ({confidence}% compatible)" if confidence is not None else ""
        print(f"{result['column']}: {result['suggested_type']}{confidence_text}")
        print(f"  Reason: {result['reason']}")
        if result["multiple_candidates"]:
            candidates = ", ".join(
                f"{candidate['type']} ({candidate['confidence']}%)"
                for candidate in result["candidates"]
            )
            print(f"  Alternatives: {candidates}")


def display_numeric_summary(numeric_summary):
    print("\nNUMERIC SUMMARY")
    print("=" * 60)
    if numeric_summary.empty:
        print("No confirmed numeric columns were available.")
    else:
        print(numeric_summary.to_string())


def display_check_results(title, results):
    print(f"\n{title}")
    print("=" * 60)
    for result in results:
        print(f"\nColumn: {result['column'] if result['column'] is not None else 'whole dataset'}")
        print(f"Status: {result['status']}")
        print(f"Classification: {result['classification']}")
        print(f"Reason: {result['reason']}")
        for name, value in result["metrics"].items():
            print(f"{name}: {value}")
        for finding in result["findings"]:
            print(
                f"  Row {finding['row_position']} "
                f"(index {finding['row_index']}): {finding['value']!r} "
                f"- {finding['message']}"
            )


def display_type_issues(df, results):
    display_check_results("DATA-TYPE VALIDATION", results)


def display_missing_report(df, results):
    display_check_results("MISSING-VALUE REPORT", results)


def display_duplicate_report(results):
    display_check_results("DUPLICATE-ROW REPORT", results)


def display_category_issues(df, results):
    display_check_results("UNUSUAL CATEGORY DETECTION", results)


def display_outliers_report(df, results):
    display_check_results("IQR OUTLIER DETECTION", results)
