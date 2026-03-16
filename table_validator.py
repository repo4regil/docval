"""
table_validator.py
------------------
Validates the content of extracted tables and performs cross-validation
between two tables as configured in ``config.TABLE_CROSS_VALIDATION_RULES``.

Checks performed
~~~~~~~~~~~~~~~~
1. For each heading in ``TABLE_HEADING_NAMES``:
   - Table was found under the heading.
   - Table is not empty (has at least one data row).
2. Cross-validation: for each rule in ``TABLE_CROSS_VALIDATION_RULES``,
   verify that every value in the source column appears in the target column.
"""

import logging
from typing import List

from config import TABLE_HEADING_NAMES, TABLE_CROSS_VALIDATION_RULES
from models import Status, ValidationResult
from table_extractor import TablesIndex

CATEGORY = "Tables"


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def validate_tables(
    tables_index: TablesIndex,
    logger: logging.Logger,
) -> List[ValidationResult]:
    """
    Validate extracted table data.

    Parameters
    ----------
    tables_index : dict
        Output from :func:`table_extractor.get_tables_by_heading`.
    logger : logging.Logger
        Session logger.

    Returns
    -------
    list of ValidationResult
    """
    logger.info("--- Table validation started ---")
    results: List[ValidationResult] = []

    # ------------------------------------------------------------------
    # Check 1: Each expected heading has a table with data rows
    # ------------------------------------------------------------------
    for heading in TABLE_HEADING_NAMES:
        table_data = tables_index.get(heading, [])

        if not table_data:
            results.append(ValidationResult(
                category=CATEGORY,
                check=f"table_found_{_slug(heading)}",
                label=f'Table under "{heading}"',
                status=Status.FAIL,
                message=(
                    f'No table found under the heading "{heading}". '
                    "Ensure the heading name exactly matches (case-insensitive) "
                    "one of TABLE_HEADING_NAMES in config.py."
                ),
            ))
            logger.warning("No table data for heading: %r", heading)
        else:
            results.append(ValidationResult(
                category=CATEGORY,
                check=f"table_found_{_slug(heading)}",
                label=f'Table under "{heading}"',
                status=Status.PASS,
                message=f'Found {len(table_data)} data row(s) under "{heading}".',
                details={"rows": table_data},
            ))
            logger.info(
                "Table under '%s': %d row(s)", heading, len(table_data)
            )

        logger.info(
            "[%s] table_found_%s – %s",
            CATEGORY, _slug(heading), results[-1].status.value
        )

    # ------------------------------------------------------------------
    # Check 2: Cross-validation between two tables
    # ------------------------------------------------------------------
    if not TABLE_CROSS_VALIDATION_RULES:
        results.append(ValidationResult(
            category=CATEGORY,
            check="cross_validation",
            label="Cross-Table Validation",
            status=Status.SKIP,
            message=(
                "No cross-validation rules configured. "
                "Add rules to TABLE_CROSS_VALIDATION_RULES in config.py."
            ),
        ))
    else:
        for rule in TABLE_CROSS_VALIDATION_RULES:
            results.extend(_apply_cross_rule(rule, tables_index, logger))

    logger.info("--- Table validation complete ---")
    return results


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _apply_cross_rule(
    rule: tuple,
    tables_index: TablesIndex,
    logger: logging.Logger,
) -> List[ValidationResult]:
    """
    Apply one cross-validation rule and return a list of ValidationResult.

    A rule is a 4-tuple:
        (source_heading, source_column, target_heading, target_column)

    All values in ``source_column`` of the source table must appear in
    ``target_column`` of the target table.
    """
    src_heading, src_col, tgt_heading, tgt_col = rule
    check_key = f"xval_{_slug(src_heading)}_{_slug(src_col)}_in_{_slug(tgt_heading)}"
    label = (
        f'"{src_heading} › {src_col}" values in '
        f'"{tgt_heading} › {tgt_col}"'
    )

    src_data = tables_index.get(src_heading, [])
    tgt_data = tables_index.get(tgt_heading, [])

    if not src_data:
        return [ValidationResult(
            category=CATEGORY,
            check=check_key,
            label=label,
            status=Status.SKIP,
            message=f'Source table "{src_heading}" has no data – cross-validation skipped.',
        )]

    if not tgt_data:
        return [ValidationResult(
            category=CATEGORY,
            check=check_key,
            label=label,
            status=Status.SKIP,
            message=f'Target table "{tgt_heading}" has no data – cross-validation skipped.',
        )]

    # Extract values
    src_values = {
        row.get(src_col, "").strip()
        for row in src_data
        if row.get(src_col, "").strip()
    }
    tgt_values = {
        row.get(tgt_col, "").strip()
        for row in tgt_data
        if row.get(tgt_col, "").strip()
    }

    missing = src_values - tgt_values

    if missing:
        return [ValidationResult(
            category=CATEGORY,
            check=check_key,
            label=label,
            status=Status.FAIL,
            message=(
                f"Cross-validation failed: {len(missing)} value(s) from "
                f'"{src_heading} › {src_col}" not found in '
                f'"{tgt_heading} › {tgt_col}".'
            ),
            details={"missing_values": sorted(missing)},
        )]
    else:
        return [ValidationResult(
            category=CATEGORY,
            check=check_key,
            label=label,
            status=Status.PASS,
            message=(
                f"All {len(src_values)} value(s) from "
                f'"{src_heading} › {src_col}" are present in '
                f'"{tgt_heading} › {tgt_col}".'
            ),
        )]


def _slug(text: str) -> str:
    """Convert a heading name to a safe identifier fragment."""
    return "".join(c if c.isalnum() else "_" for c in text).lower()
