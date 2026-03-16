"""
document_loader.py
------------------
Handles loading a Word document (.docm / .docx) from raw uploaded bytes
into a ``python-docx`` Document object.

Design notes
~~~~~~~~~~~~
* python-docx cannot open ``.docm`` files by extension, but the underlying
  OOXML format (ZIP) is identical.  We rename the temp file to ``.docx``
  before opening so python-docx is happy.
* Temp files are placed in ``tmp/`` and cleaned up by calling
  ``clear_document()``.
"""

import io
import logging
import os
from typing import Optional, Tuple

import zipfile

from docx import Document

from config import ALLOWED_EXTENSIONS, TMP_DIR


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_document(
    file_bytes: bytes,
    original_filename: str,
    logger: logging.Logger,
) -> Tuple[Optional[object], Optional[str], Optional[str]]:
    """
    Save ``file_bytes`` to a temp file and open it as a python-docx Document.

    Parameters
    ----------
    file_bytes : bytes
        Raw bytes from ``st.file_uploader``.
    original_filename : str
        The user-supplied filename (used for extension validation & temp naming).
    logger : logging.Logger
        Session logger.

    Returns
    -------
    tuple of (Document | None, tmp_path | None, error_message | None)
        On success: (doc, tmp_path, None)
        On failure: (None, None, error_message)
    """
    logger.info("Loading document: %s (%d bytes)", original_filename, len(file_bytes))

    # ------------------------------------------------------------------
    # 1. Validate extension
    # ------------------------------------------------------------------
    ext = os.path.splitext(original_filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        msg = (
            f"Unsupported file type '{ext}'. "
            f"Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
        logger.warning(msg)
        return None, None, msg

    # ------------------------------------------------------------------
    # 2. Normalise .docm package so python-docx can read it as .docx
    # ------------------------------------------------------------------
    if ext == ".docm":
        try:
            file_bytes = _convert_docm_to_docx_bytes(file_bytes, logger)
        except Exception as exc:  # noqa: BLE001
            msg = f"Could not convert .docm package to .docx-compatible format: {exc}"
            logger.error(msg)
            return None, None, msg

    # ------------------------------------------------------------------
    # 3. Write to temp directory (always as .docx so python-docx can read it)
    # ------------------------------------------------------------------
    os.makedirs(TMP_DIR, exist_ok=True)
    tmp_filename = os.path.splitext(original_filename)[0] + "_tmp.docx"
    tmp_path = os.path.join(TMP_DIR, tmp_filename)

    try:
        with open(tmp_path, "wb") as fh:
            fh.write(file_bytes)
        logger.debug("Temp file written: %s", tmp_path)
    except OSError as exc:
        msg = f"Could not write temp file: {exc}"
        logger.error(msg)
        return None, None, msg

    # ------------------------------------------------------------------
    # 4. Open with python-docx
    # ------------------------------------------------------------------
    try:
        doc = Document(tmp_path)
        logger.info("Document opened successfully.")
        return doc, tmp_path, None
    except Exception as exc:  # noqa: BLE001
        msg = f"Failed to parse document: {exc}"
        logger.error(msg)
        # Clean up the temp file on parse failure
        _delete_file(tmp_path, logger)
        return None, None, msg


def clear_document(tmp_path: Optional[str], logger: logging.Logger) -> None:
    """
    Delete the temporary copy of the uploaded document from disk.

    Parameters
    ----------
    tmp_path : str or None
        Path returned by :func:`load_document`.  If None, this is a no-op.
    logger : logging.Logger
        Session logger.
    """
    if tmp_path:
        _delete_file(tmp_path, logger)
        logger.info("Temporary document removed from memory/disk.")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _delete_file(path: str, logger: logging.Logger) -> None:
    """Remove a single file, logging any errors."""
    try:
        if os.path.exists(path):
            os.remove(path)
            logger.debug("Deleted temp file: %s", path)
    except OSError as exc:
        logger.warning("Could not delete temp file %s: %s", path, exc)


def _convert_docm_to_docx_bytes(file_bytes: bytes, logger: logging.Logger) -> bytes:
    """
    Take the original .docm package bytes and return new bytes that look like
    a regular .docx package to python-docx.

    We don't touch the actual document XML, we only rewrite the
    ``[Content_Types].xml`` main document content type from the macro-enabled
    type to the standard document type.  This keeps the flow of:

    .docm bytes → temp .docx file → python-docx
    """
    macro_ct = "application/vnd.ms-word.document.macroEnabled.main+xml"
    docx_ct = "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"

    in_buf = io.BytesIO(file_bytes)
    out_buf = io.BytesIO()

    with zipfile.ZipFile(in_buf, "r") as zin, zipfile.ZipFile(
        out_buf, "w", zipfile.ZIP_DEFLATED
    ) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "[Content_Types].xml":
                try:
                    text = data.decode("utf-8")
                except UnicodeDecodeError:
                    logger.warning(
                        "Could not decode [Content_Types].xml as UTF-8; "
                        "leaving content types unchanged."
                    )
                else:
                    if macro_ct in text:
                        text = text.replace(macro_ct, docx_ct)
                        logger.debug(
                            "Rewrote macro-enabled content type to standard docx type."
                        )
                    data = text.encode("utf-8")
            zout.writestr(item, data)

    return out_buf.getvalue()
