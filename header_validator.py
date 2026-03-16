"""
header_validator.py
-------------------
Validates the content of the document header section.

Each check is an isolated function that returns a :class:`~models.ValidationResult`.
To add a new header check:
  1. Write a ``_check_<name>(header_section, logger)`` function.
  2. Add it to the ``HEADER_CHECKS`` list in config.py.
"""

import logging
import re
from typing import List

from docx.section import _Header  # type: ignore[attr-defined]
from docx import Document

from config import HEADER_CHECKS
from models import Status, ValidationResult

CATEGORY = "Header"


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def validate_header(doc: Document, logger: logging.Logger) -> List[ValidationResult]:
    """
    Run all enabled header checks and return their results.

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
    logger.info("--- Header validation started ---")
    results: List[ValidationResult] = []

    # Grab the default section header (first section)
    try:
        header = doc.sections[0].header
    except IndexError:
        logger.error("Document has no sections – cannot read header.")
        results.append(ValidationResult(
            category=CATEGORY,
            check="header_access",
            label="Header Access",
            status=Status.FAIL,
            message="Document has no sections; header could not be read.",
        ))
        return results

    check_map = {
        "has_logo_image": _check_logo_image,
        "has_document_title": _check_document_title,
        "has_version_string": _check_version_string,
    }

    for check_key, check_fn in check_map.items():
        if not HEADER_CHECKS.get(check_key, True):
            results.append(ValidationResult(
                category=CATEGORY,
                check=check_key,
                label=check_key.replace("_", " ").title(),
                status=Status.SKIP,
                message="Check disabled in configuration.",
            ))
            logger.debug("Skipping header check: %s", check_key)
            continue

        result = check_fn(header, logger)
        results.append(result)
        logger.info("[%s] %s – %s", CATEGORY, result.check, result.status.value)

    logger.info("--- Header validation complete ---")
    return results


# ---------------------------------------------------------------------------
# Individual check functions
# ---------------------------------------------------------------------------

def _check_logo_image(header, logger: logging.Logger) -> ValidationResult:
    """
    Check that at least one inline image (logo) is present in the header.

    python-docx surfaces embedded images via ``InlineShape`` objects in the
    header's XML relationships.  We check for the presence of ``<pic:pic>``
    or ``<v:imagedata>`` XML nodes as a reliable indicator.
    """
    label = "Logo / Image in Header"
    try:
        header_xml = header._element.xml
        has_image = (
            "<pic:pic" in header_xml
            or "<v:imagedata" in header_xml
            or "blipFill" in header_xml
            or "w:drawing" in header_xml
        )
        if has_image:
            return ValidationResult(
                category=CATEGORY,
                check="has_logo_image",
                label=label,
                status=Status.PASS,
                message="At least one image element found in the header.",
            )
        else:
            return ValidationResult(
                category=CATEGORY,
                check="has_logo_image",
                label=label,
                status=Status.FAIL,
                message=(
                    "No image element detected in the header. "
                    "A company logo is expected."
                ),
            )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error checking header logo: %s", exc)
        return ValidationResult(
            category=CATEGORY,
            check="has_logo_image",
            label=label,
            status=Status.WARN,
            message=f"Could not inspect header for images: {exc}",
        )


def _check_document_title(header, logger: logging.Logger) -> ValidationResult:
    """
    Check that the header contains non-empty readable text (document title).

    We concatenate all paragraph text in the header and verify it is not blank.
    """
    label = "Document Title in Header"
    try:
        text = " ".join(p.text.strip() for p in header.paragraphs).strip()
        if text:
            return ValidationResult(
                category=CATEGORY,
                check="has_document_title",
                label=label,
                status=Status.PASS,
                message=f'Header contains text: {text[:80]}{"…" if len(text) > 80 else ""}',
            )
        else:
            return ValidationResult(
                category=CATEGORY,
                check="has_document_title",
                label=label,
                status=Status.FAIL,
                message="Header paragraphs are empty. Document title is missing from the header.",
            )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error checking header title: %s", exc)
        return ValidationResult(
            category=CATEGORY,
            check="has_document_title",
            label=label,
            status=Status.WARN,
            message=f"Could not read header text: {exc}",
        )


def _check_version_string(header, logger: logging.Logger) -> ValidationResult:
    """
    Check that the header contains a version-like string (e.g. v1.0, 1.2.3).
    """
    label = "Version String in Header"
    # Pattern: optional 'v', one or more digit groups separated by dots
    version_pattern = re.compile(r"\bv?\d+(\.\d+)+\b", re.IGNORECASE)
    try:
        text = " ".join(p.text for p in header.paragraphs)
        match = version_pattern.search(text)
        if match:
            return ValidationResult(
                category=CATEGORY,
                check="has_version_string",
                label=label,
                status=Status.PASS,
                message=f"Version string found in header: {match.group()}",
            )
        else:
            return ValidationResult(
                category=CATEGORY,
                check="has_version_string",
                label=label,
                status=Status.FAIL,
                message=(
                    "No version string detected in the header. "
                    "Expected format: v1.0 or 1.2.3"
                ),
            )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error checking header version: %s", exc)
        return ValidationResult(
            category=CATEGORY,
            check="has_version_string",
            label=label,
            status=Status.WARN,
            message=f"Could not read header text for version check: {exc}",
        )
