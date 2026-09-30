"""Tests for SampledField, FieldSource, and built-in sources."""

import numpy as np
import pytest

from propagation_sanity.core.grid import Grid
from propagation_sanity.core.field import (
    SampledField,
    SquareAperture,
    UniformField,
    GaussianBeam,
)


class TestSampledField:
    def setup_method(self):
        self.grid = Grid(nx=64, ny=64, dx=1e-6, dy=1e-6)

    def test_shape_validation(self):
        data = np.zeros((32, 64), dtype=np.complex128)
        with pytest.raises(ValueError, match="shape"):
            SampledField(data=data, grid=self.grid)

    def test_auto_complex_cast(self):
        data = np.ones((64, 64), dtype=np.float64)
        f = SampledField(data=data, grid=self.grid)
        assert np.iscomplexobj(f.data)

    def test_intensity(self):
        data = np.full((64, 64), 2.0 + 3j)
        f = SampledField(data=data, grid=self.grid)
        expected = 4.0 + 9.0  # |2+3i|² = 13
        np.testing.assert_allclose(f.intensity, expected)

    def test_amplitude(self):
        data = np.full((64, 64), 3.0 + 4j)
        f = SampledField(data=data, grid=self.grid)
        np.testing.assert_allclose(f.amplitude, 5.0)

    def test_phase(self):
        data = np.full((64, 64), 1j, dtype=np.complex128)
        f = SampledField(data=data, grid=self.grid)
        np.testing.assert_allclose(f.phase, np.pi / 2)

    def test_power(self):
        data = np.ones((64, 64), dtype=np.complex128)
        f = SampledField(data=data, grid=self.grid)
        expected = 64 * 64 * 1e-6 * 1e-6
        assert f.power == pytest.approx(expected)


class TestSquareAperture:
    def test_binary_mask(self):
        grid = Grid(nx=128, ny=128, dx=1e-6, dy=1e-6)
        source = SquareAperture(half_width=10e-6)
        field = source.sample(grid)

        X, Y = grid.xy_meshgrid()
        expected_mask = (np.abs(X) <= 10e-6) & (np.abs(Y) <= 10e-6)
        actual_nonzero = field.amplitude > 0.5

        np.testing.assert_array_equal(actual_nonzero, expected_mask)

    def test_compact_support(self):
        source = SquareAperture(half_width=50e-6)
        assert source.compact_support is True

    def test_characteristic_size(self):
        source = SquareAperture(half_width=50e-6)
        assert source.characteristic_size == pytest.approx(100e-6)

    def test_resample_different_grid(self):
        """Re-sampling on finer grid should give more pixels inside."""
        source = SquareAperture(half_width=50e-6)
        g1 = Grid(nx=128, ny=128, dx=2e-6, dy=2e-6)
        g2 = Grid(nx=256, ny=256, dx=1e-6, dy=1e-6)

        f1 = source.sample(g1)
        f2 = source.sample(g2)

        # Physical domain differs, but number of lit pixels should
        # roughly scale with area / pixel area.
        n1 = (f1.amplitude > 0.5).sum()
        n2 = (f2.amplitude > 0.5).sum()
        # g2 has 4× the pixel density, roughly 4× more lit pixels
        assert n2 > n1

    def test_negative_half_width(self):
        with pytest.raises(ValueError):
            SquareAperture(half_width=-1)


class TestUniformField:
    def test_uniform_value(self):
        grid = Grid(nx=32, ny=32, dx=1e-6, dy=1e-6)
        source = UniformField(amplitude=2.5 + 1j)
        field = source.sample(grid)
        np.testing.assert_allclose(field.data, 2.5 + 1j)

    def test_not_compact(self):
        assert UniformField().compact_support is False


class TestGaussianBeam:
    def test_peak_at_center(self):
        grid = Grid(nx=128, ny=128, dx=1e-6, dy=1e-6)
        source = GaussianBeam(waist=20e-6, amplitude=3.0)
        field = source.sample(grid)
        # Peak should be near the center
        center = (grid.ny // 2, grid.nx // 2)
        assert field.amplitude[center] == pytest.approx(3.0, abs=0.1)

    def test_not_compact(self):
        assert GaussianBeam(waist=10e-6).compact_support is False
