"""Integration test: full validate() pipeline.

Uses the benchmark square aperture to run the complete
static validation (without convergence) and verify the
report structure.
"""

import json
import numpy as np
import pytest

from propagation_sanity.core.grid import Grid
from propagation_sanity.core.wave import Wave
from propagation_sanity.core.field import SquareAperture
from propagation_sanity.core.propagation_config import (
    PropagationConfig,
    PropagationMethod,
)
from propagation_sanity.core.simulation import SimulationContract
from propagation_sanity.core.report import AssessmentType, ResultStatus
from propagation_sanity.validate import validate


@pytest.fixture
def benchmark_contract():
    """Standard benchmark square aperture parameters."""
    grid = Grid(nx=512, ny=512, dx=2e-6, dy=2e-6)
    wave = Wave(wavelength=532e-9)
    source = SquareAperture(half_width=50e-6)
    config = PropagationConfig(
        method=PropagationMethod.ASM,
        backend="waveprop",
        padding=2.0,
        bandlimit=False,
    )
    return SimulationContract(
        grid=grid,
        wave=wave,
        z=100e-3,
        propagation_config=config,
        source=source,
        characteristic_size=100e-6,
    )


class TestValidateStatic:
    """Test static validation (no convergence)."""

    def test_returns_report(self, benchmark_contract):
        report = validate(benchmark_contract)
        assert report is not None
        assert len(report.items) > 0

    def test_has_derived_quantities(self, benchmark_contract):
        report = validate(benchmark_contract)
        derived = report.get_items_by_type(AssessmentType.DERIVED)
        assert len(derived) > 0
        ids = {it.id for it in derived}
        assert "grid.nx" in ids
        assert "grid.Lx" in ids
        assert "grid.dfx" in ids

    def test_has_diagnostics(self, benchmark_contract):
        report = validate(benchmark_contract)
        diag = report.get_items_by_type(AssessmentType.DIAGNOSTIC)
        ids = {it.id for it in diag}
        assert "spectrum.edge_energy" in ids
        assert "spectrum.effective_bandwidth" in ids
        assert "spatial.boundary_energy" in ids
        # ASM-specific
        assert "asm.phase_step" in ids

    def test_has_fresnel_number(self, benchmark_contract):
        report = validate(benchmark_contract)
        diag = report.get_items_by_type(AssessmentType.DIAGNOSTIC)
        ids = {it.id for it in diag}
        assert "model.fresnel_number" in ids

    def test_has_feature_pixels(self, benchmark_contract):
        report = validate(benchmark_contract)
        diag = report.get_items_by_type(AssessmentType.DIAGNOSTIC)
        ids = {it.id for it in diag}
        assert "input.feature_pixels" in ids

    def test_convergence_unverified_without_flag(self, benchmark_contract):
        report = validate(benchmark_contract, run_convergence=False)
        conv = report.get_items_by_type(AssessmentType.CONVERGENCE)
        assert any(it.status == ResultStatus.UNVERIFIED for it in conv)

    def test_json_serializable(self, benchmark_contract):
        report = validate(benchmark_contract)
        j = report.to_json()
        parsed = json.loads(j)
        assert "metadata" in parsed
        assert "results" in parsed
        assert len(parsed["results"]) > 0

    def test_text_summary(self, benchmark_contract):
        report = validate(benchmark_contract)
        text = report.summary()
        assert "NUMERICAL PROPAGATION VALIDATION" in text
        assert "Simulation" in text

    def test_metadata_has_benchmark_values(self, benchmark_contract):
        report = validate(benchmark_contract)
        meta = report.metadata
        assert meta["nx"] == 512
        assert meta["wavelength"] == pytest.approx(532e-9)


class TestValidateMultiZ:
    """Test with multiple propagation distances."""

    def test_multi_z_produces_per_z_items(self):
        grid = Grid(nx=128, ny=128, dx=2e-6, dy=2e-6)
        wave = Wave(wavelength=532e-9)
        source = SquareAperture(half_width=30e-6)
        config = PropagationConfig(
            method=PropagationMethod.ASM,
            backend="waveprop",
        )
        contract = SimulationContract(
            grid=grid,
            wave=wave,
            z=[1e-3, 10e-3],
            propagation_config=config,
            source=source,
        )
        report = validate(contract)
        # Should have separate items for each z
        ids = {it.id for it in report.items}
        # Two z values → phase step for each
        asm_items = [it for it in report.items if "asm.phase_step" in it.id]
        assert len(asm_items) == 2
