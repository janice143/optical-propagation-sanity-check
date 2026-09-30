"""Spectral diagnostics for input field analysis.

Provides frequency-domain evaluation including high-frequency edge energy,
effective energy support quantiles, and evanescent sub-wavelength energy content.
"""

from __future__ import annotations

from typing import Optional, Dict, Any, List

import numpy as np

from propagation_sanity.core.grid import Grid
from propagation_sanity.core.field import SampledField
from propagation_sanity.core.wave import Wave
from propagation_sanity.core.report import (
    ReportItem,
    AssessmentType,
    ThresholdProvenance,
    ResultStatus,
)


def compute_spectrum(field: SampledField) -> np.ndarray:
    """Compute 2-D power spectrum |FFT(U)|²."""
    A = np.fft.fftshift(np.fft.fft2(field.data))
    return np.abs(A) ** 2


def spectral_edge_energy(
    field: SampledField,
    alpha: float = 0.8,
) -> ReportItem:
    """Input spectral edge energy diagnostic.

    Computes the fraction of spectral energy in the outer
    ``(1 - alpha)`` band of the Nyquist frequency.

    Parameters
    ----------
    field : SampledField
        Input field to analyse.
    alpha : float
        Fraction of Nyquist that defines the "inner" region.
        Default 0.8 (from original article).
    """
    grid = field.grid
    S = compute_spectrum(field)
    total_energy = S.sum()

    if total_energy == 0:
        return ReportItem(
            id="spectrum.edge_energy",
            title="Spectral edge energy",
            category="diagnostics",
            assessment_type=AssessmentType.DIAGNOSTIC,
            value=0.0,
            status=ResultStatus.INFO,
            unit="fraction",
            formula="η_edge = Σ_{edge} |A|² / Σ |A|²",
            interpretation="Zero total energy — field is identically zero.",
        )

    FX, FY = grid.fxy_meshgrid_shifted()
    edge_mask = (np.abs(FX) > alpha * grid.nyquist_x) | (
        np.abs(FY) > alpha * grid.nyquist_y
    )
    eta_edge = float(S[edge_mask].sum() / total_energy)

    risk = ""
    if eta_edge > 0.05:
        risk = (
            "Significant spectral energy near Nyquist. "
            "The sampled field may suffer from aliasing."
        )
    elif eta_edge > 0.01:
        risk = "Moderate spectral energy near Nyquist."

    return ReportItem(
        id="spectrum.edge_energy",
        title="Spectral edge energy",
        category="diagnostics",
        assessment_type=AssessmentType.DIAGNOSTIC,
        value=eta_edge,
        status=ResultStatus.INFO,
        unit="fraction",
        formula=f"η_edge (α={alpha})",
        assumptions="Only detects spectral crowding, not pre-existing aliasing",
        threshold=None,
        threshold_provenance=ThresholdProvenance.PROJECT_DEFAULT,
        source="project",
        interpretation=risk or "Low spectral energy near Nyquist edge.",
        recommended_action="Run resolution convergence if η_edge is high.",
    )


