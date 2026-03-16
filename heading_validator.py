"""
heading_validator.py
---------------------
Validates that the document contains the required top-level heading(s).

Checks performed
~~~~~~~~~~~~~~~~
1. At least one paragraph with "Heading 1" style exists.
2. If ``config.EXPECTED_DOCUMENT_HEADING`` is set, the first Heading 1
   text must match it (case-insensitive, partial match).
"""

import logging
from typing import List

from docx import Document

from config import EXPECTED_DOCUMENT_HEADING, HEADING_STYLES
from models import Status, ValidationResult

CATEGORY = "Document Heading"


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def validate_heading(doc: Document, logger: logging.Logger) -> List[ValidationResult]:
    """
    Validate that the document heading structure is correct.

    Parameters
    ----------
    doc : docx.Document
        An opened python-docx Document.
    logger : logging.Logger
        Session logger.

    Returns
    -------
    list of ValidationResult
    """
    logger.info("--- Heading validation started ---")
    results: List[ValidationResult] = []

    # ------------------------------------------------------------------
    # Collect all heading paragraphs
    # ------------------------------------------------------------------
    headings: List[tuple] = []  # (level_int, text)
    for para in doc.paragraphs:
        style_name = para.style.name if para.style else ""
        for h_style in HEADING_STYLES:
            if style_name.startswith(h_style):
                try:
                    level = int(style_name.split()[-1])
                except ValueError:
                    level = 99
                headings.append((level, para.text.strip()))
                break

    logger.debug("Found %d heading paragraph(s): %s", len(headings), headings)

    # ------------------------------------------------------------------
    # Check 1: At least one Heading 1 exists
    # ------------------------------------------------------------------
    h1_headings = [(lvl, txt) for lvl, txt in headings if lvl == 1]
    if h1_headings:
        results.append(ValidationResult(
            category=CATEGORY,
            check="has_heading_1",
            label="Heading 1 Present",
            status=Status.PASS,
            message=f"Found {len(h1_headings)} Heading 1 paragraph(s).",
            details={"headings": [txt for _, txt in h1_headings]},
        ))
    else:
        results.append(ValidationResult(
            category=CATEGORY,
            check="has_heading_1",
            label="Heading 1 Present",
            status=Status.FAIL,
            message=(
                "No paragraph with 'Heading 1' style found. "
                "The document must have at least one top-level heading."
            ),
        ))

    logger.info(
        "[%s] has_heading_1 – %s", CATEGORY, results[-1].status.value
    )

    # ------------------------------------------------------------------
    # Check 2: Expected heading text match (optional)
    # ------------------------------------------------------------------
    if EXPECTED_DOCUMENT_HEADING:
        expected = EXPECTED_DOCUMENT_HEADING.strip().lower()
        matched = next(
            (txt for _, txt in h1_headings if expected in txt.lower()),
            None,
        )
        if matched:
            results.append(ValidationResult(
                category=CATEGORY,
                check="heading_text_match",
                label="Expected Heading Text",
                status=Status.PASS,
                message=f'Expected heading text matched: "{matched}"',
            ))
        else:
            results.append(ValidationResult(
                category=CATEGORY,
                check="heading_text_match",
                label="Expected Heading Text",
                status=Status.FAIL,
                message=(
                    f'Expected heading containing "{EXPECTED_DOCUMENT_HEADING}" '
                    f"not found. Actual Heading 1(s): "
                    f"{[txt for _, txt in h1_headings] or ['(none)']}"
                ),
            ))
        logger.info(
            "[%s] heading_text_match – %s", CATEGORY, results[-1].status.value
        )
    else:
        results.append(ValidationResult(
            category=CATEGORY,
            check="heading_text_match",
            label="Expected Heading Text",
            status=Status.SKIP,
            message=(
                "EXPECTED_DOCUMENT_HEADING not configured. "
                "Set it in config.py to enable this check."
            ),
        ))

    logger.info("--- Heading validation complete ---")
    return results
