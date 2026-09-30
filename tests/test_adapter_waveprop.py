"""Tests for WavepropAdapter — Phase 5 requirement.

Verifies:
1. Coordinate conventions (shape, dimensions, x/y order)
2. Energy conservation / normalization in propagating regime
3. Simple propagation across methods (ASM, Fresnel, Fraunhofer, FFT_DI)
4. Metadata completeness
"""

import numpy as np
import pytest

from propagation_sanity.core.grid import Grid
from propagation_sanity.core.wave import Wave
from propagation_sanity.core.field import SampledField, SquareAperture, GaussianBeam
from propagation_sanity.core.propagation_config import (
    PropagationConfig,
    PropagationMethod,
)
from propagation_sanity.adapters.waveprop_adapter import WavepropAdapter


@pytest.fixture
def adapter():
    return WavepropAdapter()


@pytest.fixture
def test_setup():
    grid = Grid(nx=128, ny=128, dx=2e-6, dy=2e-6)
    wave = Wave(wavelength=532e-9)
    source = GaussianBeam(waist=40e-6, amplitude=1.0)
    field = source.sample(grid)
    return grid, wave, field


class TestWavepropCoordinates:
    """Check coordinate conventions and shapes."""

    def test_asm_preserves_grid_shape_and_spacing(self, adapter, test_setup):
        grid, wave, field = test_setup
        config = PropagationConfig(method=PropagationMethod.ASM)
        result = adapter.propagate(field, wave, z=1e-3, config=config)

        assert result.field.data.shape == (grid.ny, grid.nx)
        assert result.output_grid.nx == grid.nx
        assert result.output_grid.ny == grid.ny
        assert result.output_grid.dx == pytest.approx(grid.dx)
        assert result.output_grid.dy == pytest.approx(grid.dy)

    def test_fresnel_scales_output_grid(self, adapter, test_setup):
        grid, wave, field = test_setup
        z = 10e-3
        config = PropagationConfig(method=PropagationMethod.FRESNEL)
        result = adapter.propagate(field, wave, z=z, config=config)

        expected_dx = wave.wavelength * z / (grid.nx * grid.dx)
        expected_dy = wave.wavelength * z / (grid.ny * grid.dy)

        assert result.field.data.shape == (grid.ny, grid.nx)
        assert result.output_grid.dx == pytest.approx(expected_dx)
        assert result.output_grid.dy == pytest.approx(expected_dy)

    def test_fraunhofer_coordinates(self, adapter, test_setup):
        grid, wave, field = test_setup
        z = 100e-3
        config = PropagationConfig(method=PropagationMethod.FRAUNHOFER)
        result = adapter.propagate(field, wave, z=z, config=config)

        expected_dx = wave.wavelength * z / (grid.nx * grid.dx)
        assert result.output_grid.dx == pytest.approx(expected_dx)


class TestWavepropEnergyConservation:
    """Check that ASM roughly conserves power for propagating beam."""

    def test_asm_power_conservation(self, adapter, test_setup):
        grid, wave, field = test_setup
        input_power = field.power

        config = PropagationConfig(method=PropagationMethod.ASM, padding=2.0)
        result = adapter.propagate(field, wave, z=1e-3, config=config)
        output_power = result.field.power

        # For a smooth Gaussian beam well inside the grid at short z,
        # power should be conserved within ~2%
        assert output_power == pytest.approx(input_power, rel=0.02)


class TestWavepropMethods:
    """Check execution of different methods."""

    def test_asm_with_and_without_bandlimit(self, adapter, test_setup):
        grid, wave, field = test_setup
        cfg_blas = PropagationConfig(method=PropagationMethod.ASM, bandlimit=True)
        cfg_std = PropagationConfig(method=PropagationMethod.ASM, bandlimit=False)

        res_blas = adapter.propagate(field, wave, z=5e-3, config=cfg_blas)
        res_std = adapter.propagate(field, wave, z=5e-3, config=cfg_std)

        assert np.all(np.isfinite(res_blas.field.data))
        assert np.all(np.isfinite(res_std.field.data))

    def test_fft_di(self, adapter, test_setup):
        grid, wave, field = test_setup
        config = PropagationConfig(method=PropagationMethod.FFT_DI)
        result = adapter.propagate(field, wave, z=1e-3, config=config)
        assert result.field.data.shape == (grid.ny, grid.nx)
        assert np.all(np.isfinite(result.field.data))


class TestWavepropMetadata:
    """Check metadata returned in PropagationResult."""

    def test_metadata_fields(self, adapter, test_setup):
        grid, wave, field = test_setup
        config = PropagationConfig(method=PropagationMethod.ASM, bandlimit=True)
        result = adapter.propagate(field, wave, z=2e-3, config=config)

        meta = result.metadata
        assert meta["backend"] == "waveprop"
        assert meta["method"] == "asm"
        assert meta["z"] == 2e-3
        assert meta["wavelength"] == wave.wavelength
        assert meta["bandlimit"] is True
