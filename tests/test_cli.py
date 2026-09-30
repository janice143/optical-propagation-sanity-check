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
