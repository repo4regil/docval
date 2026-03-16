"""
page_counter.py
----------------
Obtain an exact page count for a Word document by asking Microsoft Word
via the COM automation API (Windows only).

This avoids relying on heuristics inside python-docx and returns the
same total page count that Word shows to the user, including blank pages.
"""

import logging
from typing import Optional

try:  # Import lazily so non-Windows environments still import the module
    import win32com.client  # type: ignore[import]
except Exception:  # pragma: no cover - import guards
    win32com = None  # type: ignore[assignment]


def get_exact_page_count(path: str, logger: logging.Logger) -> Optional[int]:
    """
    Return the exact total number of pages in the document at *path*.

    This uses Microsoft Word's pagination engine via COM:

    - Opens the document read-only
    - Calls ``ComputeStatistics(wdStatisticPages)``
    - Closes the document and quits Word

    Parameters
    ----------
    path : str
        Full path to the .docx/.docm file on disk.
    logger : logging.Logger
        Session logger.

    Returns
    -------
    int or None
        Exact page count, or None if Word/COM is not available or an
        error occurs.
    """
    if win32com is None:
        logger.debug("win32com is not available; cannot compute exact page count.")
        return None

    wdStatisticPages = 2  # Word constant for page count
    word_app = None
    doc = None

    try:
        word_app = win32com.client.Dispatch("Word.Application")  # type: ignore[attr-defined]
        word_app.Visible = False
        word_app.DisplayAlerts = 0  # wdAlertsNone

        doc = word_app.Documents.Open(path, ReadOnly=True)
        pages = int(doc.ComputeStatistics(wdStatisticPages))
        logger.debug("Exact page count from Word for %s: %d", path, pages)
        return pages
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to get exact page count via Word COM for %s: %s", path, exc)
        return None
    finally:
        try:
            if doc is not None:
                doc.Close(False)
        except Exception:
            pass
        try:
            if word_app is not None:
                word_app.Quit()
        except Exception:
            pass


