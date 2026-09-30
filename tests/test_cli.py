"""Tests for the command-line interface."""

import pytest
from propagation_sanity.cli import main


class TestCLI:
    def test_help(self, capsys):
        with pytest.raises(SystemExit) as excinfo:
            main(["--help"])
        assert excinfo.value.code == 0
        captured = capsys.readouterr()
        assert "propagation-sanity" in captured.out

    def test_check_square_summary(self, capsys):
        code = main(["check", "--scenario", "square", "--z-mm", "10"])
        assert code == 0
        captured = capsys.readouterr()
        assert "NUMERICAL PROPAGATION VALIDATION" in captured.out
        assert "Spectral edge energy" in captured.out

    def test_check_json_output(self, capsys):
        code = main(["check", "--scenario", "square", "--z-mm", "10", "--json"])
        assert code == 0
        captured = capsys.readouterr()
        assert '"metadata"' in captured.out
        assert '"results"' in captured.out

    def test_benchmark_square(self, capsys):
        code = main(["benchmark", "--scenario", "square"])
        assert code == 0
        captured = capsys.readouterr()
        assert "Square Aperture Benchmark Suite" in captured.out

    def test_check_save_json(self, tmp_path, capsys):
        out_json = tmp_path / "report.json"
        code = main(["check", "--scenario", "square", "--z-mm", "10", "-o", str(out_json)])
        assert code == 0
        assert out_json.exists()
        captured = capsys.readouterr()
        assert "saved to" in captured.out

    def test_check_save_html(self, tmp_path, capsys):
        out_html = tmp_path / "report.html"
        code = main(["check", "--scenario", "square", "--z-mm", "10", "--html", str(out_html)])
        assert code == 0
        assert out_html.exists()
        captured = capsys.readouterr()
        assert "saved to" in captured.out

    def test_view_command_terminal(self, tmp_path, capsys):
        # First generate a json file
        json_file = tmp_path / "report.json"
        main(["check", "--scenario", "square", "--z-mm", "10", "-o", str(json_file)])

        # View in terminal
        code = main(["view", str(json_file)])
        assert code == 0
        captured = capsys.readouterr()
        assert "NUMERICAL SCALAR WAVE PROPAGATION" in captured.out

    def test_view_command_html_export(self, tmp_path, capsys):
        json_file = tmp_path / "report.json"
        main(["check", "--scenario", "square", "--z-mm", "10", "-o", str(json_file)])

        html_file = tmp_path / "rendered.html"
        code = main(["view", str(json_file), "--format", "html", "-o", str(html_file)])
        assert code == 0
        assert html_file.exists()
        captured = capsys.readouterr()
        assert "Rendered HTML saved to" in captured.out

    def test_benchmark_json_export(self, tmp_path, capsys):
        bench_json = tmp_path / "bench.json"
        code = main(["benchmark", "--scenario", "square", "-o", str(bench_json)])
        assert code == 0
        assert bench_json.exists()
        captured = capsys.readouterr()
        assert "saved to" in captured.out

