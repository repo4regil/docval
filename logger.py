"""
logger.py
---------
Sets up a per-upload, timestamped log file for every document validation
session.  A new log file is created each time a document is uploaded so
that audit trails remain independent and easy to archive.

Usage
-----
    from logger import setup_logger

    logger = setup_logger("my_document.docm")
    logger.info("Validation started")
"""

import logging
import os
from datetime import datetime

from config import LOG_DIR, LOG_LEVEL


def setup_logger(original_filename: str) -> logging.Logger:
    """
    Create and return a logger that writes to a timestamped file.

    The log file is placed in the ``logs/`` directory and named:
        ``<YYYYMMDD_HHMMSS>_<original_filename_stem>.log``

    Parameters
    ----------
    original_filename : str
        The name of the uploaded file (e.g. ``"MyDoc.docm"``).  Used only
        to build a human-readable log file name.

    Returns
    -------
    logging.Logger
        A fully configured logger instance.  A ``StreamHandler`` (console)
        is also attached for developer convenience.
    """
    # Ensure the log directory exists.
    os.makedirs(LOG_DIR, exist_ok=True)

    # Build a unique logger name based on the timestamp to avoid collisions
    # when multiple uploads happen within the same Python session.
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    stem = os.path.splitext(original_filename)[0]
    # Sanitise the stem: replace spaces / special chars with underscores.
    safe_stem = "".join(c if c.isalnum() or c in "-_" else "_" for c in stem)

    log_filename = f"{timestamp}_{safe_stem}.log"
    log_path = os.path.join(LOG_DIR, log_filename)

    logger_name = f"doc_validator.{timestamp}.{safe_stem}"
    logger = logging.getLogger(logger_name)
    logger.setLevel(getattr(logging, LOG_LEVEL, logging.DEBUG))

    # Avoid adding duplicate handlers if setup_logger is called more than once
    # for the same logger name within a session.
    if logger.handlers:
        logger.handlers.clear()

    # ------------------------------------------------------------------
    # File handler – persists all messages to disk.
    # ------------------------------------------------------------------
    file_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(getattr(logging, LOG_LEVEL, logging.DEBUG))
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # ------------------------------------------------------------------
    # Console / stream handler – useful for local development.
    # ------------------------------------------------------------------
    console_formatter = logging.Formatter(
        fmt="%(levelname)-8s | %(message)s"
    )
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    logger.info("=" * 60)
    logger.info("Document Validator – Session Started")
    logger.info("Log file   : %s", log_path)
    logger.info("Upload file: %s", original_filename)
    logger.info("=" * 60)

    # Attach the log file path as an attribute so callers can reference it.
    logger.log_file_path = log_path  # type: ignore[attr-defined]

    return logger
