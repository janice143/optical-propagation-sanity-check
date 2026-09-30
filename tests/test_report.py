"""Tests for ValidationReport and ReportItem."""

import json

import pytest

from propagation_sanity.core.report import (
    AssessmentType,
    ThresholdProvenance,
    ResultStatus,
    ReportItem,
    ValidationReport,
)


class TestReportItem:
    def test_creation(self):
        item = ReportItem(
            id="grid.Lx",
            title="Physical extent X",
            category="grid",
            assessment_type=AssessmentType.DERIVED,
            value=1.024e-3,
            status=ResultStatus.INFO,
            unit="m",
            formula="L_x = N_x * dx",
        )
        assert item.id == "grid.Lx"
        assert item.assessment_type == AssessmentType.DERIVED

    def test_to_dict(self):
        item = ReportItem(
            id="spectrum.edge_energy",
            title="Spectral edge energy",
            category="diagnostics",
            assessment_type=AssessmentType.DIAGNOSTIC,
            value=0.0042,
            status=ResultStatus.INFO,
            threshold=None,
            threshold_provenance=ThresholdProvenance.NONE,
            source="project",
        )
        d = item.to_dict()
        assert d["id"] == "spectrum.edge_energy"
        assert d["assessment_type"] == "diagnostic"
        assert d["value"] == 0.0042
        assert d["status"] == "info"

    def test_formal_criterion_item(self):
        item = ReportItem(
            id="asm.admissible_band",
            title="ASM admissible band",
            category="criteria",
            assessment_type=AssessmentType.FORMAL_CRITERION,
            value=True,
            status=ResultStatus.PASS,
            threshold="Matsushima Eq. (8)",
            threshold_provenance=ThresholdProvenance.LITERATURE,
            source="Matsushima & Shimobaba, Opt. Express 17, 2009",
        )
        d = item.to_dict()
        assert d["status"] == "pass"
        assert d["threshold_provenance"] == "literature"


class TestValidationReport:
    def test_empty_report(self):
        report = ValidationReport(metadata={"nx": 512})
        assert len(report.items) == 0
        d = report.to_dict()
        assert "metadata" in d
        assert "results" in d

    def test_add_items(self):
        report = ValidationReport()
        report.add_item(ReportItem(
            id="grid.dfx",
            title="Δfx",
            category="grid",
            assessment_type=AssessmentType.DERIVED,
            value=976.5625,
            status=ResultStatus.INFO,
        ))
        assert len(report.items) == 1

    def test_json_roundtrip(self):
        report = ValidationReport(metadata={"wavelength": 532e-9})
        report.add_item(ReportItem(
            id="test",
            title="Test item",
            category="test",
            assessment_type=AssessmentType.DIAGNOSTIC,
            value=42.0,
            status=ResultStatus.INFO,
        ))
        j = report.to_json()
        parsed = json.loads(j)
        assert parsed["results"][0]["value"] == 42.0

    def test_summary_no_convergence(self):
        report = ValidationReport()
        text = report.summary()
        assert "unverified" in text.lower()

    def test_summary_with_convergence(self):
        report = ValidationReport()
        report.add_item(ReportItem(
            id="convergence.resolution",
            title="Input resolution",
            category="convergence",
            assessment_type=AssessmentType.CONVERGENCE,
            value={"final_error": 0.001},
            status=ResultStatus.CONVERGED_AT_TOLERANCE,
        ))
        report.add_item(ReportItem(
            id="convergence.domain",
            title="Domain",
            category="convergence",
            assessment_type=AssessmentType.CONVERGENCE,
            value={"final_error": 0.002},
            status=ResultStatus.CONVERGED_AT_TOLERANCE,
        ))
        text = report.summary()
        assert "supported" in text.lower() or "stability" in text.lower()

    def test_filter_by_type(self):
        report = ValidationReport()
        report.add_item(ReportItem(
            id="a", title="A", category="c",
            assessment_type=AssessmentType.DIAGNOSTIC,
            value=1, status=ResultStatus.INFO,
        ))
        report.add_item(ReportItem(
            id="b", title="B", category="c",
            assessment_type=AssessmentType.CONVERGENCE,
            value=2, status=ResultStatus.UNVERIFIED,
        ))
        diag = report.get_items_by_type(AssessmentType.DIAGNOSTIC)
        assert len(diag) == 1
        assert diag[0].id == "a"