def effective_bandwidth(
    field: SampledField,
    coverage_levels: Optional[List[float]] = None,
) -> ReportItem:
    """Effective spectrum energy support quantiles.

    Computes radial and per-axis frequency quantiles.
    """
    if coverage_levels is None:
        coverage_levels = [0.95, 0.99, 0.999]

    grid = field.grid
    S = compute_spectrum(field)
    total_energy = S.sum()

    if total_energy == 0:
        return ReportItem(
            id="spectrum.effective_bandwidth",
            title="Effective bandwidth",
            category="diagnostics",
            assessment_type=AssessmentType.DIAGNOSTIC,
            value={"radial": {}, "x": {}, "y": {}},
            status=ResultStatus.INFO,
            interpretation="Zero total energy.",
        )

    FX, FY = grid.fxy_meshgrid_shifted()

    # Radial quantiles
    FR = np.sqrt(FX**2 + FY**2)
    fr_flat = FR.ravel()
    s_flat = S.ravel()
    order = np.argsort(fr_flat)
    fr_sorted = fr_flat[order]
    cumsum = np.cumsum(s_flat[order])
    cumsum /= cumsum[-1]

    radial_quantiles = {}
    for cov in coverage_levels:
        idx = np.searchsorted(cumsum, cov)
        if idx < len(fr_sorted):
            radial_quantiles[f"{cov*100:.1f}%"] = float(fr_sorted[idx])
        else:
            radial_quantiles[f"{cov*100:.1f}%"] = float(fr_sorted[-1])

    # X-axis projected quantiles
    sx = S.sum(axis=0)  # sum over y → function of fx
    fx_1d = np.fft.fftshift(grid.fx_coords())
    abs_fx = np.abs(fx_1d)
    order_x = np.argsort(abs_fx)
    cumsum_x = np.cumsum(sx[order_x])
    cumsum_x /= cumsum_x[-1]
    x_quantiles = {}
    for cov in coverage_levels:
        idx = np.searchsorted(cumsum_x, cov)
        if idx < len(abs_fx):
            x_quantiles[f"{cov*100:.1f}%"] = float(abs_fx[order_x[idx]])
        else:
            x_quantiles[f"{cov*100:.1f}%"] = float(abs_fx[order_x[-1]])

    # Y-axis projected quantiles
    sy = S.sum(axis=1)  # sum over x → function of fy
    fy_1d = np.fft.fftshift(grid.fy_coords())
    abs_fy = np.abs(fy_1d)
    order_y = np.argsort(abs_fy)
    cumsum_y = np.cumsum(sy[order_y])
    cumsum_y /= cumsum_y[-1]
    y_quantiles = {}
    for cov in coverage_levels:
        idx = np.searchsorted(cumsum_y, cov)
        if idx < len(abs_fy):
            y_quantiles[f"{cov*100:.1f}%"] = float(abs_fy[order_y[idx]])
        else:
            y_quantiles[f"{cov*100:.1f}%"] = float(abs_fy[order_y[-1]])

    value = {
        "radial": radial_quantiles,
        "x": x_quantiles,
        "y": y_quantiles,
        "nyquist_x": grid.nyquist_x,
        "nyquist_y": grid.nyquist_y,
    }

    return ReportItem(
        id="spectrum.effective_bandwidth",
        title="Effective bandwidth",
        category="diagnostics",
        assessment_type=AssessmentType.DIAGNOSTIC,
        value=value,
        status=ResultStatus.INFO,
        formula="Energy quantiles of |FFT(U)|² sorted by frequency",
        interpretation="Effective spectral support at various coverage levels.",
    )


def evanescent_diagnostic(
    field: SampledField,
    wave: Wave,
) -> ReportItem:
    """Evanescent sub-wavelength component diagnostic.

    Computes the fraction of spectral energy beyond the
    propagating-wave cutoff ``1/λ``.
    """
    grid = field.grid
    S = compute_spectrum(field)
    total_energy = S.sum()

    if total_energy == 0:
        return ReportItem(
            id="scope.evanescent",
            title="Evanescent energy",
            category="diagnostics",
            assessment_type=AssessmentType.SCOPE_CHECK,
            value=0.0,
            status=ResultStatus.INFO,
            interpretation="Zero total energy.",
        )

    FX, FY = grid.fxy_meshgrid_shifted()
    FR = np.sqrt(FX**2 + FY**2)
    cutoff = wave.freq_cutoff  # 1 / λ_medium
    evanescent_mask = FR > cutoff
    eta_evan = float(S[evanescent_mask].sum() / total_energy)

    status = ResultStatus.INFO
    interp = "Negligible evanescent spectral content."
    if eta_evan > 0.01:
        interp = (
            "Significant sub-wavelength spectral content detected. "
            "Scalar free-space V1 may not be sufficient for this field."
        )
        status = ResultStatus.INFO  # Still INFO — scope check, not FAIL

    return ReportItem(
        id="scope.evanescent",
        title="Evanescent energy",
        category="diagnostics",
        assessment_type=AssessmentType.SCOPE_CHECK,
        value=eta_evan,
        status=status,
        unit="fraction",
        formula="Fraction of |A|² where √(fx²+fy²) > 1/λ",
        source="Wave equation",
        interpretation=interp,
        recommended_action=(
            "Consider vector diffraction or near-field methods "
            "if evanescent content is essential."
            if eta_evan > 0.01
            else None
        ),
    )
