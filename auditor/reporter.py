
from auditor.profiler import _missing_mask


def display_profile(df, dataset_summary, column_profile):
    """
    Print the dataset preview and profile to the terminal.
    """
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

    print("\nNUMERIC SUMMARY")
    print("=" * 60)

    numeric_columns = df.select_dtypes(include="number")

    if numeric_columns.empty:
        print("No numeric columns were detected.")
    else:
        numeric_summary = numeric_columns.describe().round(2)
        print(numeric_summary.to_string())


def display_missing_report(df, missing_report):
    """
    Display the missing-value report in the terminal.
    """
    print("\nMISSING-VALUE REPORT")
    print("=" * 60)

    missing = _missing_mask(df)
    total_missing = int(missing.sum().sum())
    rows_with_missing = int(missing.any(axis=1).sum())

    print(f"Total missing cells: {total_missing}")
    print(f"Rows containing missing values: {rows_with_missing}")

    columns_with_missing = missing_report[
        missing_report["missing_count"] > 0
    ]

    if columns_with_missing.empty:
        print("\nNo missing values were detected.")
    else:
        print("\nColumns with missing values:")
        print(columns_with_missing.to_string(index=False))


def display_type_issues(df, type_report):
    print("\nDATA-TYPE VALIDATION")
    print("=" * 60, end="")
    
    for result in type_report:
        print(f"\nColumn: {result['column']}")
        print(f"Current pandas type: {result['current_pandas_type']}")
        print(f"Confirmed type: {result['expected_type']}")
        print(f"Invalid count: {result['invalid_count']}")
        print(f"Invalid percentage: {result['invalid_percentage']}%")
        print(f"Invalid rows: {result['invalid_rows']}")
        print(f"Invalid values: {result['invalid_values']}")


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


def display_category_issues(df, issues_report):
    print("\nUNUSUAL CATEGORY DETECTION")
    print("=" * 60, end="")
    
    for result in issues_report:
        print(f"\nColumn: {result['column']}")
        if "classification" in result:
            print(f"Classification: {result['classification']}")
            print(f"Reason: {result['reason']}")
            continue

        if "is_categorical" in result:
            is_categorical = result["is_categorical"]
            print(f"Classification: {is_categorical['classification']}")
            print(f"Reason: {is_categorical['reason']}")
            continue

        if "high_cardinality" in result:
            high_cardinality = result["high_cardinality"]
            print("-- High category cardinality detected --")
            print(f"Classification: {high_cardinality['classification']}")
            print(f"Reason: {high_cardinality['reason']}")
            print(f"Values tested: {high_cardinality['values_tested']}")
            print(f"Unique count: {high_cardinality['unique_count']}")
            print(f"Unique-to-All ratio: {high_cardinality['cardinality_ratio']}")
            continue

        if "rare_categories" in result:
            rare_categories = result["rare_categories"]
            print("-- Rare categories Detection --")
            print(f"Classification: {rare_categories['classification']}")
            print(f"Reason: {rare_categories['reason']}")
            print(f"Rare category count: {rare_categories['rare_category_count']}")
            print("Rare values:")
            for value, info in rare_categories["rare_records"].items():
                print(f"   {value}: count={info['count']}, rows={info['rows']}")  


def display_outliers_report(df, outliers_report):
    print("\nIQR OUTLIER DETECTION")
    print("=" * 60, end="")
    for result in outliers_report:
        print(f"\nColumn: {result['column']}")
        print(f"Classification: {result['classification']}")
        print(f"Reason: {result['reason']}")
        print(f"Values tested: {result['values_tested']}")
        if not result["check_performed"]:
            continue
        for label, key in [("Q1", "q1"), ("Q3", "q3"), ("IQR", "iqr"), ("Lower bound", "lower_bound"), ("Upper bound", "upper_bound"), ("Outlier count", "outlier_count")]:
            print(f"{label}: {result[key]}")
        print(f"Outlier percentage: {result['outlier_percentage']}%")
        for value, info in result["outlier_records"].items():
            print(f"   {value}: count={info['count']}, rows={info['rows']}")
