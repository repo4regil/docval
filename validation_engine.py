"""
validation_engine.py
--------------------
Orchestrates all validation modules in sequence and yields progress
messages so the UI can show live status updates.

The engine is a *generator function* – each ``yield`` returns a progress
message string.  When the generator is exhausted the caller can retrieve
the completed :class:`~models.ValidationReport` from the ``report``
attribute of the generator object.

Usage (inside a Streamlit callback)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    gen = run_validation(doc, filename, logger)
    report = ValidationReport(filename=filename)

    for message in gen:
        # message is a human-readable status string
        st.write(message)

    report = gen.report   # available after the loop
"""

import logging
from typing import Generator

from docx import Document

from config import VALIDATION_TOGGLES, TABLE_HEADING_NAMES
from document_properties import extract_properties
from header_validator import validate_header
from footer_validator import validate_footer
from heading_validator import validate_heading
from table_extractor import get_tables_by_heading
from table_validator import validate_tables
from models import DocumentProperties, ValidationReport, Status, ValidationResult
from page_counter import get_exact_page_count


# ---------------------------------------------------------------------------
# Generator-based engine
# ---------------------------------------------------------------------------

class ValidationEngine:
    """
    Runs all validation steps and exposes results through a generator
    so the UI can stream live progress messages.

    Parameters
    ----------
    doc : docx.Document
        An opened python-docx Document.
    filename : str
        Original uploaded filename (used in the report).
    logger : logging.Logger
        Session logger.

    Examples
    --------
    ::

        engine = ValidationEngine(doc, "MyDoc.docm", logger)
        for msg in engine.run():
            display(msg)
        report    = engine.report
        doc_props = engine.doc_properties
    """

    def __init__(self, doc: Document, filename: str, logger: logging.Logger, tmp_path: str | None = None):
        self.doc          = doc
        self.filename     = filename
        self.logger       = logger
        self.report       = ValidationReport(filename=filename)
        self.doc_props    = None          # filled during run()
        self.tables_index = {}            # filled during run()
        self.tmp_path     = tmp_path

    # ------------------------------------------------------------------
    # Main generator
    # ------------------------------------------------------------------

    def run(self) -> Generator[str, None, None]:
        """
        Run all validation steps, yielding a status string before each step.

        Yields
        ------
        str
            Human-readable progress message for display in the UI.
        """
        logger = self.logger
        logger.info("=== Validation run started for: %s ===", self.filename)

        exact_pages: int | None = None

        # -----------------------------------------------------------
        # Step 1: Extract document properties
        # -----------------------------------------------------------
        if VALIDATION_TOGGLES.get("document_properties", True):
            yield "📋 Extracting document properties…"
            try:
                self.doc_props = extract_properties(self.doc, logger)
                yield "✅ Document properties extracted."
            except Exception as exc:  # noqa: BLE001
                logger.exception("Property extraction failed: %s", exc)
                yield f"⚠️ Property extraction error: {exc}"
                self.doc_props = None
        else:
            yield "⏭️ Document properties check skipped (disabled in config)."

        # Try to obtain an exact page count via Word COM using the temp path.
        if self.tmp_path:
            try:
                exact_pages = get_exact_page_count(self.tmp_path, logger)
                if exact_pages is not None and self.doc_props is not None:
                    # Keep properties view consistent with the exact count
                    self.doc_props.page_count = exact_pages
                    logger.info("Using exact page count from Word: %d", exact_pages)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Exact page count retrieval failed: %s", exc)

        # -----------------------------------------------------------
        # Step 2: Header validation
        # -----------------------------------------------------------
        if VALIDATION_TOGGLES.get("header_checks", True):
            yield "🔍 Validating document header…"
            try:
                results = validate_header(self.doc, logger)
                self.report.extend(results)
                fail_count = sum(1 for r in results if r.status == Status.FAIL)
                yield (
                    f"✅ Header validation done – "
                    f"{len(results) - fail_count} passed, {fail_count} failed."
                )
            except Exception as exc:  # noqa: BLE001
                logger.exception("Header validation crashed: %s", exc)
                yield f"⚠️ Header validation error: {exc}"
        else:
            yield "⏭️ Header checks skipped (disabled in config)."

        # -----------------------------------------------------------
        # Step 3: Footer validation
        # -----------------------------------------------------------
        if VALIDATION_TOGGLES.get("footer_checks", True):
            yield "🔍 Validating document footer…"
            try:
                total_pages_for_footer = exact_pages
                if total_pages_for_footer is None and self.doc_props is not None:
                    total_pages_for_footer = self.doc_props.page_count

                results = validate_footer(self.doc, logger, total_pages=total_pages_for_footer)
                self.report.extend(results)
                fail_count = sum(1 for r in results if r.status == Status.FAIL)
                yield (
                    f"✅ Footer validation done – "
                    f"{len(results) - fail_count} passed, {fail_count} failed."
                )
            except Exception as exc:  # noqa: BLE001
                logger.exception("Footer validation crashed: %s", exc)
                yield f"⚠️ Footer validation error: {exc}"
        else:
            yield "⏭️ Footer checks skipped (disabled in config)."

        # -----------------------------------------------------------
        # Step 4: Heading validation
        # -----------------------------------------------------------
        if VALIDATION_TOGGLES.get("heading_check", True):
            yield "🔍 Validating document heading…"
            try:
                results = validate_heading(self.doc, logger)
                self.report.extend(results)
                fail_count = sum(1 for r in results if r.status == Status.FAIL)
                yield (
                    f"✅ Heading validation done – "
                    f"{len(results) - fail_count} passed, {fail_count} failed."
                )
            except Exception as exc:  # noqa: BLE001
                logger.exception("Heading validation crashed: %s", exc)
                yield f"⚠️ Heading validation error: {exc}"
        else:
            yield "⏭️ Heading check skipped (disabled in config)."

        # -----------------------------------------------------------
        # Step 5: Table extraction
        # -----------------------------------------------------------
        if VALIDATION_TOGGLES.get("table_extraction", True):
            yield f"📊 Extracting tables under {len(TABLE_HEADING_NAMES)} heading(s)…"
            try:
                self.tables_index = get_tables_by_heading(
                    self.doc, TABLE_HEADING_NAMES, logger
                )
                found = sum(1 for v in self.tables_index.values() if v)
                yield f"✅ Table extraction done – {found}/{len(TABLE_HEADING_NAMES)} table(s) found."
            except Exception as exc:  # noqa: BLE001
                logger.exception("Table extraction crashed: %s", exc)
                yield f"⚠️ Table extraction error: {exc}"
                self.tables_index = {}
        else:
            yield "⏭️ Table extraction skipped (disabled in config)."

        # -----------------------------------------------------------
        # Step 6: Table content + cross-validation
        # -----------------------------------------------------------
        if VALIDATION_TOGGLES.get("table_cross_validate", True):
            yield "🔗 Validating table content and cross-references…"
            try:
                results = validate_tables(self.tables_index, logger)
                self.report.extend(results)
                fail_count = sum(1 for r in results if r.status == Status.FAIL)
                yield (
                    f"✅ Table validation done – "
                    f"{len(results) - fail_count} passed, {fail_count} failed."
                )
            except Exception as exc:  # noqa: BLE001
                logger.exception("Table validation crashed: %s", exc)
                yield f"⚠️ Table validation error: {exc}"
        else:
            yield "⏭️ Table cross-validation skipped (disabled in config)."

        # -----------------------------------------------------------
        # Done
        # -----------------------------------------------------------
        logger.info("=== Validation complete. Summary: %s ===", self.report.summary())
        yield f"🏁 Validation complete! {self.report.summary()}"
