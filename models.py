"""
models.py
---------
Shared data models (dataclasses) used across the entire validator stack.
Keeping models in one place prevents circular imports and makes it easy
to add fields without touching multiple modules.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Validation status enum
# ---------------------------------------------------------------------------

class Status(str, Enum):
    """Outcome of an individual validation check."""
    PASS  = "PASS"
    FAIL  = "FAIL"
    WARN  = "WARN"   # Non-blocking issue – check passed but something looks off
    SKIP  = "SKIP"   # Check was disabled in config or could not run


# ---------------------------------------------------------------------------
# A single validation result
# ---------------------------------------------------------------------------

@dataclass
class ValidationResult:
    """
    Represents the outcome of one validation check.

    Attributes
    ----------
    category : str
        High-level group name, e.g. "Header", "Footer", "Tables".
    check : str
        Short unique identifier for the check, e.g. "has_logo_image".
    label : str
        Human-readable description shown in the UI.
    status : Status
        PASS / FAIL / WARN / SKIP.
    message : str
        Detailed message explaining why the check passed or failed.
    details : dict, optional
        Any extra structured data the UI can render (e.g. table diff rows).
    """
    category : str
    check    : str
    label    : str
    status   : Status
    message  : str
    details  : Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Aggregated validation report
# ---------------------------------------------------------------------------

@dataclass
class ValidationReport:
    """
    Aggregates all ValidationResult objects produced during a validation run.

    Attributes
    ----------
    filename : str
        Name of the validated file.
    results : list of ValidationResult
        All individual check results in execution order.
    """
    filename : str
    results  : List[ValidationResult] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def add(self, result: ValidationResult) -> None:
        """Append a single result to the report."""
        self.results.append(result)

    def extend(self, results: List[ValidationResult]) -> None:
        """Append multiple results at once."""
        self.results.extend(results)

    @property
    def passed(self) -> List[ValidationResult]:
        """All results with PASS status."""
        return [r for r in self.results if r.status == Status.PASS]

    @property
    def failed(self) -> List[ValidationResult]:
        """All results with FAIL status."""
        return [r for r in self.results if r.status == Status.FAIL]

    @property
    def warnings(self) -> List[ValidationResult]:
        """All results with WARN status."""
        return [r for r in self.results if r.status == Status.WARN]

    @property
    def skipped(self) -> List[ValidationResult]:
        """All results with SKIP status."""
        return [r for r in self.results if r.status == Status.SKIP]

    @property
    def is_valid(self) -> bool:
        """True if there are zero FAIL results."""
        return len(self.failed) == 0

    def by_category(self) -> Dict[str, List[ValidationResult]]:
        """Return results grouped by category."""
        grouped: Dict[str, List[ValidationResult]] = {}
        for result in self.results:
            grouped.setdefault(result.category, []).append(result)
        return grouped

    def summary(self) -> str:
        """One-line summary string, e.g. '5 passed | 2 failed | 1 warning'."""
        parts = []
        if self.passed:
            parts.append(f"{len(self.passed)} passed")
        if self.failed:
            parts.append(f"{len(self.failed)} failed")
        if self.warnings:
            parts.append(f"{len(self.warnings)} warning(s)")
        if self.skipped:
            parts.append(f"{len(self.skipped)} skipped")
        return " | ".join(parts) if parts else "No checks run"


# ---------------------------------------------------------------------------
# Document properties
# ---------------------------------------------------------------------------

@dataclass
class DocumentProperties:
    """
    Container for metadata extracted from a Word document's core properties.

    All fields are Optional because not every template populates them.
    """
    title             : Optional[str] = None
    subject           : Optional[str] = None
    author            : Optional[str] = None
    last_modified_by  : Optional[str] = None
    created           : Optional[str] = None   # ISO 8601 string
    modified          : Optional[str] = None   # ISO 8601 string
    revision          : Optional[str] = None
    keywords          : Optional[str] = None
    description       : Optional[str] = None
    page_count        : Optional[int] = None
    word_count        : Optional[int] = None
    section_count     : Optional[int] = None

    def to_display_dict(self) -> Dict[str, str]:
        """
        Return a flat dict suitable for display in the UI (None → "—").
        """
        return {
            "Title"            : self.title           or "—",
            "Subject"          : self.subject         or "—",
            "Author"           : self.author          or "—",
            "Last Modified By" : self.last_modified_by or "—",
            "Created"          : self.created         or "—",
            "Modified"         : self.modified        or "—",
            "Revision"         : self.revision        or "—",
            "Keywords"         : self.keywords        or "—",
            "Description"      : self.description     or "—",
            "Est. Page Count"  : str(self.page_count)  if self.page_count  is not None else "—",
            "Word Count"       : str(self.word_count)  if self.word_count  is not None else "—",
            "Section Count"    : str(self.section_count) if self.section_count is not None else "—",
        }
