"""Validation report data structures.

Every checker result is a ``ReportItem`` with a clear assessment type
and traceable threshold provenance.  Items are collected into a
``ValidationReport`` that can be serialised to JSON or printed as a
human-readable summary.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class AssessmentType(Enum):
    """Category of a validation result."""
    DERIVED = "derived"
    DIAGNOSTIC = "diagnostic"
    FORMAL_CRITERION = "formal_criterion"
    CONVERGENCE = "convergence"
    CROSS_REFERENCE = "cross_reference"
    SCOPE_CHECK = "scope_check"


class ThresholdProvenance(Enum):
    """Where a threshold value comes from."""
    THEORETICAL = "theoretical"
    LITERATURE = "literature"
    PROJECT_DEFAULT = "project_default"
    USER_DEFINED = "user_defined"
    NONE = "none"  # no threshold (e.g. diagnostics)


class ResultStatus(Enum):
    """Status outcome for a single check."""
    # Generic
    INFO = "info"
    # Formal criterion
    PASS = "pass"
    FAIL = "fail"
    # Convergence
    CONVERGED_AT_TOLERANCE = "converged_at_tolerance"
    NOT_CONVERGED = "not_converged"
    # Cross-reference
    AGREES_AT_TOLERANCE = "agrees_at_tolerance"
    DISAGREES = "disagrees"
    # Indeterminate
    UNVERIFIED = "unverified"
    NOT_APPLICABLE = "not_applicable"
    OUT_OF_SCOPE = "out_of_scope"


class ValidationState(Enum):
    """Top-level validation summary state."""
    SUPPORTED_AT_TOLERANCE = "supported_at_tolerance"
    NOT_CONVERGED = "not_converged"
    UNVERIFIED = "unverified"
    OUT_OF_SCOPE = "out_of_scope"


# ---------------------------------------------------------------------------
# Report item
# ---------------------------------------------------------------------------

@dataclass
class ReportItem:
    """Single validation result with traceable metadata and evaluation status."""

    id: str
    title: str
    category: str
    assessment_type: AssessmentType
    value: Any
    status: ResultStatus

    # Optional extended metadata
    applicable_methods: Optional[List[str]] = None
    unit: Optional[str] = None
    formula: Optional[str] = None
    assumptions: Optional[str] = None
    threshold: Optional[Any] = None
    threshold_provenance: ThresholdProvenance = ThresholdProvenance.NONE
    source: Optional[str] = None
    interpretation: Optional[str] = None
    recommended_action: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "assessment_type": self.assessment_type.value,
            "value": _serialise(self.value),
            "status": self.status.value,
        }
        for key in (
            "applicable_methods", "unit", "formula", "assumptions",
            "threshold", "threshold_provenance", "source",
            "interpretation", "recommended_action",
        ):
            val = getattr(self, key)
            if val is not None:
                if isinstance(val, Enum):
                    d[key] = val.value
                else:
                    d[key] = _serialise(val)
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> ReportItem:
        """Construct a ReportItem from a dictionary representation."""
        data = dict(d)
        raw_atype = data.pop("assessment_type")
        atype = AssessmentType(raw_atype) if isinstance(raw_atype, str) else raw_atype

        raw_status = data.pop("status")
        status = ResultStatus(raw_status) if isinstance(raw_status, str) else raw_status

        raw_prov = data.pop("threshold_provenance", None)
        if raw_prov is not None:
            prov = ThresholdProvenance(raw_prov) if isinstance(raw_prov, str) else raw_prov
        else:
            prov = ThresholdProvenance.NONE

        return cls(
            id=data.pop("id"),
            title=data.pop("title"),
            category=data.pop("category"),
            assessment_type=atype,
            value=data.pop("value"),
            status=status,
            threshold_provenance=prov,
            applicable_methods=data.pop("applicable_methods", None),
            unit=data.pop("unit", None),
            formula=data.pop("formula", None),
            assumptions=data.pop("assumptions", None),
            threshold=data.pop("threshold", None),
            source=data.pop("source", None),
            interpretation=data.pop("interpretation", None),
            recommended_action=data.pop("recommended_action", None),
        )


# ---------------------------------------------------------------------------
# Validation report
# ---------------------------------------------------------------------------

@dataclass
class ValidationReport:
    """Collection of validation results for a simulation.

    Parameters
    ----------
    metadata : dict
        Simulation contract derived report (reproducibility info).
    """

    metadata: Dict[str, Any] = field(default_factory=dict)
    items: List[ReportItem] = field(default_factory=list)

    def add_item(self, item: ReportItem) -> None:
        """Append a result item to the report."""
        self.items.append(item)

    def get_items_by_category(self, category: str) -> List[ReportItem]:
        return [it for it in self.items if it.category == category]

    def get_items_by_type(self, atype: AssessmentType) -> List[ReportItem]:
        return [it for it in self.items if it.assessment_type == atype]

    # ---- serialisation ---------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metadata": self.metadata,
            "results": [item.to_dict() for item in self.items],
            "summary": self._summary_dict(),
        }

    def to_json(self, indent: int = 2, **kwargs) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str, **kwargs)

    def save(self, filepath: Union[str, Path], indent: int = 2) -> None:
        """Save the validation report to a JSON file.

        Parameters
        ----------
        filepath : str or Path
            Target JSON file path.
        indent : int, default=2
            Indentation level for pretty JSON output.
        """
        p = Path(filepath)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(self.to_json(indent=indent))

    def save_json(self, filepath: Union[str, Path], indent: int = 2) -> None:
        """Alias for save()."""
        self.save(filepath, indent=indent)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ValidationReport:
        """Construct a ValidationReport instance from a dictionary."""
        metadata = data.get("metadata", {})
        results_data = data.get("results", [])
        items = [ReportItem.from_dict(it) for it in results_data]
        return cls(metadata=metadata, items=items)

    @classmethod
    def from_json(cls, json_str_or_path: Union[str, Path]) -> ValidationReport:
        """Load a ValidationReport from a JSON string or file path.

        Parameters
        ----------
        json_str_or_path : str or Path
            Either a file path ending with .json / pointing to an existing file,
            or a raw JSON string.
        """
        if isinstance(json_str_or_path, Path):
            with open(json_str_or_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        elif isinstance(json_str_or_path, str):
            stripped = json_str_or_path.strip()
            if stripped.startswith("{") or stripped.startswith("["):
                data = json.loads(json_str_or_path)
            else:
                p = Path(json_str_or_path)
                if p.is_file():
                    with open(p, "r", encoding="utf-8") as f:
                        data = json.load(f)
                else:
                    data = json.loads(json_str_or_path)
        else:
            raise TypeError(f"Expected str or Path, got {type(json_str_or_path)}")
        return cls.from_dict(data)

    @classmethod
    def load(cls, filepath: Union[str, Path]) -> ValidationReport:
        """Load a ValidationReport from a JSON file path."""
        return cls.from_json(filepath)

    def to_html(
        self,
        output_path: Optional[Union[str, Path]] = None,
        title: str = "Optical Propagation Validation Report",
    ) -> str:
        """Render the report to an interactive standalone HTML document.

        Parameters
        ----------
        output_path : str or Path, optional
            Path where the HTML file will be written.
        title : str
            Document title.

        Returns
        -------
        str
            The complete HTML document string.
        """
        from propagation_sanity.viewer.html_viewer import render_html
        return render_html(self, output_path=output_path, title=title)

    def save_html(
        self,
        filepath: Union[str, Path],
        title: str = "Optical Propagation Validation Report",
    ) -> str:
        """Save the report as an interactive HTML document to the specified path."""
        return self.to_html(output_path=filepath, title=title)

    def view(
        self,
        format: str = "html",
        open_browser: bool = False,
        output_path: Optional[Union[str, Path]] = None,
        color: Optional[bool] = None,
    ) -> Any:
        """Visualize the report in either HTML or terminal format.

        Parameters
        ----------
        format : {"html", "terminal"}
            Visualizer mode.
        open_browser : bool
            Whether to open the HTML viewer in the default browser.
        output_path : str or Path, optional
            Path to write HTML output to.
        color : bool, optional
            Whether to enable ANSI color codes in terminal mode.
        """
        from propagation_sanity.viewer import view
        return view(
            self,
            format=format,
            open_browser=open_browser,
            output_path=output_path,
            color=color,
        )

    # ---- human-readable summary -----------------------------------------

    def summary(self) -> str:
        """Formatted human-readable text summary of the validation report."""
        lines: List[str] = []
        lines.append("NUMERICAL PROPAGATION VALIDATION")
        lines.append("")

        # Simulation section
        lines.append("Simulation")
        lines.append("-" * 40)
        for key in ("nx", "ny", "dx", "dy", "Lx", "Ly",
                     "wavelength", "z", "method"):
            if key in self.metadata:
                val = self.metadata[key]
                lines.append(f"  {key:20s}  {_format_value(key, val)}")
        lines.append("")

        # Derived
        derived = self.get_items_by_type(AssessmentType.DERIVED)
        if derived:
            lines.append("Derived")
            lines.append("-" * 40)
            for item in derived:
                lines.append(f"  {item.title:20s}  {_format_value(item.id, item.value)}")
            lines.append("")

        # Diagnostics
        diagnostics = self.get_items_by_type(AssessmentType.DIAGNOSTIC)
        if diagnostics:
            lines.append("Diagnostics")
            lines.append("-" * 40)
            for item in diagnostics:
                status_str = f"  [{item.status.value.upper()}]" if item.status != ResultStatus.INFO else ""
                lines.append(
                    f"  {item.title:20s}  {_format_value(item.id, item.value)}{status_str}"
                )
            lines.append("")

        # Formal criteria
        criteria = self.get_items_by_type(AssessmentType.FORMAL_CRITERION)
        if criteria:
            lines.append("Formal Criteria")
            lines.append("-" * 40)
            for item in criteria:
                lines.append(
                    f"  {item.title:20s}  {item.status.value.upper()}"
                )
            lines.append("")

        # Convergence
        convergence = self.get_items_by_type(AssessmentType.CONVERGENCE)
        if convergence:
            lines.append("Convergence")
            lines.append("-" * 40)
            for item in convergence:
                lines.append(
                    f"  {item.title:20s}  {item.status.value.upper()}"
                )
            lines.append("")

        # Cross-reference
        xref = self.get_items_by_type(AssessmentType.CROSS_REFERENCE)
        if xref:
            lines.append("Reference")
            lines.append("-" * 40)
            for item in xref:
                lines.append(
                    f"  {item.title:20s}  {item.status.value.upper()}"
                )
            lines.append("")

        # Summary statement
        lines.append("Summary")
        lines.append("-" * 40)
        lines.append(f"  {self._summary_statement()}")

        return "\n".join(lines)

    # ---- internal --------------------------------------------------------

    def _summary_dict(self) -> Dict[str, str]:
        """Per-dimension summary states."""
        dimensions = {}
        for item in self.items:
            if item.assessment_type == AssessmentType.CONVERGENCE:
                dimensions[item.id] = item.status.value
        return dimensions

    def _summary_statement(self) -> str:
        """Single-sentence summary."""
        convergence_items = self.get_items_by_type(AssessmentType.CONVERGENCE)
        if not convergence_items:
            return (
                "No convergence experiments have been run. "
                "Numerical reliability is unverified."
            )
        all_converged = all(
            it.status == ResultStatus.CONVERGED_AT_TOLERANCE
            for it in convergence_items
        )
        any_failed = any(
            it.status == ResultStatus.NOT_CONVERGED
            for it in convergence_items
        )
        unverified = [
            it for it in convergence_items
            if it.status == ResultStatus.UNVERIFIED
        ]
        if all_converged:
            return (
                "Numerical stability is supported for the tested "
                "resolution, physical domain, and propagation "
                "configuration at the requested tolerance."
            )
        if any_failed:
            return (
                "At least one convergence test did not pass. "
                "Numerical reliability has not been demonstrated."
            )
        if unverified:
            names = ", ".join(it.title for it in unverified)
            return (
                f"Validation incomplete: {names} "
                "convergence was not available."
            )
        return "Numerical reliability status is mixed. Review individual results."


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _serialise(val: Any) -> Any:
    """Make a value JSON-serialisable."""
    import numpy as np
    if isinstance(val, np.ndarray):
        return val.tolist()
    if isinstance(val, np.generic):
        return val.item()
    if isinstance(val, Enum):
        return val.value
    return val


def _format_value(key: str, val: Any) -> str:
    """Pretty-format a value for terminal display."""
    if isinstance(val, float):
        if abs(val) < 1e-3 or abs(val) > 1e4:
            return f"{val:.4e}"
        return f"{val:.6f}"
    if isinstance(val, list):
        return ", ".join(str(v) for v in val)
    return str(val)
