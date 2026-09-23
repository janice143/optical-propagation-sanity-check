"""waveprop-backed propagation models and their analytic validity hooks."""

from __future__ import annotations

import numpy as np
from scipy.interpolate import RegularGridInterpolator
from waveprop.fraunhofer import fraunhofer as waveprop_fraunhofer
from waveprop.fresnel import fresnel_conv as waveprop_fresnel_conv
from waveprop.rs import angular_spectrum as waveprop_angular_spectrum
from waveprop.rs import fft_di as waveprop_fft_di

from .grids import centered_axes, fft2c
from .types import GridSpec, PropagationModel, PropagationResult, PropagationSpec


def _waveprop_spacing(grid: GridSpec) -> list[float]:
    """waveprop orders two-dimensional sampling as ``[dy, dx]``."""

    return [grid.resolved_dy, grid.dx]


def _waveprop_result(result: tuple[np.ndarray, np.ndarray, np.ndarray]) -> PropagationResult:
    field, x, y = result
    return PropagationResult(
        field=np.asarray(field),
        x=np.asarray(x).squeeze(),
        y=np.asarray(y).squeeze(),
    )


def propagate_asm(
    field: np.ndarray, grid: GridSpec, propagation: PropagationSpec
) -> PropagationResult:
    """Band-limited angular-spectrum propagation without internal padding."""

    return _waveprop_result(
        waveprop_angular_spectrum(
            field,
            wv=propagation.wavelength,
            d1=_waveprop_spacing(grid),
            dz=propagation.z,
            bandlimit=True,
            pad=False,
        )
    )


def propagate_asm_padded(
    field: np.ndarray, grid: GridSpec, propagation: PropagationSpec
) -> PropagationResult:
    """Band-limited angular-spectrum propagation with waveprop zero padding."""

    return _waveprop_result(
        waveprop_angular_spectrum(
            field,
            wv=propagation.wavelength,
            d1=_waveprop_spacing(grid),
            dz=propagation.z,
            bandlimit=True,
            pad=True,
        )
    )


def propagate_asm_unbandlimited(
    field: np.ndarray, grid: GridSpec, propagation: PropagationSpec
) -> PropagationResult:
    """Unbandlimited ASM for diagnostic comparison, not the default."""

    return _waveprop_result(
        waveprop_angular_spectrum(
            field,
            wv=propagation.wavelength,
            d1=_waveprop_spacing(grid),
            dz=propagation.z,
            bandlimit=False,
            pad=False,
        )
    )


def propagate_fresnel(
    field: np.ndarray, grid: GridSpec, propagation: PropagationSpec
) -> PropagationResult:
    """One-step Fresnel convolution on a square-sampled spatial grid."""

    if not np.isclose(grid.dx, grid.resolved_dy):
        raise ValueError("waveprop.fresnel_conv requires square spatial sampling")
    return _waveprop_result(
        waveprop_fresnel_conv(
            field,
            wv=propagation.wavelength,
            d1=float(grid.dx),
            dz=propagation.z,
            pad=False,
        )
    )


def propagate_fraunhofer(
    field: np.ndarray, grid: GridSpec, propagation: PropagationSpec
) -> PropagationResult:
    """Fraunhofer propagation with waveprop's output-coordinate convention."""

    return _waveprop_result(
        waveprop_fraunhofer(
            field,
            wv=propagation.wavelength,
            d1=_waveprop_spacing(grid),
            dz=propagation.z,
        )
    )


def propagate_fft_di(
    field: np.ndarray, grid: GridSpec, propagation: PropagationSpec
) -> PropagationResult:
    """FFT-DI Rayleigh-Sommerfeld reference for real-valued input fields."""

    if np.any(np.abs(np.asarray(field).imag) > 0):
        raise ValueError("waveprop FFT-DI accepts only real-valued input fields here")
    return _waveprop_result(
        waveprop_fft_di(
            np.asarray(field).real,
            wv=propagation.wavelength,
            d1=_waveprop_spacing(grid),
            dz=propagation.z,
            N_out=[field.shape[1], field.shape[0]],
        )
    )


def propagate_direct_integration(
    field: np.ndarray,
    grid: GridSpec,
    propagation: PropagationSpec,
    *,
    n_di: int = 100,
) -> PropagationResult:
    """Downsampled brute-force Rayleigh-Sommerfeld reference.

    The direct integral costs roughly ``O(n_di**4)``. Its coarse output grid
    is returned without pretending it has the source grid's resolution; the
    checker resamples reference results onto the tested model's coordinates.
    """

    from waveprop.rs import direct_integration

    ny, nx = field.shape
    if ny != nx:
        raise ValueError(
            f"propagate_direct_integration requires a square grid (got {field.shape})"
        )
    if not np.isclose(grid.dx, grid.resolved_dy):
        raise ValueError("propagate_direct_integration requires square spatial sampling")
    if n_di < 2:
        raise ValueError("n_di must be at least 2")

    n_output = min(n_di, nx)
    source_x, source_y = centered_axes(field.shape, grid)
    sample_x = np.linspace(source_x[0], source_x[-1], n_output)
    sample_y = np.linspace(source_y[0], source_y[-1], n_output)
    sample_points = np.stack(
        np.meshgrid(sample_y, sample_x, indexing="ij"), axis=-1
    )
    real = RegularGridInterpolator((source_y, source_x), field.real)
    imag = RegularGridInterpolator((source_y, source_x), field.imag)
    sampled_field = real(sample_points) + 1j * imag(sample_points)
    sample_dx = float(np.median(np.diff(sample_x)))
    # Keep the reference on the source field of view. The coarse spacing is
    # explicit; returning a denser-looking axis would overstate DI resolution.
    half_width = max(nx, ny) * grid.dx / 2
    coordinates = np.linspace(-half_width, half_width, n_output)
    output = direct_integration(
        sampled_field,
        propagation.wavelength,
        sample_dx,
        propagation.z,
        x=coordinates,
        y=coordinates,
    )
    return PropagationResult(
        field=np.asarray(output, dtype=np.complex128),
        x=coordinates,
        y=coordinates.copy(),
    )


