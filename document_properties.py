"""
document_properties.py
-----------------------
Extracts metadata and structural statistics from a python-docx Document.

The function returns a :class:`~models.DocumentProperties` instance which
is then displayed in the UI and logged for audit purposes.
"""

import logging
from typing import Optional

from docx import Document

from models import DocumentProperties


def extract_properties(
    doc: Document,
    logger: logging.Logger,
) -> DocumentProperties:
    """
    Extract core properties and structural stats from *doc*.

    Parameters
    ----------
    doc : docx.Document
        An already-opened python-docx Document object.
    logger : logging.Logger
        Session logger.

    Returns
    -------
    DocumentProperties
        Populated dataclass; missing fields are ``None``.
    """
    logger.info("Extracting document properties …")
    props = doc.core_properties

    # ------------------------------------------------------------------
    # Helper: safely convert datetime to ISO string
    # ------------------------------------------------------------------
    def _dt(value) -> Optional[str]:
        try:
            return value.isoformat() if value else None
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Structural counts
    # ------------------------------------------------------------------
    section_count = len(doc.sections)
    word_count    = _count_words(doc)
    page_count    = _get_total_pages(doc, logger)

    dp = DocumentProperties(
        title             = props.title            or None,
        subject           = props.subject          or None,
        author            = props.author           or None,
        last_modified_by  = props.last_modified_by or None,
        created           = _dt(props.created),
        modified          = _dt(props.modified),
        revision          = str(props.revision) if props.revision else None,
        keywords          = props.keywords         or None,
        description       = props.description      or None,
        page_count        = page_count,
        word_count        = word_count,
        section_count     = section_count,
    )

    logger.info(
        "Properties extracted – title=%r, author=%r, pages≈%s, words≈%s",
        dp.title, dp.author, dp.page_count, dp.word_count,
    )
    return dp


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _count_words(doc: Document) -> int:
    """
    Count words across all paragraphs in the document body.

    This is a simple whitespace-split count and does not match Word's
    built-in word count exactly, but it provides a useful approximation.
    """
    total = 0
    for para in doc.paragraphs:
        total += len(para.text.split())
    return total


def _get_total_pages(doc: Document, logger: logging.Logger) -> int:
    """
    Try to determine the actual total number of pages in *doc*.

    Strategy
    --------
    1. Look for a NUMPAGES field in any footer. When the document has been
       updated in Word, this usually contains the true total page count,
       including blank pages.
    2. If no such field (or it cannot be parsed), fall back to a conservative
       estimate based on explicit page breaks and section breaks.
    """
    try:
        from docx.oxml import OxmlElement  # type: ignore[import]
    except Exception:
        # Fallback immediately if low-level XML helpers are unavailable
        logger.debug("docx.oxml helpers not available; using estimated page count.")
        return _estimate_pages(doc)

    # Search all section footers for a NUMPAGES field that carries the total.
    from docx.oxml.ns import qn

    def _parse_numpages_from_footer(footer) -> int:
        xml = footer._element.xml
        # Look for a pattern like 'NUMPAGES 12' or 'NUMPAGES  12 '
        import re

        m = re.search(r"NUMPAGES[^0-9]*(\d+)", xml)
        if m:
            return int(m.group(1))
        return 0

    max_pages = 0
    try:
        for section in doc.sections:
            footer = section.footer
            pages = _parse_numpages_from_footer(footer)
            if pages > max_pages:
                max_pages = pages
    except Exception as exc:  # noqa: BLE001
        logger.debug("Error while reading NUMPAGES from footer: %s", exc)

    if max_pages > 0:
        logger.debug("Total pages determined from NUMPAGES field: %d", max_pages)
        return max_pages

    # Fallback – keep existing estimation behaviour if NUMPAGES is not present
    logger.debug("NUMPAGES field not found; falling back to estimated pages.")
    return _estimate_pages(doc)


def _estimate_pages(doc: Document) -> int:
    """
    Estimate the number of pages when no NUMPAGES field is available.

    This maintains the previous behaviour so existing expectations are kept.
    """
    page_breaks = 0
    for para in doc.paragraphs:
        for run in para.runs:
            if run._r.xml.find("w:lastRenderedPageBreak") != -1:
                page_breaks += 1
            if run._r.xml.find('w:br w:type="page"') != -1:
                page_breaks += 1
        # Check paragraph-level page breaks via XML
        if "<w:pageBreakBefore/>" in para._p.xml:
            page_breaks += 1

    # Each section (except the first) typically starts on a new page
    section_breaks = max(0, len(doc.sections) - 1)

    return 1 + page_breaks + section_breaks
