"""
ui_components.py
----------------
Reusable Streamlit UI components used by ``app.py``.

Keeping UI rendering logic separate from the main app file makes it easy
to change the look-and-feel without touching business logic.
"""

import streamlit as st
from typing import Dict, List, Optional

from models import DocumentProperties, Status, ValidationReport, ValidationResult


# ---------------------------------------------------------------------------
# Status icon & colour helpers
# ---------------------------------------------------------------------------

_STATUS_ICON: Dict[Status, str] = {
    Status.PASS: "✅",
    Status.FAIL: "❌",
    Status.WARN: "⚠️",
    Status.SKIP: "⏭️",
}

_STATUS_COLOR: Dict[Status, str] = {
    Status.PASS: "#1a7f37",   # green
    Status.FAIL: "#cf222e",   # red
    Status.WARN: "#d1a000",   # amber
    Status.SKIP: "#6e7781",   # grey
}

_STATUS_BG: Dict[Status, str] = {
    Status.PASS: "#dafbe1",
    Status.FAIL: "#ffeef0",
    Status.WARN: "#fff8c5",
    Status.SKIP: "#f6f8fa",
}


# ---------------------------------------------------------------------------
# Document properties panel
# ---------------------------------------------------------------------------

def render_property_table(props: Optional[DocumentProperties]) -> None:
    """
    Display document core properties in an expandable styled table.

    Parameters
    ----------
    props : DocumentProperties or None
        Extracted properties.  If None, a warning is shown.
    """
    with st.expander("📋 Document Properties", expanded=True):
        if props is None:
            st.warning("Document properties could not be extracted.")
            return

        display = props.to_display_dict()
        col1, col2 = st.columns(2)
        items = list(display.items())
        half = (len(items) + 1) // 2

        with col1:
            for key, val in items[:half]:
                st.markdown(
                    f"<div style='margin-bottom:6px'>"
                    f"<span style='color:#6e7781;font-size:0.82rem;'>{key}</span><br>"
                    f"<span style='font-weight:600'>{val}</span></div>",
                    unsafe_allow_html=True,
                )

        with col2:
            for key, val in items[half:]:
                st.markdown(
                    f"<div style='margin-bottom:6px'>"
                    f"<span style='color:#6e7781;font-size:0.82rem;'>{key}</span><br>"
                    f"<span style='font-weight:600'>{val}</span></div>",
                    unsafe_allow_html=True,
                )


# ---------------------------------------------------------------------------
# Validation results panel
# ---------------------------------------------------------------------------

def render_validation_report(report: ValidationReport) -> None:
    """
    Display the validation report with colour-coded cards grouped by category.

    Parameters
    ----------
    report : ValidationReport
        The completed report from the ValidationEngine.
    """
    st.markdown("---")

    # ------------------------------------------------------------------
    # Summary banner
    # ------------------------------------------------------------------
    total   = len(report.results)
    passed  = len(report.passed)
    failed  = len(report.failed)
    warned  = len(report.warnings)
    skipped = len(report.skipped)

    if report.is_valid:
        banner_color = "#1a7f37"
        banner_bg    = "#dafbe1"
        banner_icon  = "✅"
        banner_text  = "All checks passed — document is valid!"
    else:
        banner_color = "#cf222e"
        banner_bg    = "#ffeef0"
        banner_icon  = "❌"
        banner_text  = f"{failed} check(s) failed — please review the issues below."

    st.markdown(
        f"""
        <div style="
            background:{banner_bg};
            border-left: 5px solid {banner_color};
            padding: 14px 18px;
            border-radius: 6px;
            margin-bottom: 16px;
        ">
            <span style="font-size:1.25rem;font-weight:700;color:{banner_color};">
                {banner_icon} {banner_text}
            </span>
            <br>
            <span style="color:#57606a;font-size:0.9rem;">
                {passed} passed &nbsp;·&nbsp;
                {failed} failed &nbsp;·&nbsp;
                {warned} warning(s) &nbsp;·&nbsp;
                {skipped} skipped &nbsp;/&nbsp;
                {total} total
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ------------------------------------------------------------------
    # Result cards grouped by category
    # ------------------------------------------------------------------
    grouped = report.by_category()
    for category, results in grouped.items():
        st.markdown(
            f"<h4 style='margin-top:1rem;margin-bottom:0.4rem;'>{category}</h4>",
            unsafe_allow_html=True,
        )
        for result in results:
            _render_result_card(result)


def _render_result_card(result: ValidationResult) -> None:
    """Render a single validation result as a styled card."""
    icon  = _STATUS_ICON.get(result.status, "•")
    color = _STATUS_COLOR.get(result.status, "#000")
    bg    = _STATUS_BG.get(result.status, "#fff")

    details_html = ""
    if result.status == Status.FAIL and result.details:
        # Render missing values list for cross-validation failures
        if "missing_values" in result.details:
            missing = result.details["missing_values"]
            items_html = "".join(f"<li>{v}</li>" for v in missing)
            details_html = (
                f"<ul style='margin:4px 0 0 16px;font-size:0.85rem;'>{items_html}</ul>"
            )
        # Render table rows for table extraction results
        elif "rows" in result.details and result.details["rows"]:
            rows = result.details["rows"]
            sample = rows[:3]
            table_rows = "".join(
                "<tr>" + "".join(f"<td style='padding:2px 6px;'>{v}</td>" for v in row.values()) + "</tr>"
                for row in sample
            )
            headers = "".join(
                f"<th style='padding:2px 6px;text-align:left;'>{k}</th>"
                for k in rows[0].keys()
            )
            details_html = (
                f"<table style='font-size:0.8rem;margin-top:6px;border-collapse:collapse;'>"
                f"<thead><tr>{headers}</tr></thead>"
                f"<tbody>{table_rows}</tbody></table>"
                + (f"<span style='font-size:0.75rem;color:#6e7781;'>…and {len(rows)-3} more row(s)</span>" if len(rows) > 3 else "")
            )

    st.markdown(
        f"""
        <div style="
            background:{bg};
            border-left: 4px solid {color};
            padding: 10px 14px;
            border-radius: 5px;
            margin-bottom: 8px;
        ">
            <span style="font-size:1rem;font-weight:600;color:{color};">
                {icon} {result.label}
            </span>
            <br>
            <span style="font-size:0.88rem;color:#24292f;">{result.message}</span>
            {details_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Progress display
# ---------------------------------------------------------------------------

def render_progress_line(message: str) -> None:
    """
    Write a single progress line.  Intended to be used inside a
    ``st.empty()`` container that is updated on each generator yield.

    Parameters
    ----------
    message : str
        Progress string from the ValidationEngine.
    """
    st.markdown(
        f"<div style='font-size:0.9rem;padding:3px 0;color:#24292f;'>{message}</div>",
        unsafe_allow_html=True,
    )
