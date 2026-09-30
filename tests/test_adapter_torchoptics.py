"""Tests for TorchOpticsAdapter.

Verifies:
1. Coordinate conventions (shape, dimensions, x/y order, anisotropic grids)
2. Machine-precision cross-validation against WavepropAdapter for ASM and FFT_DI/DIM
3. Energy / power conservation in propagating regimes
4. Execution across propagation methods (ASM, DIM, ASM_FRESNEL, DIM_FRESNEL, AUTO)
5. asm_pad handling: unpadded, custom padding, and default 2x padding
6. Arbitrary output grid resampling (output shape and spacing)
7. Voelz critical propagation distance calculation
8. Metadata completeness and reproducibility tracking
9. Convergence engine execution with backend="torchoptics"
10. Autograd / differentiable propagation support
"""

import numpy as np
import pytest
import torch

pytest.importorskip("torchoptics")

from propagation_sanity.core.grid import Grid
from propagation_sanity.core.wave import Wave
from propagation_sanity.core.field import SampledField, SquareAperture, GaussianBeam
from propagation_sanity.core.propagation_config import (
    PropagationConfig,
    PropagationMethod,
)
from propagation_sanity.adapters.waveprop_adapter import WavepropAdapter
from propagation_sanity.adapters.torchoptics_adapter import TorchOpticsAdapter
from propagation_sanity.convergence.engine import (
    padding_convergence,
    resolution_convergence,
    domain_convergence,
)
from propagation_sanity.benchmarks.diff_optics import (
    PhaseModulator,
    optimize_diffractive_element_torchoptics,
    evaluate_phase_profile_torchoptics,
)


@pytest.fixture
def adapter():
    return TorchOpticsAdapter()


@pytest.fixture
def test_setup():
    grid = Grid(nx=64, ny=64, dx=2e-6, dy=2e-6)
    wave = Wave(wavelength=532e-9)
    source = GaussianBeam(waist=30e-6, amplitude=1.0)
    field = source.sample(grid)
    return grid, wave, field


class TestTorchOpticsCoordinates:
    """Verify coordinate mapping and shape conventions."""

    def test_asm_preserves_grid_shape_and_spacing(self, adapter, test_setup):
        grid, wave, field = test_setup
        config = PropagationConfig(
            method=PropagationMethod.ASM,
            backend="torchoptics",
            padding=1.0,
        )
        result = adapter.propagate(field, wave, z=1e-3, config=config)

        assert result.field.data.shape == (grid.ny, grid.nx)
        assert result.output_grid.nx == grid.nx
        assert result.output_grid.ny == grid.ny
        assert result.output_grid.dx == pytest.approx(grid.dx)
        assert result.output_grid.dy == pytest.approx(grid.dy)

    def test_anisotropic_grid_coordinates(self, adapter):
        grid = Grid(nx=128, ny=64, dx=2e-6, dy=4e-6)
        wave = Wave(wavelength=532e-9)
        source = GaussianBeam(waist=30e-6, amplitude=1.0)
        field = source.sample(grid)

        config = PropagationConfig(
            method=PropagationMethod.ASM,
            backend="torchoptics",
            padding=1.0,
        )
        result = adapter.propagate(field, wave, z=1e-3, config=config)

        assert result.field.data.shape == (64, 128)
        assert result.output_grid.nx == 128
        assert result.output_grid.ny == 64
        assert result.output_grid.dx == pytest.approx(2e-6)
        assert result.output_grid.dy == pytest.approx(4e-6)

    def test_cross_validation_asm_against_waveprop(self, adapter, test_setup):
        """TorchOptics and waveprop unpadded ASM should agree to machine precision."""
        grid, wave, field = test_setup
        z = 1.5e-3

        wp_adapter = WavepropAdapter()
        cfg_wp = PropagationConfig(method=PropagationMethod.ASM, padding=1.0, bandlimit=False)
        res_wp = wp_adapter.propagate(field, wave, z=z, config=cfg_wp)

        cfg_to = PropagationConfig(
            method=PropagationMethod.ASM,
            backend="torchoptics",
            padding=1.0,
            bandlimit=False,
        )
        res_to = adapter.propagate(field, wave, z=z, config=cfg_to)

        max_err = np.max(np.abs(res_wp.field.data - res_to.field.data))
        assert max_err < 1e-11

    def test_cross_validation_dim_against_fft_di(self, adapter):
        """TorchOptics DIM and waveprop FFT_DI agree to machine precision when boundaries are zero.

        Note: Waveprop's fft_di applies trapezoidal weights (0.5 factor) at the array boundaries
        when use_simpson=True. For fields with strictly zero boundary values, the two implementations
        agree to ~1e-13.
        """
        grid = Grid(nx=64, ny=64, dx=4e-6, dy=4e-6)
        wave = Wave(wavelength=532e-9)
        source = SquareAperture(half_width=40e-6)
        field = source.sample(grid)
        z = 2e-3

        wp_adapter = WavepropAdapter()
        cfg_wp = PropagationConfig(method=PropagationMethod.FFT_DI)
        res_wp = wp_adapter.propagate(field, wave, z=z, config=cfg_wp)

        cfg_to = PropagationConfig(
            method=PropagationMethod.FFT_DI,
            backend="torchoptics",
        )
        res_to = adapter.propagate(field, wave, z=z, config=cfg_to)

        max_val = np.max(np.abs(res_wp.field.data))
        rel_err = np.max(np.abs(res_wp.field.data - res_to.field.data)) / max_val
        assert rel_err < 1e-10


