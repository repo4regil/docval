"""
metadata_store.py
------------------
Holds globally accessible metadata about the currently uploaded document.

These simple module-level variables can be imported from any module,
for example::

    from metadata_store import (
        document_title,
        document_version,
        company_name,
        author_name,
    )

and will reflect the values last saved via :func:`set_document_metadata`.
"""

from typing import Tuple

# ---------------------------------------------------------------------------
# Global metadata variables
# ---------------------------------------------------------------------------

document_title: str = ""
document_version: str = ""
company_name: str = ""
author_name: str = ""


def set_document_metadata(
    title: str,
    version: str,
    company: str,
    author: str,
) -> None:
    """
    Update the global document metadata values.

    All parameters are stored as strings and can be accessed from any module
    that imports this module.
    """
    global document_title, document_version, company_name, author_name

    document_title = str(title)
    document_version = str(version)
    company_name = str(company)
    author_name = str(author)


def get_document_metadata() -> Tuple[str, str, str, str]:
    """Return the current document metadata as a tuple."""
    return document_title, document_version, company_name, author_name


