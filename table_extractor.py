"""
table_extractor.py
------------------
Walks the document body and maps heading paragraphs to the tables that
immediately follow them.

The extractor uses a two-pass approach:
1. Build a flat ordered list of (paragraph | table) body elements.
2. For each known heading name, find the matching heading element and
   return the first table that follows it (if any).

The result is a dict keyed by heading name:

    {
        "Change History":  [{"Date": "...", "Author": "...", ...}, ...],
        "Approvals":       [{"Role": "...", "Name": "...", ...}, ...],
    }

Heading names are matched case-insensitively and with leading/trailing
whitespace stripped.
"""

import logging
from typing import Dict, List, Optional

from docx import Document
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

from config import HEADING_STYLES


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

TableData   = List[Dict[str, str]]
TablesIndex = Dict[str, TableData]


def get_tables_by_heading(
    doc: Document,
    heading_names: List[str],
    logger: logging.Logger,
) -> TablesIndex:
    """
    Return table data for each heading listed in *heading_names*.

    Parameters
    ----------
    doc : docx.Document
        An opened python-docx Document.
    heading_names : list of str
        The heading texts (from ``config.TABLE_HEADING_NAMES``) to look for.
    logger : logging.Logger
        Session logger.

    Returns
    -------
    dict
        Keys are heading names (as supplied).  Values are lists of row-dicts.
        If a heading is not found or has no following table, its value is an
        empty list.
    """
    logger.info("Extracting tables for headings: %s", heading_names)

    # Normalise the target names for case-insensitive matching
    target_map = {name.strip().lower(): name for name in heading_names}
    result: TablesIndex = {name: [] for name in heading_names}

    # Build a flat list of body children (paragraphs + tables) in order
    body_elements = _ordered_body_elements(doc)

    # Walk the element list; when we hit a matching heading, grab the
    # next table in the sequence.
    i = 0
    while i < len(body_elements):
        elem_type, elem_obj = body_elements[i]

        if elem_type == "paragraph":
            para: Paragraph = elem_obj
            para_text = para.text.strip().lower()
            canonical_name = target_map.get(para_text)

            if canonical_name and _is_heading(para):
                logger.debug("Found target heading: %r", para.text.strip())

                # Look ahead for the first table
                j = i + 1
                while j < len(body_elements):
                    next_type, next_obj = body_elements[j]
                    if next_type == "table":
                        table_data = _table_to_list_of_dicts(next_obj)
                        result[canonical_name] = table_data
                        logger.info(
                            "Table under '%s': %d rows, columns: %s",
                            canonical_name,
                            len(table_data),
                            list(table_data[0].keys()) if table_data else [],
                        )
                        break
                    elif next_type == "paragraph" and _is_heading(next_obj):
                        # Encountered a new heading before finding a table
                        logger.warning(
                            "No table found under heading '%s' before next heading.",
                            canonical_name,
                        )
                        break
                    j += 1
                else:
                    logger.warning(
                        "Reached end of document without finding table under '%s'.",
                        canonical_name,
                    )

        i += 1

    # Log headings that were not found at all
    for heading in heading_names:
        if not result[heading]:
            logger.warning("Heading '%s' not found or has no associated table.", heading)

    return result


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _ordered_body_elements(doc: Document) -> List[tuple]:
    """
    Return a list of (type_str, object) tuples representing the document body
    children in document order.

    ``type_str`` is either ``"paragraph"`` or ``"table"``.
    """
    elements = []
    body = doc.element.body
    for child in body:
        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if tag == "p":
            # Wrap the XML element in a python-docx Paragraph proxy
            para = Paragraph(child, doc)
            elements.append(("paragraph", para))
        elif tag == "tbl":
            table = Table(child, doc)
            elements.append(("table", table))
    return elements


def _is_heading(para: Paragraph) -> bool:
    """Return True if the paragraph uses a heading style."""
    style_name = para.style.name if para.style else ""
    return any(style_name.startswith(h) for h in HEADING_STYLES)


def _table_to_list_of_dicts(table: Table) -> TableData:
    """
    Convert a python-docx Table into a list of dicts.

    The first row is treated as the header row; subsequent rows become data
    rows keyed by the header cell values.  Empty trailing columns are
    included but their values will be empty strings.
    """
    rows = table.rows
    if not rows:
        return []

    # Header row
    headers = [cell.text.strip() for cell in rows[0].cells]
    # Deduplicate headers (Word sometimes merges cells, producing duplicates)
    seen: Dict[str, int] = {}
    unique_headers = []
    for h in headers:
        if h in seen:
            seen[h] += 1
            unique_headers.append(f"{h}_{seen[h]}")
        else:
            seen[h] = 0
            unique_headers.append(h)

    data: TableData = []
    for row in rows[1:]:
        cells = [cell.text.strip() for cell in row.cells]
        row_dict = dict(zip(unique_headers, cells))
        data.append(row_dict)

    return data
