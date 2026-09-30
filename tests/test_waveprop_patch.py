"""Tests for the defensive waveprop runtime patch module."""

import warnings
import numpy as np
import pytest

from propagation_sanity.core.grid import Grid
from propagation_sanity.core.wave import Wave
from propagation_sanity.core.field import SampledField
from propagation_sanity.core.propagation_config import (
    PropagationConfig,
    PropagationMethod,
)
from propagation_sanity.adapters.waveprop_adapter import WavepropAdapter
from propagation_sanity.adapters.waveprop_patch import ensure_waveprop_patched


def test_ensure_waveprop_patched_idempotent():
    """`ensure_waveprop_patched` should run cleanly and be idempotent."""
    res1 = ensure_waveprop_patched()
    res2 = ensure_waveprop_patched()

    assert isinstance(res1, dict)
    assert isinstance(res2, dict)
    assert res1 == res2


def test_angular_spectrum_np_pad_false_non_square():
    """`angular_spectrum_np(pad=False)` must run without UnboundLocalError
    and return correct coordinates on non-square inputs (Ny != Nx).
    """
    ensure_waveprop_patched()
    from waveprop.rs import angular_spectrum_np

    Ny, Nx = 48, 32
    u_in = np.ones((Ny, Nx), dtype=complex)
    u_out, x2, y2 = angular_spectrum_np(
        u_in=u_in,
        wv=632e-9,
        d1=[2e-6, 3e-6],
        dz=1e-3,
        pad=False,
        bandlimit=False,
    )

    assert u_out.shape == (Ny, Nx)
    assert x2.shape == (1, Nx)
    assert y2.shape == (Ny, 1)
    assert np.all(np.isfinite(u_out))


def test_fft_di_preserves_complex_phase_without_warning():
    """`fft_di` must preserve imaginary/phase content and not raise ComplexWarning."""
    ensure_waveprop_patched()
    from waveprop.rs import fft_di

    Ny, Nx = 32, 32
    phase = np.linspace(0, 2 * np.pi, Nx)
    u_in = np.exp(1j * phase)[np.newaxis, :].repeat(Ny, axis=0)

    with warnings.catch_warnings(record=True) as ws:
        warnings.simplefilter("always")
        u_out, x2, y2 = fft_di(u_in, wv=632e-9, d1=4e-6, dz=5e-3)

        complex_warns = [w for w in ws if issubclass(w.category, np.ComplexWarning)]
        assert len(complex_warns) == 0, "fft_di should not cast complex array to float"

    assert np.iscomplexobj(u_out)
    assert np.max(np.abs(u_out.imag)) > 1e-4


def test_waveprop_adapter_unpadded_asm():
    """WavepropAdapter should successfully execute unpadded ASM (padding=1.0)."""
    grid = Grid(nx=64, ny=48, dx=2e-6, dy=2e-6)
    wave = Wave(wavelength=532e-9)
    field = SampledField(data=np.ones((grid.ny, grid.nx), dtype=complex), grid=grid)

    adapter = WavepropAdapter()
    config = PropagationConfig(method=PropagationMethod.ASM, padding=1.0)
    result = adapter.propagate(field, wave, z=2e-3, config=config)

    assert result.field.data.shape == (grid.ny, grid.nx)
    assert np.all(np.isfinite(result.field.data))


def test_waveprop_adapter_complex_fft_di():
    """WavepropAdapter should execute FFT_DI on complex fields without losing imaginary part."""
    grid = Grid(nx=32, ny=32, dx=4e-6, dy=4e-6)
    wave = Wave(wavelength=632e-9)
    data = np.exp(1j * np.linspace(0, np.pi, 32))[None, :].repeat(32, axis=0)
    field = SampledField(data=data, grid=grid)

    adapter = WavepropAdapter()
    config = PropagationConfig(method=PropagationMethod.FFT_DI)
    result = adapter.propagate(field, wave, z=5e-3, config=config)

    assert result.field.data.shape == (32, 32)
    assert np.iscomplexobj(result.field.data)
    assert np.max(np.abs(result.field.data.imag)) > 1e-4
