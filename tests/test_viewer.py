"""Tests for the report viewer (HTML and terminal visualizers)."""

import json
from pathlib import Path
import pytest

from propagation_sanity.core.report import (
    AssessmentType,
    ReportItem,
    ResultStatus,
    ValidationReport,
)
from propagation_sanity.viewer import render_html, render_terminal, view


@pytest.fixture
def sample_report():
    report = ValidationReport(
        metadata={
            "nx": 512,
            "ny": 512,
            "dx": 2e-6,
            "dy": 2e-6,
            "Lx": 1.024e-3,
            "Ly": 1.024e-3,
            "wavelength": 532e-9,
            "z": [0.1],
            "method": "asm",
            "backend": "waveprop",
            "bandlimit": False,
            "padding": 2.0,
        }
    )
    report.add_item(
        ReportItem(
            id="asm.admissible_band",
            title="ASM admissible band",
            category="criteria",
            assessment_type=AssessmentType.FORMAL_CRITERION,
            value={"fx_limit": 19247.0},
            status=ResultStatus.FAIL,
            interpretation="Matsushima criterion violated.",
            recommended_action="Enable bandlimit=True.",
        )
    )
    report.add_item(
        ReportItem(
            id="convergence.resolution",
            title="Input resolution",
            category="convergence",
            assessment_type=AssessmentType.CONVERGENCE,
            value={
                "tolerance": 0.01,
                "errors": [
                    {"factor_from": 1, "factor_to": 2, "intensity_relative_error": 0.05}
                ],
            },
            status=ResultStatus.NOT_CONVERGED,
        )
    )
    report.add_item(
        ReportItem(
            id="spectrum.edge_energy",
            title="Spectral edge energy",
            category="diagnostics",
            assessment_type=AssessmentType.DIAGNOSTIC,
            value=0.0042,
            unit="fraction",
            status=ResultStatus.INFO,
        )
    )
    return report


class TestTerminalViewer:
    def test_render_terminal_from_object(self, sample_report):
        text = render_terminal(sample_report, color=False)
        assert "NUMERICAL SCALAR WAVE PROPAGATION" in text
        assert "SIMULATION CONTRACT" in text
        assert "FORMAL CRITERIA" in text
        assert "CONVERGENCE EXPERIMENTS" in text
        assert "FAIL" in text
        assert "532.0 nm" in text

    def test_render_terminal_from_dict(self, sample_report):
        d = sample_report.to_dict()
        text = render_terminal(d, color=False)
        assert "Spectral edge energy" in text
        assert "Input resolution" in text

    def test_render_terminal_from_file(self, sample_report, tmp_path):
        json_file = tmp_path / "report.json"
        sample_report.save(json_file)
        text = render_terminal(json_file, color=False)
        assert "ASM admissible band" in text


class TestHtmlViewer:
    def test_render_html_content(self, sample_report):
        html = render_html(sample_report)
        assert "<!DOCTYPE html>" in html
        assert "report-data" in html
        assert "ASM admissible band" in html
        assert "5.32e-07" in html
        assert "tailwindcss.min.js" in html

    def test_render_html_to_file(self, sample_report, tmp_path):
        out_html = tmp_path / "dashboard.html"
        render_html(sample_report, output_path=out_html)
        assert out_html.exists()
        content = out_html.read_text(encoding="utf-8")
        assert "dashboard" in str(out_html) or "<!DOCTYPE html>" in content


class TestViewFunction:
    def test_view_terminal_mode(self, sample_report, capsys):
        out = view(sample_report, format="terminal", color=False)
        captured = capsys.readouterr()
        assert "VALIDATION REPORT" in captured.out
        assert "VALIDATION REPORT" in out

    def test_view_html_mode(self, sample_report, tmp_path):
        out_html = tmp_path / "view.html"
        out = view(sample_report, format="html", output_path=out_html, open_browser=False)
        assert out_html.exists()
        assert "<!DOCTYPE html>" in out

    def test_view_invalid_format(self, sample_report):
        with pytest.raises(ValueError, match="Unknown format"):
            view(sample_report, format="invalid_format")
