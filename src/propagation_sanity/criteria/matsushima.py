"""Matsushima & Shimobaba (2009) BLAS admissible band criterion.

Implements checker C08 from the specification:
- ASM admissible band / Matsushima criterion (FORMAL_CRITERION)

Reference:
K. Matsushima and T. Shimobaba, "Band-Limited Angular Spectrum Method for
Numerical Simulation of Free-Space Propagation in Far and Near Fields,"
Opt. Express 17, 19662-19673 (2009). DOI: 10.1364/OE.17.019662.
"""

from __future__ import annotations

from typing import Optional, Dict, Any

import numpy as np

from propagation_sanity.core.grid import Grid
from propagation_sanity.core.wave import Wave
from propagation_sanity.core.field import SampledField
from propagation_sanity.core.report import (
    ReportItem,
    AssessmentType,
    ThresholdProvenance,
    ResultStatus,
)
from propagation_sanity.diagnostics.spectrum import effective_bandwidth


def matsushima_admissible_limit(
    domain_size: float,
    z: float,
    wavelength: float,
) -> float:
    """Compute Matsushima limit frequency along one dimension.

    For on-axis propagation:
    .. math::
        f_{\\max} = \\frac{1}{\\lambda \\sqrt{1 + 4 z^2 / S^2}}

    where S is the spatial computation window size (including padding if used).
    """
    if z == 0:
        return 1.0 / wavelength
    s = domain_size
    return float(1.0 / (wavelength * np.sqrt(1.0 + 4.0 * (z**2) / (s**2))))


def asm_admissible_band_check(
    grid: Grid,
    wave: Wave,
    z: float,
    field: Optional[SampledField] = None,
    padded: bool = True,
    bandlimit_enabled: bool = False,
) -> ReportItem:
    """C08 — ASM admissible band formal criterion (Matsushima 2009).

    Evaluates whether the simulation frequency range stays within the
    aliasing-free sampling bound for the ASM transfer function.

    Parameters
    ----------
    grid : Grid
        Computation grid.
    wave : Wave
        Wave parameters.
    z : float
        Propagation distance (m).
    field : SampledField, optional
        Sampled field to evaluate against effective bandwidth.
    padded : bool
        Whether FFT zero-padding (typically 2x) is applied.
    bandlimit_enabled : bool
        Whether BLAS (band-limiting filter) is active in the propagator.
    """
    lam = wave.wavelength_medium
    sx = grid.Lx * (2.0 if padded else 1.0)
    sy = grid.Ly * (2.0 if padded else 1.0)

    fx_limit = matsushima_admissible_limit(sx, z, lam)
    fy_limit = matsushima_admissible_limit(sy, z, lam)

    # Compare against Nyquist
    nyq_x_safe = grid.nyquist_x <= fx_limit
    nyq_y_safe = grid.nyquist_y <= fy_limit

    # If field is available, check whether effective energy exceeds the limit
    field_check = {}
    field_exceeds = False
    if field is not None:
        bw = effective_bandwidth(field, coverage_levels=[0.99])
        x_99 = bw.value["x"].get("99.0%", 0.0)
        y_99 = bw.value["y"].get("99.0%", 0.0)
        field_check = {
            "x_99_percent_freq": x_99,
            "y_99_percent_freq": y_99,
            "x_energy_within_limit": x_99 <= fx_limit,
            "y_energy_within_limit": y_99 <= fy_limit,
        }
        if x_99 > fx_limit or y_99 > fy_limit:
            field_exceeds = True

    value = {
        "fx_limit": fx_limit,
        "fy_limit": fy_limit,
        "nyquist_x": grid.nyquist_x,
        "nyquist_y": grid.nyquist_y,
        "nyquist_within_limit": nyq_x_safe and nyq_y_safe,
        "bandlimit_enabled": bandlimit_enabled,
        "field_effective_support": field_check,
        "z": z,
    }

    if bandlimit_enabled:
        status = ResultStatus.PASS
        interp = (
            f"BLAS filter is active: frequencies beyond "
            f"(fx_limit={fx_limit:.1e}, fy_limit={fy_limit:.1e}) 1/m "
            "are band-limited according to Matsushima (2009)."
        )
    elif nyq_x_safe and nyq_y_safe:
        status = ResultStatus.PASS
        interp = (
            f"All frequencies up to Nyquist are within Matsushima limit "
            f"(fx_lim={fx_limit:.1e}, fy_lim={fy_limit:.1e}) 1/m. Standard ASM is alias-free."
        )
    elif field_exceeds:
        status = ResultStatus.FAIL
        interp = (
            f"Matsushima criterion VIOLATED: significant field energy (99%) "
            f"exceeds the admissible frequency limit (fx_lim={fx_limit:.1e}, fy_lim={fy_limit:.1e}). "
            "Standard ASM transfer function will suffer from chirp aliasing."
        )
    else:
        # Nyquist exceeds limit, but 99% of field energy is within limit
        status = ResultStatus.PASS
        interp = (
            f"Grid Nyquist exceeds Matsushima limit, but field 99% energy "
            f"is safely contained within the admissible band."
        )

    return ReportItem(
        id="asm.admissible_band",
        title="ASM admissible band (Matsushima)",
        category="criteria",
        assessment_type=AssessmentType.FORMAL_CRITERION,
        applicable_methods=["asm"],
        value=value,
        status=status,
        unit="1/m",
        formula="f_limit = 1 / (λ √(1 + 4 z² / S²))",
        threshold=f"fx_limit={fx_limit:.2e}, fy_limit={fy_limit:.2e}",
        threshold_provenance=ThresholdProvenance.LITERATURE,
        source="Matsushima & Shimobaba, Opt. Express 17, 19662 (2009)",
        interpretation=interp,
        recommended_action=(
            "Enable band-limited angular spectrum (bandlimit=True) or refine grid / pad."
            if status == ResultStatus.FAIL
            else None
        ),
    )