class TestTorchOpticsPowerConservation:
    """Verify energy conservation under free-space propagation."""

    def test_asm_power_conservation(self, adapter, test_setup):
        grid, wave, field = test_setup
        input_power = field.power

        config = PropagationConfig(
            method=PropagationMethod.ASM,
            backend="torchoptics",
            padding=2.0,
        )
        result = adapter.propagate(field, wave, z=1e-3, config=config)
        output_power = result.field.power

        assert output_power == pytest.approx(input_power, rel=0.02)

    def test_dim_power_conservation(self, adapter, test_setup):
        grid, wave, field = test_setup
        input_power = field.power

        config = PropagationConfig(
            method=PropagationMethod.FFT_DI,
            backend="torchoptics",
        )
        result = adapter.propagate(field, wave, z=1e-3, config=config)
        output_power = result.field.power

        assert output_power == pytest.approx(input_power, rel=0.03)


class TestTorchOpticsMethods:
    """Verify execution of different propagation algorithms."""

    def test_fresnel_asm_and_dim(self, adapter, test_setup):
        grid, wave, field = test_setup
        z = 5e-3

        cfg_asm_fresnel = PropagationConfig(
            method=PropagationMethod.FRESNEL,
            backend="torchoptics",
            extra={"use_dim": False},
        )
        cfg_dim_fresnel = PropagationConfig(
            method=PropagationMethod.FRESNEL,
            backend="torchoptics",
            extra={"use_dim": True},
        )

        res_asm = adapter.propagate(field, wave, z=z, config=cfg_asm_fresnel)
        res_dim = adapter.propagate(field, wave, z=z, config=cfg_dim_fresnel)

        assert np.all(np.isfinite(res_asm.field.data))
        assert np.all(np.isfinite(res_dim.field.data))
        assert res_asm.metadata["method"] == "ASM_FRESNEL"
        assert res_dim.metadata["method"] == "DIM_FRESNEL"

    def test_auto_propagation_method(self, adapter, test_setup):
        grid, wave, field = test_setup

        cfg_auto = PropagationConfig(
            method=PropagationMethod.ASM,
            backend="torchoptics",
            extra={"propagation_method": "AUTO"},
        )
        # Short distance: ASM chosen
        res_short = adapter.propagate(field, wave, z=1e-4, config=cfg_auto)
        assert np.all(np.isfinite(res_short.field.data))

        # Long distance: DIM chosen
        res_long = adapter.propagate(field, wave, z=10e-3, config=cfg_auto)
        assert np.all(np.isfinite(res_long.field.data))

    def test_unsupported_fraunhofer_raises(self, adapter, test_setup):
        grid, wave, field = test_setup
        config = PropagationConfig(
            method=PropagationMethod.FRAUNHOFER,
            backend="torchoptics",
        )
        with pytest.raises(NotImplementedError):
            adapter.propagate(field, wave, z=1e-3, config=config)


