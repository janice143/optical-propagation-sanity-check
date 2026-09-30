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

    def test_item_from_dict(self):
        item = ReportItem(
            id="test.item",
            title="Test Item",
            category="criteria",
            assessment_type=AssessmentType.FORMAL_CRITERION,
            value={"score": 10},
            status=ResultStatus.PASS,
            threshold=5,
            threshold_provenance=ThresholdProvenance.LITERATURE,
            source="Test Lit",
            interpretation="Test interpretation",
            recommended_action="None needed",
        )
        d = item.to_dict()
        reconstructed = ReportItem.from_dict(d)
        assert reconstructed.id == item.id
        assert reconstructed.title == item.title
        assert reconstructed.assessment_type == AssessmentType.FORMAL_CRITERION
        assert reconstructed.status == ResultStatus.PASS
        assert reconstructed.threshold_provenance == ThresholdProvenance.LITERATURE
        assert reconstructed.value == {"score": 10}
        assert reconstructed.source == "Test Lit"

    def test_save_and_load_json(self, tmp_path):
        report = ValidationReport(metadata={"nx": 256, "method": "asm"})
        report.add_item(ReportItem(
            id="diag.1",
            title="Diagnostic 1",
            category="diagnostics",
            assessment_type=AssessmentType.DIAGNOSTIC,
            value=0.123,
            status=ResultStatus.INFO,
        ))
        report.add_item(ReportItem(
            id="conv.1",
            title="Convergence 1",
            category="convergence",
            assessment_type=AssessmentType.CONVERGENCE,
            value={"final_error": 0.005},
            status=ResultStatus.CONVERGED_AT_TOLERANCE,
        ))

        json_file = tmp_path / "test_report.json"
        report.save(json_file)
        assert json_file.exists()

        # Load back
        loaded = ValidationReport.load(json_file)
        assert loaded.metadata == {"nx": 256, "method": "asm"}
        assert len(loaded.items) == 2
        assert loaded.items[0].id == "diag.1"
        assert loaded.items[0].value == 0.123
        assert loaded.items[1].status == ResultStatus.CONVERGED_AT_TOLERANCE

    def test_from_json_string(self):
        report = ValidationReport(metadata={"nx": 128})
        report.add_item(ReportItem(
            id="item.1",
            title="Item 1",
            category="grid",
            assessment_type=AssessmentType.DERIVED,
            value=128,
            status=ResultStatus.INFO,
        ))
        j_str = report.to_json()
        loaded = ValidationReport.from_json(j_str)
        assert loaded.metadata["nx"] == 128
        assert loaded.items[0].value == 128

    def test_to_html_and_save_html(self, tmp_path):
        report = ValidationReport(metadata={"nx": 512, "method": "asm", "wavelength": 532e-9})
        report.add_item(ReportItem(
            id="matsushima",
            title="Matsushima Criterion",
            category="criteria",
            assessment_type=AssessmentType.FORMAL_CRITERION,
            value=True,
            status=ResultStatus.PASS,
        ))

        html_str = report.to_html()
        assert "<!DOCTYPE html>" in html_str
        assert "Matsushima Criterion" in html_str
        assert "report-data" in html_str

        out_html = tmp_path / "report.html"
        report.save_html(out_html)
        assert out_html.exists()
        assert out_html.read_text(encoding="utf-8") == html_str

