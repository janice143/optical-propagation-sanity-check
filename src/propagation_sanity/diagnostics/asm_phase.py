"""ASM-specific diagnostics.

Analyzes the phase variation of the Angular Spectrum Method transfer function
across adjacent discrete frequency grid samples.
"""

from __future__ import annotations

from typing import Optional

import numpy as np

from propagation_sanity.core.grid import Grid
from propagation_sanity.core.wave import Wave
from propagation_sanity.core.report import (
    ReportItem,
    AssessmentType,
    ThresholdProvenance,
    ResultStatus,
)


def _asm_unwrapped_phase(fx: np.ndarray, fy: np.ndarray, z: float, wavelength: float) -> np.ndarray:
    """Compute the *unwrapped* analytical ASM transfer-function phase.

    .. math::
        \\phi(f_x, f_y) = 2\\pi z \\sqrt{1/\\lambda^2 - f_x^2 - f_y^2}

    Returns NaN for evanescent components (f² > 1/λ²).
    """
    inv_lam_sq = 1.0 / wavelength**2
    arg = inv_lam_sq - fx**2 - fy**2
    phase = np.full_like(arg, np.nan)
    prop = arg >= 0
    phase[prop] = 2 * np.pi * z * np.sqrt(arg[prop])
    return phase


def asm_phase_step(
    grid: Grid,
    wave: Wave,
    z: float,
    spectral_support_fraction: Optional[float] = None,
) -> ReportItem:
    """Analyze the phase step of the ASM transfer function between adjacent frequencies.

    Computes the maximum phase change of the ASM transfer function
    between adjacent frequency samples, using the **unwrapped
    analytical** phase.

    Parameters
    ----------
    grid : Grid
        Computation grid.
    wave : Wave
        Wave parameters.
    z : float
        Propagation distance (m).
    spectral_support_fraction : float, optional
        If given, restrict analysis to frequencies within this
        fraction of Nyquist.  Default: full propagating spectrum.
    """
    lam = wave.wavelength_medium
    FX, FY = grid.fxy_meshgrid_shifted()
    phi = _asm_unwrapped_phase(FX, FY, z, lam)

    # Phase steps along x (column direction)
    dphi_x = np.abs(np.diff(phi, axis=1))
    # Phase steps along y (row direction)
    dphi_y = np.abs(np.diff(phi, axis=0))

    # Mask to selected spectral support
    if spectral_support_fraction is not None:
        frac = spectral_support_fraction
        mask_2d = (np.abs(FX) <= frac * grid.nyquist_x) & (
            np.abs(FY) <= frac * grid.nyquist_y
        )
        # For diff arrays, mask must be shrunk
        mask_x = mask_2d[:, :-1] & mask_2d[:, 1:]
        mask_y = mask_2d[:-1, :] & mask_2d[1:, :]

        dphi_x_valid = dphi_x[mask_x & np.isfinite(dphi_x)]
        dphi_y_valid = dphi_y[mask_y & np.isfinite(dphi_y)]
    else:
        dphi_x_valid = dphi_x[np.isfinite(dphi_x)]
        dphi_y_valid = dphi_y[np.isfinite(dphi_y)]

    max_step_x = float(dphi_x_valid.max()) if dphi_x_valid.size > 0 else 0.0
    max_step_y = float(dphi_y_valid.max()) if dphi_y_valid.size > 0 else 0.0
    max_step = max(max_step_x, max_step_y)

    value = {
        "max_phase_step": max_step,
        "max_phase_step_pi": max_step / np.pi,
        "max_step_x": max_step_x,
        "max_step_y": max_step_y,
        "z": z,
    }

    if max_step > np.pi:
        interp = (
            f"Max ASM phase step is {max_step/np.pi:.1f}π — "
            "the transfer function varies rapidly between adjacent "
            "frequency samples. Standard ASM may produce aliased results."
        )
    else:
        interp = (
            f"Max ASM phase step is {max_step/np.pi:.2f}π — "
            "transfer function is adequately sampled at this resolution."
        )

    return ReportItem(
        id="asm.phase_step",
        title="ASM phase step",
        category="diagnostics",
        assessment_type=AssessmentType.DIAGNOSTIC,
        applicable_methods=["asm"],
        value=value,
        status=ResultStatus.INFO,
        unit="rad",
        formula="Δφ = |φ(f+Δf) - φ(f)| using analytical unwrapped phase",
        assumptions="Analytical (unwrapped) phase; not arg(H)",
        threshold=None,
        threshold_provenance=ThresholdProvenance.PROJECT_DEFAULT,
        source="sampling theory + original article",
        interpretation=interp,
        recommended_action=(
            "Run ASM formal criterion and/or enable BLAS."
            if max_step > np.pi
            else "Phase step is within project guideline."
        ),
    )
