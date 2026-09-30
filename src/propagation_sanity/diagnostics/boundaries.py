"""Spatial boundary diagnostics.

Evaluates field containment at the computational window boundaries and
previews diffracted field geometric expansion.
"""

from __future__ import annotations

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


def boundary_energy(
    field: SampledField,
    edge_fraction: float = 0.05,
) -> ReportItem:
    """Spatial boundary energy diagnostic.

    Computes the fraction of field intensity in the outer
    ``edge_fraction`` strip of the spatial domain.

    Parameters
    ----------
    field : SampledField
        Input field.
    edge_fraction : float
        Fraction of each axis defining the edge strip (default 5%).
    """
    grid = field.grid
    intensity = field.intensity
    total_energy = intensity.sum()

    if total_energy == 0:
        return ReportItem(
            id="spatial.boundary_energy",
            title="Boundary energy",
            category="diagnostics",
            assessment_type=AssessmentType.DIAGNOSTIC,
            value=0.0,
            status=ResultStatus.INFO,
            interpretation="Zero total energy.",
        )

    # Compute edge mask: outer edge_fraction on each side
    nx_edge = max(1, int(grid.nx * edge_fraction))
    ny_edge = max(1, int(grid.ny * edge_fraction))

    mask = np.zeros((grid.ny, grid.nx), dtype=bool)
    mask[:ny_edge, :] = True    # top
    mask[-ny_edge:, :] = True   # bottom
    mask[:, :nx_edge] = True    # left
    mask[:, -nx_edge:] = True   # right

    eta_boundary = float(intensity[mask].sum() / total_energy)

    risk = ""
    if eta_boundary > 0.01:
        risk = (
            "Field has significant energy near the computation-domain boundary. "
            "Consider enlarging the physical domain."
        )
    else:
        risk = "Field energy is well-contained within the computation domain."

    return ReportItem(
        id="spatial.boundary_energy",
        title="Boundary energy",
        category="diagnostics",
        assessment_type=AssessmentType.DIAGNOSTIC,
        value=eta_boundary,
        status=ResultStatus.INFO,
        unit="fraction",
        formula=f"η_boundary (edge strip = {edge_fraction*100:.0f}% per side)",
        threshold=None,
        threshold_provenance=ThresholdProvenance.PROJECT_DEFAULT,
        source="project heuristic; cf. Zemax POP guard-band guidance",
        interpretation=risk,
        recommended_action="Run physical-domain convergence." if eta_boundary > 0.01 else None,
    )


def paraxial_fov_preview(
    grid: Grid,
    wave: Wave,
    z: float,
) -> ReportItem:
    """Paraxial field-of-view (FOV) expansion preview (f_safe).

    Estimates whether diffracted spectral components may exceed the
    computation window using the paraxial relation x ≈ λ z f.

    Parameters
    ----------
    grid : Grid
        Computation grid.
    wave : Wave
        Wave parameters.
    z : float
        Propagation distance (m).
    """
    lam = wave.wavelength_medium

    # f_safe: max frequency whose diffracted position stays within L/2
    f_safe_x = grid.Lx / (2 * lam * abs(z)) if z != 0 else float("inf")
    f_safe_y = grid.Ly / (2 * lam * abs(z)) if z != 0 else float("inf")

    ratio_x = f_safe_x / grid.nyquist_x if grid.nyquist_x > 0 else float("inf")
    ratio_y = f_safe_y / grid.nyquist_y if grid.nyquist_y > 0 else float("inf")

    value = {
        "f_safe_x": f_safe_x,
        "f_safe_y": f_safe_y,
        "nyquist_x": grid.nyquist_x,
        "nyquist_y": grid.nyquist_y,
        "ratio_x": ratio_x,
        "ratio_y": ratio_y,
        "z": z,
    }

    if min(ratio_x, ratio_y) > 1.0:
        interp = (
            "All propagating frequencies stay within the computation window "
            "(paraxial estimate)."
        )
    else:
        interp = (
            f"Frequencies above f_safe may diffract beyond the window. "
            f"f_safe/f_Nyquist = ({ratio_x:.2f}, {ratio_y:.2f}). "
            "This is a paraxial estimate and does not replace convergence."
        )

    return ReportItem(
        id="spatial.paraxial_fov",
        title="Paraxial FOV",
        category="diagnostics",
        assessment_type=AssessmentType.DIAGNOSTIC,
        value=value,
        status=ResultStatus.INFO,
        formula="f_safe = L / (2 λ z)",
        assumptions="Paraxial; does not account for full field support or interference",
        source="Paraxial diffraction relation x ≈ λ z f",
        interpretation=interp,
        recommended_action="Cannot replace convergence experiments.",
    )