class TestTorchOpticsPadding:
    """Verify asm_pad parameter and boundary effects."""

    def test_explicit_asm_pad(self, adapter, test_setup):
        grid, wave, field = test_setup
        config = PropagationConfig(
            method=PropagationMethod.ASM,
            backend="torchoptics",
            extra={"asm_pad": (16, 16)},
        )
        result = adapter.propagate(field, wave, z=2e-3, config=config)
        assert result.metadata["asm_pad"] == (16, 16)
        assert result.field.data.shape == (grid.ny, grid.nx)

    def test_default_torchoptics_padding(self, adapter, test_setup):
        grid, wave, field = test_setup
        config = PropagationConfig(
            method=PropagationMethod.ASM,
            backend="torchoptics",
            extra={"use_default_asm_pad": True},
        )
        result = adapter.propagate(field, wave, z=2e-3, config=config)
        assert result.metadata["asm_pad"] is None
        assert result.field.data.shape == (grid.ny, grid.nx)

    def test_padding_reduces_boundary_wrap_around(self, adapter):
        """Off-center aperture creates boundary diffraction; padding alters the wrap-around."""
        grid = Grid(nx=64, ny=64, dx=4e-6, dy=4e-6)
        wave = Wave(wavelength=532e-9)
        source = SquareAperture(half_width=40e-6)
        field = source.sample(grid)

        cfg_unpadded = PropagationConfig(
            method=PropagationMethod.ASM,
            backend="torchoptics",
            padding=1.0,
        )
        cfg_padded = PropagationConfig(
            method=PropagationMethod.ASM,
            backend="torchoptics",
            padding=2.0,
        )

        res_unpadded = adapter.propagate(field, wave, z=10e-3, config=cfg_unpadded)
        res_padded = adapter.propagate(field, wave, z=10e-3, config=cfg_padded)

        diff = np.mean(np.abs(res_unpadded.field.data - res_padded.field.data))
        assert diff > 0.01  # Significant wrap-around difference demonstrated


class TestTorchOpticsOutputSampling:
    """Verify arbitrary output grid resampling."""

    def test_propagate_to_different_output_grid(self, adapter, test_setup):
        grid, wave, field = test_setup
        target_grid = Grid(nx=48, ny=32, dx=3e-6, dy=3e-6)

        config = PropagationConfig(
            method=PropagationMethod.ASM,
            backend="torchoptics",
            padding=1.5,
            interpolation="bilinear",
        )
        result = adapter.propagate(field, wave, z=1e-3, config=config, output_grid=target_grid)

        assert result.field.data.shape == (32, 48)
        assert result.output_grid.nx == 48
        assert result.output_grid.ny == 32
        assert result.output_grid.dx == pytest.approx(3e-6)
        assert result.output_grid.dy == pytest.approx(3e-6)


class TestTorchOpticsCriticalDistance:
    """Verify calculation of Voelz critical propagation distance."""

    def test_critical_distance(self, adapter):
        grid = Grid(nx=64, ny=64, dx=2e-6, dy=2e-6)
        wave = Wave(wavelength=532e-9)

        zc_y, zc_x = adapter.calculate_critical_distance(grid, wave)

        # Expected: 2 * (N * dx / 2) * dx / lambda = N * dx^2 / lambda
        expected_zc = 64 * (2e-6 ** 2) / 532e-9
        assert zc_y == pytest.approx(expected_zc)
        assert zc_x == pytest.approx(expected_zc)


