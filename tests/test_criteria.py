"""Tests for Formal Criteria (Phase 6) — Matsushima Admissible Band."""

import pytest

from propagation_sanity.core.grid import Grid
from propagation_sanity.core.wave import Wave
from propagation_sanity.core.field import SquareAperture
from propagation_sanity.core.report import AssessmentType, ResultStatus
from propagation_sanity.criteria.matsushima import (
    matsushima_admissible_limit,
    asm_admissible_band_check,
)


@pytest.fixture
def benchmark_grid():
    return Grid(nx=512, ny=512, dx=2e-6, dy=2e-6)


@pytest.fixture
def benchmark_wave():
    return Wave(wavelength=532e-9)


class TestMatsushimaLimit:
    def test_zero_distance_limit_is_cutoff(self):
        lam = 532e-9
        lim = matsushima_admissible_limit(domain_size=1e-3, z=0.0, wavelength=lam)
        assert lim == pytest.approx(1.0 / lam)

    def test_limit_decreases_with_distance(self):
        lam = 532e-9
        s = 1.024e-3
        lim_short = matsushima_admissible_limit(s, z=1e-3, wavelength=lam)
        lim_long = matsushima_admissible_limit(s, z=100e-3, wavelength=lam)
        assert lim_long < lim_short


class TestASMAdmissibleBandCheck:
    def test_assessment_type_and_provenance(self, benchmark_grid, benchmark_wave):
        res = asm_admissible_band_check(
            grid=benchmark_grid,
            wave=benchmark_wave,
            z=10e-3,
            padded=True,
            bandlimit_enabled=False,
        )
        assert res.assessment_type == AssessmentType.FORMAL_CRITERION
        assert res.threshold_provenance.value == "literature"

    def test_bandlimit_enabled_passes(self, benchmark_grid, benchmark_wave):
        res = asm_admissible_band_check(
            grid=benchmark_grid,
            wave=benchmark_wave,
            z=150e-3,
            padded=True,
            bandlimit_enabled=True,
        )
        assert res.status == ResultStatus.PASS
        assert "BLAS filter is active" in res.interpretation

    def test_long_distance_without_blas_fails_for_wide_field(
        self, benchmark_grid, benchmark_wave
    ):
        # A sharp square aperture has high frequency content
        source = SquareAperture(half_width=50e-6)
        field = source.sample(benchmark_grid)

        # At z = 150mm, the admissible limit is very small (~ 1.2e4 1/m)
        # while aperture spectrum extends well beyond this
        res = asm_admissible_band_check(
            grid=benchmark_grid,
            wave=benchmark_wave,
            z=150e-3,
            field=field,
            padded=False,
            bandlimit_enabled=False,
        )
        assert res.status == ResultStatus.FAIL
        assert "Matsushima criterion VIOLATED" in res.interpretation
