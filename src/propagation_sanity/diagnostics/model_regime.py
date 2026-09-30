"""Propagation-model regime diagnostics.

Evaluates applicability of paraxial approximations, including the Fresnel
phase remainder relative to ASM and the Fresnel number regime indicator.
"""

from __future__ import annotations

from typing import Optional

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
from propagation_sanity.diagnostics.spectrum import compute_spectrum


def fresnel_phase_remainder(
    grid: Grid,
    wave: Wave,
    z: float,
    field: Optional[SampledField] = None,
    energy_coverage: float = 0.99,
) -> ReportItem:
    """Fresnel phase remainder diagnostic.

    Computes the difference between the exact ASM phase and the
    Fresnel (paraxial quadratic) approximation over the active
    spectral region.

    Parameters
    ----------
    grid : Grid
        Computation grid.
    wave : Wave
        Wave parameters.
    z : float
        Propagation distance (m).
    field : SampledField, optional
        If provided, restricts analysis to the field's effective
        spectral support.
    energy_coverage : float
        Energy coverage threshold for effective bandwidth (default 99%).
    """
    lam = wave.wavelength_medium
    FX, FY = grid.fxy_meshgrid_shifted()
    fsq = FX**2 + FY**2
    inv_lam_sq = 1.0 / lam**2

    # Only propagating waves
    prop = fsq < inv_lam_sq

    # ASM phase: 2π z sqrt(1/λ² - fx² - fy²)
    phi_asm = np.zeros_like(fsq)
    phi_asm[prop] = 2 * np.pi * z * np.sqrt(inv_lam_sq - fsq[prop])

    # Fresnel phase: 2π z / λ - π λ z (fx² + fy²)
    phi_fresnel = np.zeros_like(fsq)
    phi_fresnel[prop] = 2 * np.pi * z / lam - np.pi * lam * z * fsq[prop]

    dphi = np.abs(phi_asm - phi_fresnel)

    # If field provided, weight by spectrum
    if field is not None:
        S = compute_spectrum(field)
        # Use spectral region with significant energy
        threshold = energy_coverage * S.max()
        active = S > (1 - energy_coverage) * S.sum() / S.size
        active = active & prop
    else:
        active = prop

    if active.sum() == 0:
        return ReportItem(
            id="model.fresnel_remainder",
            title="Fresnel phase error",
            category="diagnostics",
            assessment_type=AssessmentType.DIAGNOSTIC,
            value=0.0,
            status=ResultStatus.INFO,
            interpretation="No active spectral region.",
        )

    max_dphi = float(dphi[active].max())
    mean_dphi = float(dphi[active].mean())

    value = {
        "max_phase_error_rad": max_dphi,
        "max_phase_error_pi": max_dphi / np.pi,
        "mean_phase_error_rad": mean_dphi,
        "z": z,
    }

    if max_dphi > 1.0:
        interp = (
            f"Maximum Fresnel-approximation phase error is {max_dphi:.2f} rad "
            f"({max_dphi/np.pi:.2f}π). Fresnel propagation may be inaccurate; "
            "consider using ASM."
        )
    else:
        interp = (
            f"Maximum Fresnel-approximation phase error is {max_dphi:.3f} rad. "
            "Fresnel propagation appears valid for this configuration."
        )

    return ReportItem(
        id="model.fresnel_remainder",
        title="Fresnel phase error",
        category="diagnostics",
        assessment_type=AssessmentType.DIAGNOSTIC,
        applicable_methods=["fresnel"],
        value=value,
        status=ResultStatus.INFO,
        unit="rad",
        formula="Δφ = |φ_ASM - φ_Fresnel| over active spectrum",
        threshold=None,
        threshold_provenance=ThresholdProvenance.PROJECT_DEFAULT,
        source="Fourier optics, paraxial expansion",
        interpretation=interp,
        recommended_action=(
            "Prefer ASM or run cross-reference comparison."
            if max_dphi > 1.0
            else None
        ),
    )


def fresnel_number(
    wave: Wave,
    z: float,
    characteristic_size: Optional[float] = None,
) -> ReportItem:
    """Fresnel number regime indicator diagnostic.

    Parameters
    ----------
    wave : Wave
        Wave parameters.
    z : float
        Propagation distance (m).
    characteristic_size : float, optional
        Aperture half-width or beam radius (m).
    """
    if characteristic_size is None or z == 0:
        return ReportItem(
            id="model.fresnel_number",
            title="Fresnel number",
            category="diagnostics",
            assessment_type=AssessmentType.DIAGNOSTIC,
            value=None,
            status=ResultStatus.NOT_APPLICABLE,
            interpretation=(
                "Characteristic size not provided or z=0."
                if characteristic_size is None
                else "z=0 — propagation distance is zero."
            ),
        )

    lam = wave.wavelength_medium
    a = characteristic_size
    nf = a**2 / (lam * abs(z))

    if nf > 10:
        regime = "Near field (Fresnel regime)"
    elif nf > 1:
        regime = "Fresnel regime"
    elif nf > 0.1:
        regime = "Transition to Fraunhofer"
    else:
        regime = "Fraunhofer (far field)"

    return ReportItem(
        id="model.fresnel_number",
        title="Fresnel number",
        category="diagnostics",
        assessment_type=AssessmentType.DIAGNOSTIC,
        value=nf,
        status=ResultStatus.INFO,
        formula="N_F = a² / (λ z)",
        source="Standard Fourier optics",
        interpretation=f"N_F = {nf:.4f} — {regime}.",
        recommended_action="Use to select propagation regime; not a standalone check.",
    )