def exact_asm_phase(
    fx: np.ndarray, fy: np.ndarray, propagation: PropagationSpec
) -> np.ndarray:
    argument = 1 / propagation.wavelength**2 - fx**2 - fy**2
    kz = 2 * np.pi * np.sqrt(np.maximum(argument, 0.0))
    return propagation.z * kz


def fresnel_phase(
    fx: np.ndarray, fy: np.ndarray, propagation: PropagationSpec
) -> np.ndarray:
    k = 2 * np.pi / propagation.wavelength
    return propagation.z * (
        k - np.pi * propagation.wavelength * (fx**2 + fy**2)
    )


def _energy_ratio(values: np.ndarray, mask: np.ndarray) -> float:
    energy = np.abs(values) ** 2
    total = energy.sum()
    return float(energy[mask].sum() / total) if total > 0 else 0.0


def _blas_limits(
    shape: tuple[int, int], grid: GridSpec, propagation: PropagationSpec
) -> tuple[float, float]:
    ny, nx = shape
    sx = nx * grid.dx
    sy = ny * grid.resolved_dy
    z = abs(propagation.z)
    wavelength = propagation.wavelength
    fx_limit = 1 / (wavelength * np.sqrt(1 + (2 * z / sx) ** 2))
    fy_limit = 1 / (wavelength * np.sqrt(1 + (2 * z / sy) ** 2))
    return fx_limit, fy_limit


def asm_validity(field, grid, propagation, active_mask, fx, fy) -> dict:
    evanescent_energy = _energy_ratio(
        fft2c(field), (fx**2 + fy**2) > 1 / propagation.wavelength**2
    )
    fx_limit, fy_limit = _blas_limits(field.shape, grid, propagation)
    outside = active_mask & ((np.abs(fx) > fx_limit) | (np.abs(fy) > fy_limit))
    active_count = max(int(active_mask.sum()), 1)
    return {
        "phase_error_rad": 0.0,
        "evanescent_energy_ratio": evanescent_energy,
        "active_spectrum_outside_blas": float(outside.sum() / active_count),
        "criterion": "scalar ASM has no paraxial approximation; numerical checks still apply",
    }


def fresnel_validity(field, grid, propagation, active_mask, fx, fy) -> dict:
    error = np.abs(exact_asm_phase(fx, fy, propagation) - fresnel_phase(fx, fy, propagation))
    return {
        "phase_error_rad": float(np.max(error[active_mask])) if np.any(active_mask) else 0.0,
        "criterion": "max z|kz_exact-kz_Fresnel| over active spectrum",
    }


def fraunhofer_validity(field, grid, propagation, active_mask, fx, fy) -> dict:
    amplitude = np.abs(field)
    support = amplitude >= 1e-3 * amplitude.max()
    x, y = centered_axes(field.shape, grid)
    x_grid, y_grid = np.meshgrid(x, y)
    k = 2 * np.pi / propagation.wavelength
    phase_error = np.abs(k * (x_grid**2 + y_grid**2) / (2 * propagation.z))
    return {
        "phase_error_rad": float(np.max(phase_error[support])) if np.any(support) else 0.0,
        "criterion": "max input quadratic phase neglected by Fraunhofer",
    }


ASM_MODEL = PropagationModel(
    "Waveprop band-limited ASM",
    propagate_asm,
    exact_asm_phase,
    asm_validity,
    "Default model: band-limited ASM without internal padding.",
)
ASM_PADDED_MODEL = PropagationModel(
    "Waveprop band-limited ASM (padded)",
    propagate_asm_padded,
    exact_asm_phase,
    asm_validity,
    "Band-limited ASM with waveprop-owned zero padding.",
)
ASM_UNBANDED_MODEL = PropagationModel(
    "Waveprop ASM (bandlimit disabled)",
    propagate_asm_unbandlimited,
    exact_asm_phase,
    asm_validity,
    "Diagnostic model for demonstrating the effect of ASM band limiting.",
)
FRESNEL_MODEL = PropagationModel(
    "Fresnel convolution", propagate_fresnel, fresnel_phase, fresnel_validity
)
FRAUNHOFER_MODEL = PropagationModel(
    "Fraunhofer", propagate_fraunhofer, None, fraunhofer_validity
)
FFT_DI_MODEL = PropagationModel(
    "FFT-DI (Rayleigh-Sommerfeld)",
    propagate_fft_di,
    description="Fast cross-method reference for real-valued inputs.",
)
DIRECT_INTEGRATION_MODEL = PropagationModel(
    "Direct integration (Rayleigh-Sommerfeld, downsampled)",
    propagate_direct_integration,
    description="Slow, coarse brute-force reference; intended for cross-method checks.",
)

# Migration aliases retained for code copied from the original notebook.
BLAS_MODEL = ASM_MODEL
ASM_BANDLIMITED_PADDED_MODEL = ASM_PADDED_MODEL
UNBANDED_ASM_MODEL = ASM_UNBANDED_MODEL
