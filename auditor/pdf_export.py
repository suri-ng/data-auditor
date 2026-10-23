"""Create a readable PDF summary from a completed audit report."""

from html import escape
from io import BytesIO

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    CondPageBreak,
    HRFlowable,
    LongTable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)


def _paragraph(value, style):
    """Keep source column names and reasons from becoming PDF markup."""
    return Paragraph(escape(str(value)), style)


def _stat_text(value):
    return "N/A" if pd.isna(value) else f"{value:g}"


def _table(headers, rows, widths, styles):
    cells = [[_paragraph(header, styles["table_header"]) for header in headers]]
    cells.extend(
        [_paragraph(value, styles["table_cell"]) for value in row]
        for row in rows
    )
    table = LongTable(cells, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EEF6")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#F7F9FC")]),
        ("LINEBELOW", (0, 0), (-1, 0), 0.7, colors.HexColor("#9AABC0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ])
    return table


def _draw_footer(canvas, document):
    canvas.saveState()
    width, _ = letter
    canvas.setStrokeColor(colors.HexColor("#D5DDE8"))
    canvas.line(0.65 * inch, 0.58 * inch, width - 0.65 * inch, 0.58 * inch)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#617087"))
    canvas.drawString(0.65 * inch, 0.39 * inch, "Data Auditor")
    canvas.drawRightString(width - 0.65 * inch, 0.39 * inch,
                           f"Page {document.page}")
    canvas.restoreState()


def to_export_pdf(report):
    """Return PDF bytes for the report's overview and check summaries."""
    output = BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=letter,
        leftMargin=0.65 * inch,
        rightMargin=0.65 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.85 * inch,
        title="Data Auditor Report",
    )
    available_width = letter[0] - document.leftMargin - document.rightMargin

    styles = getSampleStyleSheet()
    styles["Title"].textColor = colors.HexColor("#183153")
    styles["Heading2"].textColor = colors.HexColor("#183153")
    styles["Heading2"].spaceBefore = 18
    styles["Heading2"].spaceAfter = 8
    styles.add(styles["Normal"].clone("table_cell"))
    styles["table_cell"].fontSize = 8
    styles["table_cell"].leading = 11
    styles.add(styles["table_cell"].clone("table_header"))
    styles["table_header"].fontName = "Helvetica-Bold"

    summary = report["dataset_summary"]
    missing = report["missing_totals"]
    findings = report["finding_totals"]
    story = [
        Paragraph("Data Audit Report", styles["Title"]),
        Paragraph("Dataset quality overview", styles["Normal"]),
        Spacer(1, 12),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#D5DDE8")),
        Paragraph("Overview", styles["Heading2"]),
        _table(
            ["Rows", "Columns", "Duplicate rows", "Missing cells", "Findings", "Errors", "Warnings"],
            [[summary["number_of_rows"], summary["number_of_columns"],
              summary["duplicate_rows"], missing["total"], findings["total"],
              findings["by_severity"]["error"],
              findings["by_severity"]["warning"]]],
            [available_width / 7] * 7,
            styles,
        ),
        Paragraph("Confirmed types and missing values", styles["Heading2"]),
        _table(
            ["Column", "Confirmed type", "Missing cells"],
            [[column, selected_type, missing["by_column"][column]]
             for column, selected_type in report["confirmed_types"].items()],
            [available_width * 0.48, available_width * 0.27,
             available_width * 0.25],
            styles,
        ),
        Paragraph("Findings by check", styles["Heading2"]),
        _table(
            ["Check", "Finding count"],
            [[check, count] for check, count in findings["by_check"].items()],
            [available_width * 0.65, available_width * 0.35],
            styles,
        ),
    ]

    numeric_summary = report["numeric_summary"]
    story.append(CondPageBreak(1.6 * inch))
    story.append(Paragraph("Numeric statistics", styles["Heading2"]))
    if numeric_summary.empty:
        story.append(Paragraph(
            "No columns were confirmed as integer or float.", styles["Normal"]
        ))
    else:
        story.append(Paragraph(
            "Computed from valid numeric values. Median is the second quartile (Q2).",
            styles["Normal"],
        ))
        statistic_labels = [
            ("count", "Valid count"), ("mean", "Mean"),
            ("std", "Std dev"), ("min", "Min"),
            ("q1", "Q1 (25%)"), ("median_q2", "Median (Q2)"),
            ("q3", "Q3 (75%)"), ("max", "Max"),
        ]
        columns = list(numeric_summary.columns)
        for start in range(0, len(columns), 4):
            group = columns[start:start + 4]
            story.append(Spacer(1, 8))
            story.append(_table(
                ["Statistic", *group],
                [[label, *[_stat_text(numeric_summary.loc[key, column])
                           for column in group]]
                 for key, label in statistic_labels],
                [available_width * 0.22] +
                [available_width * 0.78 / len(group)] * len(group),
                styles,
            ))

    for check_name, results in report["checks"].items():
        story.append(CondPageBreak(1.0 * inch))
        story.append(Paragraph(f"{escape(check_name.title())} checks", styles["Heading2"]))
        story.append(_table(
            ["Column", "Status", "Classification", "Findings", "Reason"],
            [[result["column"] if result["column"] is not None else "Whole dataset",
              result["status"], result["classification"],
              result["metrics"]["finding_count"], result["reason"]]
             for result in results],
            [available_width * 0.18, available_width * 0.13,
             available_width * 0.22, available_width * 0.10,
             available_width * 0.37],
            styles,
        ))

    document.build(story, onFirstPage=_draw_footer, onLaterPages=_draw_footer)
    return output.getvalue()
