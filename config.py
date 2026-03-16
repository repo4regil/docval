"""
config.py
---------
Central configuration for the Document Validator application.
All tunable constants, heading names, validation rule toggles, and
path settings live here. Edit this file to customise behaviour without
touching the core logic.
"""

import os

# ---------------------------------------------------------------------------
# Application metadata
# ---------------------------------------------------------------------------
APP_TITLE = "Document Validator"
APP_VERSION = "1.0.0"
APP_ICON = "📄"

# ---------------------------------------------------------------------------
# File handling
# ---------------------------------------------------------------------------
# Accepted file extensions (lowercase). Add ".docx" here to also accept plain
# Word documents.
ALLOWED_EXTENSIONS = [".docm"]

# Temporary directory where uploaded files are saved for processing.
TMP_DIR = os.path.join(os.path.dirname(__file__), "tmp")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
LOG_LEVEL = "DEBUG"          # DEBUG | INFO | WARNING | ERROR

# ---------------------------------------------------------------------------
# Document properties to extract
# These are the core-properties keys exposed by python-docx.
# ---------------------------------------------------------------------------
PROPERTY_FIELDS = [
    "title",
    "subject",
    "author",
    "last_modified_by",
    "created",
    "modified",
    "revision",
    "keywords",
    "description",
]

# ---------------------------------------------------------------------------
# Header validation rules
# Each key maps to a human-readable label shown in the results panel.
# Set the value to True to enable the check, False to skip it.
# ---------------------------------------------------------------------------
HEADER_CHECKS = {
    "has_logo_image":      True,    # At least one image (logo) in the header
    "has_document_title":  True,    # A text run containing the doc title
    "has_version_string":  True,    # Text that looks like a version (e.g. "v1.0")
}

# ---------------------------------------------------------------------------
# Footer validation rules
# ---------------------------------------------------------------------------
FOOTER_CHECKS = {
    "has_confidentiality_label": True,   # e.g. "Confidential" text
    "has_page_number_field":     True,   # PAGE / NUMPAGES fields
    "has_company_name":          True,   # A known company name string
}

# Company name to search for in the footer.
# Update this to match your organisation's footer template.
COMPANY_NAME = "Your Company Name"       # <-- UPDATE THIS

# ---------------------------------------------------------------------------
# Heading validation
# ---------------------------------------------------------------------------
# The expected document title / top-level heading text (exact or partial match).
# Leave empty ("") to skip this check.
EXPECTED_DOCUMENT_HEADING = ""           # <-- UPDATE THIS if needed

# Heading style names used in python-docx (Word's built-in names).
HEADING_STYLES = ["Heading 1", "Heading 2", "Heading 3"]

# ---------------------------------------------------------------------------
# Table extraction – headings that precede tables we want to extract.
# The validator will find the first table that immediately follows a paragraph
# styled as any of the HEADING_STYLES AND whose text matches one of these names
# (case-insensitive, stripped).
# ---------------------------------------------------------------------------
TABLE_HEADING_NAMES = [
    "Change History",       # <-- UPDATE with your actual heading names
    "Approvals",
    "Review Matrix",
]

# ---------------------------------------------------------------------------
# Table cross-validation rules
# Define which two tables to cross-validate and what columns must match.
# Format:  (source_heading, source_column, target_heading, target_column)
# ---------------------------------------------------------------------------
TABLE_CROSS_VALIDATION_RULES = [
    # Example: every person listed in "Approvals > Name" must also appear
    # in "Review Matrix > Reviewer Name".
    # ("Approvals", "Name", "Review Matrix", "Reviewer Name"),
]

# ---------------------------------------------------------------------------
# Validation engine – toggle entire validators on / off
# ---------------------------------------------------------------------------
VALIDATION_TOGGLES = {
    "document_properties":  True,
    "header_checks":        True,
    "footer_checks":        True,
    "heading_check":        True,
    "table_extraction":     True,
    "table_cross_validate": True,
}
