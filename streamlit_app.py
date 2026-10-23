import streamlit as st
from hashlib import sha256
from io import BytesIO
import pandas as pd
from auditor.pipeline import prepare_audit, run_auditor
from auditor.data_type import SUPPORTED_TYPES
from auditor.export import to_export_json, to_export_pdf

st.title("Data Auditor")
st.write("Upload a CSV file for a data summary and run an audit")

uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
if uploaded_file is None:
    st.info("Choose a CSV file to begin")
    st.stop()

file_bytes = uploaded_file.getvalue()
source_digest = sha256(file_bytes).hexdigest()
if st.session_state.get("source_digest") != source_digest:
    st.session_state["source_digest"] = source_digest
    st.session_state.pop("report", None)

try:
    df = pd.read_csv(BytesIO(file_bytes))
except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError) as error:
    st.error(f"Could not read this CSV: {error}")
    st.stop()

if df.empty:
    st.error("The CSV has no data rows.")
    st.stop()

st.subheader("Dataset preview")
st.dataframe(df.head(10))

preview = prepare_audit(df)

st.subheader("Dataset summary")
summary = preview["dataset_summary"]
st.write(f"Rows: {summary['number_of_rows']}")
st.write(f"Columns: {summary['number_of_columns']}")
st.write(f"Number of duplicate rows: {summary['duplicate_rows']}")

st.subheader("Column profile")
profile = preview["column_profile"]
st.dataframe(profile)

if "report" not in st.session_state:
    st.subheader("Suggested data types")
    for suggestion in preview["type_suggestions"]:
        st.write(
            f"**{suggestion['column']}**: {suggestion['suggested_type']}"
        )
        st.caption(suggestion["reason"])

    type_options = [
        "Choose a type", "string", "integer", "float", "boolean", "date",
    ]
    with st.form(f"type_confirmation_{source_digest}"):
        confirmed_types = {}
        for suggestion in preview["type_suggestions"]:
            column = suggestion["column"]
            suggested = suggestion["suggested_type"]
            starting_position = (
                type_options.index(suggested) if suggested in SUPPORTED_TYPES else 0
            )
            confirmed_types[column] = st.selectbox(
                f"Type for {column}",
                options=type_options,
                index=starting_position,
                key=f"type_{source_digest}_{column}",
            )
        submitted = st.form_submit_button("Confirm types and run audit")

    if submitted:
        unresolved = [
            column for column, selected_type in confirmed_types.items()
            if selected_type == "Choose a type"
        ]
        if unresolved:
            st.error("Choose a type for: " + ", ".join(unresolved))
        else:
            st.session_state["report"] = run_auditor(df, confirmed_types)
            st.rerun()

else:
    report = st.session_state["report"]

    st.subheader("Confirmed data types")
    st.dataframe(
        pd.DataFrame([
            {"Column": column, "Type": selected_type}
            for column, selected_type in report["confirmed_types"].items()
        ]),
        hide_index=True,
    )
    st.caption("Types are fixed for this audit. Upload a different CSV to start a new review.")

    st.subheader("Audit results")

    first, second, third, fourth = st.columns(4)

    first.metric("Rows", report["dataset_summary"]["number_of_rows"])
    second.metric("Missing cells", report["missing_totals"]["total"])
    third.metric("Errors", report["finding_totals"]["by_severity"]["error"])
    fourth.metric("Warning", report["finding_totals"]["by_severity"]["warning"])

    st.subheader("Numeric statistics")
    numeric_summary = report["numeric_summary"]
    if numeric_summary.empty:
        st.info("No columns were confirmed as integer or float.")
    else:
        st.caption("Computed from valid numeric values. Median is the second quartile (Q2).")
        numeric_display = numeric_summary.T.rename(columns={
            "count": "Valid count",
            "mean": "Mean",
            "std": "Std dev",
            "min": "Min",
            "q1": "Q1 (25%)",
            "median_q2": "Median (Q2)",
            "q3": "Q3 (75%)",
            "max": "Max",
        })
        numeric_display.index.name = "Column"
        st.dataframe(numeric_display.reset_index(), hide_index=True)

    st.subheader("Findings by check")
    st.bar_chart(pd.Series(report["finding_totals"]["by_check"]))

    check_name = st.selectbox(
        "Choose a check to inspect",
        options=list(report["checks"]),
    )

    check_rows = []
    for result in report["checks"][check_name]:
        check_rows.append({
            "Column": result["column"] if result["column"] is not None else "Whole dataset",
            "Status": result["status"],
            "Classification": result["classification"],
            "Finding count": result["metrics"]["finding_count"],
            "Reason": result["reason"],
        })
    st.dataframe(pd.DataFrame(check_rows), hide_index=True)

    st.download_button(
        label="Download audit report",
        data=to_export_json(report),
        file_name="audit_report.json",
        mime="application/json",
    )
    st.download_button(
        label="Download PDF summary",
        data=to_export_pdf(report),
        file_name="audit_report.pdf",
        mime="application/pdf",
    )
