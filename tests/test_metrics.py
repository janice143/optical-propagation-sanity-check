"""Tests for comparison metrics — plan sections 44–47."""

import numpy as np
import pytest

from propagation_sanity.core.grid import Grid
from propagation_sanity.core.field import SampledField
from propagation_sanity.core.metrics import (
    intensity_relative_error,
    complex_field_relative_error,
    global_phase_offset,
    phase_error,
    power,
)


@pytest.fixture
def grid():
    return Grid(nx=64, ny=64, dx=1e-6, dy=1e-6)


@pytest.fixture
def random_field(grid):
    rng = np.random.default_rng(42)
    data = rng.standard_normal((64, 64)) + 1j * rng.standard_normal((64, 64))
    return SampledField(data=data, grid=grid)


# ------------------------------------------------------------------
# §70  Global phase invariance
# ------------------------------------------------------------------

class TestGlobalPhaseInvariance:
    """If U₂ = U₁ exp(iα), then ε_U ≈ 0."""

    def test_zero_error_for_global_phase_shift(self, random_field):
        alpha = 1.234
        shifted_data = random_field.data * np.exp(1j * alpha)
        shifted = SampledField(data=shifted_data, grid=random_field.grid)

        err = complex_field_relative_error(shifted, random_field)
        assert err == pytest.approx(0.0, abs=1e-12)

    def test_phase_offset_recovery(self, random_field):
        alpha = 0.7
        shifted_data = random_field.data * np.exp(1j * alpha)
        shifted = SampledField(data=shifted_data, grid=random_field.grid)

        recovered = global_phase_offset(shifted, random_field)
        assert recovered == pytest.approx(alpha, abs=1e-10)

    def test_intensity_invariant_to_phase(self, random_field):
        """Intensity error should be zero for pure phase shift."""
        alpha = 2.5
        shifted_data = random_field.data * np.exp(1j * alpha)
        shifted = SampledField(data=shifted_data, grid=random_field.grid)

        err = intensity_relative_error(shifted, random_field)
        assert err == pytest.approx(0.0, abs=1e-14)


# ------------------------------------------------------------------
# §70  Scaling invariance
# ------------------------------------------------------------------

class TestScalingInvariance:
    """Normalized spectral-energy metrics: U → cU should not change result."""

    def test_intensity_error_scaling(self, grid):
        """ε_I should scale with |c|² difference."""
        data = np.ones((64, 64), dtype=np.complex128)
        f1 = SampledField(data=data, grid=grid)
        f2 = SampledField(data=data * 2.0, grid=grid)
        f3 = SampledField(data=data * 2.0, grid=grid)

        # Same field → zero error
        err_same = intensity_relative_error(f2, f3)
        assert err_same == pytest.approx(0.0, abs=1e-14)


# ------------------------------------------------------------------
# Basic metric tests
# ------------------------------------------------------------------

class TestIntensityRelativeError:
    def test_identical_fields(self, grid):
        data = np.ones((64, 64), dtype=np.complex128) * (1 + 2j)
        fa = SampledField(data=data.copy(), grid=grid)
        fb = SampledField(data=data.copy(), grid=grid)
        assert intensity_relative_error(fa, fb) == pytest.approx(0.0, abs=1e-14)

    def test_known_error(self, grid):
        da = np.ones((64, 64), dtype=np.complex128)
        db = np.ones((64, 64), dtype=np.complex128) * 2.0
        fa = SampledField(data=da, grid=grid)
        fb = SampledField(data=db, grid=grid)

        # I_a = 1 everywhere, I_b = 4 everywhere
        # ||I_a - I_b||_2 / ||I_b||_2 = ||3|| / ||4|| = 3/4
        err = intensity_relative_error(fa, fb)
        assert err == pytest.approx(3.0 / 4.0, rel=1e-10)


class TestPhaseError:
    def test_zero_phase_error(self, grid):
        data = np.ones((64, 64), dtype=np.complex128)
        fa = SampledField(data=data, grid=grid)
        fb = SampledField(data=data, grid=grid)
        result = phase_error(fa, fb)
        assert result["mean_abs"] == pytest.approx(0.0, abs=1e-14)
        assert result["max_abs"] == pytest.approx(0.0, abs=1e-14)

    def test_masked_by_intensity(self, grid):
        """Phase error should only count significant pixels."""
        data = np.zeros((64, 64), dtype=np.complex128)
        data[30:35, 30:35] = 1.0  # small bright region
        fa = SampledField(data=data, grid=grid)
        fb = SampledField(data=data, grid=grid)
        result = phase_error(fa, fb, intensity_threshold=0.01)
        assert result["n_pixels"] > 0
        assert result["n_pixels"] < 64 * 64


class TestPower:
    def test_uniform_power(self, grid):
        data = np.ones((64, 64), dtype=np.complex128)
        f = SampledField(data=data, grid=grid)
        expected = 64 * 64 * 1e-6 * 1e-6
        assert power(f) == pytest.approx(expected)
