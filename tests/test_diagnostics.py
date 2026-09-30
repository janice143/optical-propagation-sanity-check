"""Tests for diagnostic checkers."""

import numpy as np
import pytest

from propagation_sanity.core.grid import Grid
from propagation_sanity.core.field import SampledField, SquareAperture, GaussianBeam
from propagation_sanity.core.wave import Wave
from propagation_sanity.core.report import AssessmentType, ResultStatus
from propagation_sanity.diagnostics import (
    spectral_edge_energy,
    effective_bandwidth,
    evanescent_diagnostic,
    boundary_energy,
    paraxial_fov_preview,
    asm_phase_step,
    fresnel_phase_remainder,
    fresnel_number,
)


@pytest.fixture
def benchmark_grid():
    """Standard benchmark: N=512, dx=2μm."""
    return Grid(nx=512, ny=512, dx=2e-6, dy=2e-6)


@pytest.fixture
def benchmark_wave():
    return Wave(wavelength=532e-9)


@pytest.fixture
def aperture_field(benchmark_grid):
    source = SquareAperture(half_width=50e-6)
    return source.sample(benchmark_grid)


class TestSpectralEdgeEnergy:
    def test_returns_diagnostic(self, aperture_field):
        item = spectral_edge_energy(aperture_field)
        assert item.assessment_type == AssessmentType.DIAGNOSTIC
        assert item.status == ResultStatus.INFO

    def test_low_edge_for_well_sampled(self, aperture_field):
        item = spectral_edge_energy(aperture_field, alpha=0.8)
        assert item.value < 0.1  # Should be relatively low

    def test_near_nyquist_sinusoid_high_edge(self):
        """A near-Nyquist sinusoid should have high edge energy."""
        grid = Grid(nx=128, ny=128, dx=1e-6, dy=1e-6)
        x = grid.x_coords()
        # Sinusoid at 0.9 * Nyquist
        freq = 0.9 * grid.nyquist_x
        pattern = np.cos(2 * np.pi * freq * x)
        data = np.tile(pattern, (128, 1)).astype(np.complex128)
        field = SampledField(data=data, grid=grid)

        item = spectral_edge_energy(field, alpha=0.8)
        assert item.value > 0.5  # Most energy should be in edge band

    def test_zero_field(self):
        grid = Grid(nx=64, ny=64, dx=1e-6, dy=1e-6)
        data = np.zeros((64, 64), dtype=np.complex128)
        field = SampledField(data=data, grid=grid)
        item = spectral_edge_energy(field)
        assert item.value == 0.0


class TestEffectiveBandwidth:
    def test_returns_radial_and_axis_quantiles(self, aperture_field):
        item = effective_bandwidth(aperture_field)
        val = item.value
        assert "radial" in val
        assert "x" in val
        assert "y" in val
        assert "95.0%" in val["radial"]


class TestEvanescentDiagnostic:
    def test_no_evanescent_for_large_aperture(self, aperture_field, benchmark_wave):
        """A well-sampled aperture should have negligible evanescent content."""
        item = evanescent_diagnostic(aperture_field, benchmark_wave)
        assert item.value < 0.01

    def test_scope_check_type(self, aperture_field, benchmark_wave):
        item = evanescent_diagnostic(aperture_field, benchmark_wave)
        assert item.assessment_type == AssessmentType.SCOPE_CHECK


class TestBoundaryEnergy:
    def test_small_aperture_low_boundary(self):
        """Small aperture in large domain → low boundary energy."""
        grid = Grid(nx=256, ny=256, dx=1e-6, dy=1e-6)
        source = SquareAperture(half_width=20e-6)
        field = source.sample(grid)
        item = boundary_energy(field)
        assert item.value < 0.01

    def test_large_aperture_high_boundary(self):
        """Aperture filling most of domain → high boundary energy."""
        grid = Grid(nx=128, ny=128, dx=1e-6, dy=1e-6)
        source = SquareAperture(half_width=60e-6)
        field = source.sample(grid)
        item = boundary_energy(field, edge_fraction=0.05)
        assert item.value > 0.01


class TestParaxialFOV:
    def test_short_distance(self, benchmark_grid, benchmark_wave):
        item = paraxial_fov_preview(benchmark_grid, benchmark_wave, z=1e-3)
        assert item.value["ratio_x"] > 1.0  # Should be safe

    def test_long_distance(self, benchmark_grid, benchmark_wave):
        item = paraxial_fov_preview(benchmark_grid, benchmark_wave, z=0.5)
        assert item.value["ratio_x"] < 10  # More constrained


class TestASMPhaseStep:
    def test_short_distance_small_step(self, benchmark_grid, benchmark_wave):
        item = asm_phase_step(benchmark_grid, benchmark_wave, z=1e-3)
        assert item.value["max_phase_step_pi"] < 10  # Reasonable

    def test_long_distance_large_step(self, benchmark_grid, benchmark_wave):
        item = asm_phase_step(benchmark_grid, benchmark_wave, z=150e-3)
        assert item.value["max_phase_step_pi"] > 1  # Should be large

    def test_asm_only(self, benchmark_grid, benchmark_wave):
        item = asm_phase_step(benchmark_grid, benchmark_wave, z=1e-3)
        assert "asm" in item.applicable_methods


class TestFresnelPhaseRemainder:
    def test_returns_diagnostic(self, benchmark_grid, benchmark_wave):
        item = fresnel_phase_remainder(benchmark_grid, benchmark_wave, z=10e-3)
        assert item.assessment_type == AssessmentType.DIAGNOSTIC

    def test_remainder_is_finite(self, benchmark_grid, benchmark_wave):
        """Fresnel phase remainder should be a finite positive value."""
        item = fresnel_phase_remainder(benchmark_grid, benchmark_wave, z=100e-3)
        # The max phase error can be large across the full Nyquist bandwidth
        # because Fresnel approximation breaks down at high spatial frequencies.
        # This is expected and is exactly why this diagnostic exists.
        assert item.value["max_phase_error_rad"] > 0
        assert np.isfinite(item.value["max_phase_error_rad"])


class TestFresnelNumber:
    def test_known_value(self, benchmark_wave):
        """N_F = a² / (λz), a=50μm, λ=532nm, z=100mm."""
        item = fresnel_number(benchmark_wave, z=100e-3, characteristic_size=50e-6)
        expected = (50e-6)**2 / (532e-9 * 100e-3)
        assert item.value == pytest.approx(expected, rel=1e-6)

    def test_not_applicable_without_size(self, benchmark_wave):
        item = fresnel_number(benchmark_wave, z=100e-3)
        assert item.status == ResultStatus.NOT_APPLICABLE