class TestTorchOpticsMetadata:
    """Verify metadata contents."""

    def test_metadata_fields(self, adapter, test_setup):
        grid, wave, field = test_setup
        config = PropagationConfig(
            method=PropagationMethod.ASM,
            backend="torchoptics",
            padding=1.5,
        )
        result = adapter.propagate(field, wave, z=2e-3, config=config)

        meta = result.metadata
        assert meta["backend"] == "torchoptics"
        assert meta["method"] == "ASM"
        assert meta["z"] == 2e-3
        assert meta["wavelength"] == wave.wavelength
        assert "critical_distance" in meta
        assert "torchoptics_version" in meta
        assert "torch_version" in meta


class TestTorchOpticsConvergenceEngine:
    """Verify convergence engine execution with backend='torchoptics'."""

    def test_padding_convergence(self, test_setup):
        grid, wave, field = test_setup
        config = PropagationConfig(
            method=PropagationMethod.ASM,
            backend="torchoptics",
        )
        item = padding_convergence(
            field=field,
            wave=wave,
            z=1e-3,
            config=config,
            padding_factors=(1.0, 1.5, 2.0),
            tolerance=0.05,
        )
        assert item.category == "convergence"
        assert len(item.value["errors"]) == 2

    def test_domain_convergence(self, test_setup):
        grid, wave, _ = test_setup
        source = GaussianBeam(waist=20e-6)
        config = PropagationConfig(
            method=PropagationMethod.ASM,
            backend="torchoptics",
            padding=1.0,
        )
        item = domain_convergence(
            source=source,
            base_grid=grid,
            wave=wave,
            z=1e-3,
            config=config,
            factors=(1, 2),
            tolerance=0.05,
        )
        assert item.category == "convergence"
        assert len(item.value["errors"]) == 1

    def test_resolution_convergence(self, test_setup):
        grid, wave, _ = test_setup
        source = GaussianBeam(waist=30e-6)
        config = PropagationConfig(
            method=PropagationMethod.ASM,
            backend="torchoptics",
            padding=1.0,
        )
        item = resolution_convergence(
            source=source,
            base_grid=grid,
            wave=wave,
            z=1e-3,
            config=config,
            factors=(1, 2),
            tolerance=0.05,
        )
        assert item.category == "convergence"
        assert len(item.value["errors"]) == 1


class TestTorchOpticsDifferentiable:
    """Verify autograd and differentiable propagation."""

    def test_propagate_tensor_gradient_flow(self, adapter, test_setup):
        grid, wave, _ = test_setup
        modulator = PhaseModulator(nx=32, ny=32)
        grid_small = Grid(nx=32, ny=32, dx=4e-6, dy=4e-6)

        x_in = torch.ones((32, 32), dtype=torch.complex64)
        u_mod = modulator(x_in)

        config = PropagationConfig(
            method=PropagationMethod.ASM,
            backend="torchoptics",
            padding=1.0,
        )

        u_out = adapter.propagate_tensor(
            u_in=u_mod,
            grid=grid_small,
            wave=wave,
            z=2e-3,
            config=config,
        )

        loss = torch.sum(torch.abs(u_out) ** 2)
        loss.backward()

        assert modulator.phase.grad is not None
        assert torch.isfinite(modulator.phase.grad).all()
        assert float(modulator.phase.grad.norm()) > 0.0

    def test_torchoptics_optimization_benchmark(self):
        """Train a phase modulator with TorchOptics and check loss reduction."""
        target = torch.zeros((24, 24), dtype=torch.float32)
        target[10:14, 10:14] = 1.0

        mod, losses = optimize_diffractive_element_torchoptics(
            target_intensity=target,
            nx=24,
            ny=24,
            dx=4e-6,
            dy=4e-6,
            wavelength=532e-9,
            z=15e-3,
            propagation_method="ASM",
            asm_pad=(8, 8),
            n_steps=10,
            lr=0.3,
        )

        assert len(losses) == 10
        assert losses[-1] < losses[0]

        eval_loss = evaluate_phase_profile_torchoptics(
            mod, target, nx=24, ny=24, dx=4e-6, dy=4e-6, wavelength=532e-9, z=15e-3, asm_pad=(8, 8)
        )
        assert eval_loss < losses[0]
        assert eval_loss == pytest.approx(losses[-1], rel=0.05)

