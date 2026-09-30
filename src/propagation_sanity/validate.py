"""Top-level validation API.

Provides the ``validate()`` function that runs all applicable checks
on a simulation contract and returns a structured ``ValidationReport``.
"""

from __future__ import annotations

from typing import Optional

from propagation_sanity.core.simulation import SimulationContract
from propagation_sanity.core.report import (
    ValidationReport,
    ReportItem,
    AssessmentType,
    ResultStatus,
)
from propagation_sanity.diagnostics import (
    spectral_edge_energy,
    effective_bandwidth,
    evanescent_diagnostic,
    boundary_energy,
    paraxial_fov_preview,
    asm_phase_step,
    fresnel_phase_remainder,
    fresnel_number,
)
from propagation_sanity.core.propagation_config import PropagationMethod


def validate(
    contract: SimulationContract,
    run_convergence: bool = False,
    convergence_tolerance: float = 0.01,
    spectral_edge_alpha: float = 0.8,
    boundary_edge_fraction: float = 0.05,
) -> ValidationReport:
    """Run all applicable validation checks.

    Parameters
    ----------
    contract : SimulationContract
        Complete simulation description.
    run_convergence : bool
        Whether to run convergence experiments (requires propagator).
    convergence_tolerance : float
        Tolerance for convergence experiments.
    spectral_edge_alpha : float
        Alpha parameter for spectral edge energy diagnostic.
    boundary_edge_fraction : float
        Edge fraction for spatial boundary diagnostic.

    Returns
    -------
    ValidationReport
        Structured validation report with all results.
    """
    report = ValidationReport(metadata=contract.derived_report())

    # ---- Layer 0: Derived quantities (always) ----
    grid = contract.grid
    grid_report = grid.derived_report()
    for key, val in grid_report.items():
        unit = _grid_unit(key)
        report.add_item(ReportItem(
            id=f"grid.{key}",
            title=key,
            category="grid",
            assessment_type=AssessmentType.DERIVED,
            value=val,
            status=ResultStatus.INFO,
            unit=unit,
        ))

    # ---- Layer 1: Diagnostics ----
    field = contract.field
    wave = contract.wave

    if field is not None:
        # Spectral edge energy
        report.add_item(spectral_edge_energy(field, alpha=spectral_edge_alpha))

        # Effective bandwidth
        report.add_item(effective_bandwidth(field))

        # Spatial boundary energy
        report.add_item(boundary_energy(field, edge_fraction=boundary_edge_fraction))

        # Evanescent diagnostic
        report.add_item(evanescent_diagnostic(field, wave))

    # Paraxial FOV (for each z)
    for z_val in contract.z_values:
        item = paraxial_fov_preview(grid, wave, z_val)
        if len(contract.z_values) > 1:
            item.id = f"spatial.paraxial_fov_z{z_val}"
            item.title = f"Paraxial FOV (z={z_val})"
        report.add_item(item)

    # ASM phase step and Matsushima admissible band (ASM only)
    method = contract.propagation_config.method
    if method == PropagationMethod.ASM:
        from propagation_sanity.criteria.matsushima import asm_admissible_band_check
        padded = contract.propagation_config.padding > 1.0
        bandlimit = contract.propagation_config.bandlimit
        for z_val in contract.z_values:
            item = asm_phase_step(grid, wave, z_val)
            crit_item = asm_admissible_band_check(
                grid=grid,
                wave=wave,
                z=z_val,
                field=field,
                padded=padded,
                bandlimit_enabled=bandlimit,
            )
            if len(contract.z_values) > 1:
                item.id = f"asm.phase_step_z{z_val}"
                item.title = f"ASM phase step (z={z_val})"
                crit_item.id = f"asm.admissible_band_z{z_val}"
                crit_item.title = f"ASM admissible band (z={z_val})"
            report.add_item(item)
            report.add_item(crit_item)

    # Fresnel phase remainder (Fresnel method, or as comparison)
    if method in (PropagationMethod.FRESNEL, PropagationMethod.ASM):
        for z_val in contract.z_values:
            item = fresnel_phase_remainder(grid, wave, z_val, field=field)
            if len(contract.z_values) > 1:
                item.id = f"model.fresnel_remainder_z{z_val}"
                item.title = f"Fresnel phase error (z={z_val})"
            report.add_item(item)

    # Fresnel number
    if contract.characteristic_size is not None:
        for z_val in contract.z_values:
            item = fresnel_number(wave, z_val, contract.characteristic_size)
            if len(contract.z_values) > 1:
                item.id = f"model.fresnel_number_z{z_val}"
                item.title = f"Fresnel number (z={z_val})"
            report.add_item(item)

    # Input feature pixels
    if contract.characteristic_size is not None:
        feat_px_x = contract.characteristic_size / grid.dx
        feat_px_y = contract.characteristic_size / grid.dy
        report.add_item(ReportItem(
            id="input.feature_pixels",
            title="Feature pixels",
            category="diagnostics",
            assessment_type=AssessmentType.DIAGNOSTIC,
            value={"x": feat_px_x, "y": feat_px_y},
            status=ResultStatus.INFO,
            formula="N_feat = characteristic_size / Δx",
            interpretation=(
                f"Characteristic feature spans {feat_px_x:.1f} × {feat_px_y:.1f} pixels."
            ),
            recommended_action="Use resolution convergence for definitive assessment.",
        ))

    # ---- Layer 3: Convergence (optional) ----
    if run_convergence:
        _run_convergence(contract, report, convergence_tolerance)
    else:
        # Mark convergence as unverified
        if not contract.resolution_convergence_available:
            report.add_item(ReportItem(
                id="convergence.resolution",
                title="Input resolution",
                category="convergence",
                assessment_type=AssessmentType.CONVERGENCE,
                value=None,
                status=ResultStatus.UNVERIFIED,
                interpretation=(
                    "Resolution convergence unavailable: "
                    "no FieldSource provided (only raw array)."
                ),
            ))
        else:
            report.add_item(ReportItem(
                id="convergence.resolution",
                title="Input resolution",
                category="convergence",
                assessment_type=AssessmentType.CONVERGENCE,
                value=None,
                status=ResultStatus.UNVERIFIED,
                interpretation="Convergence experiments not requested.",
                recommended_action="Call validate(..., run_convergence=True).",
            ))

    return report


def _run_convergence(
    contract: SimulationContract,
    report: ValidationReport,
    tolerance: float,
) -> None:
    """Run convergence experiments and add results to report."""
    from propagation_sanity.convergence.engine import (
        resolution_convergence,
        domain_convergence,
        padding_convergence,
    )

    z_val = contract.z_values[0]  # Use first z for convergence

    # Resolution convergence (requires FieldSource)
    if contract.source is not None:
        report.add_item(resolution_convergence(
            source=contract.source,
            base_grid=contract.grid,
            wave=contract.wave,
            z=z_val,
            config=contract.propagation_config,
            tolerance=tolerance,
            roi=contract.roi,
        ))
    else:
        report.add_item(ReportItem(
            id="convergence.resolution",
            title="Input resolution",
            category="convergence",
            assessment_type=AssessmentType.CONVERGENCE,
            value=None,
            status=ResultStatus.UNVERIFIED,
            interpretation=(
                "The validator only received an already sampled field. "
                "A finer physical sampling cannot be reconstructed "
                "reliably from the existing array."
            ),
        ))

    # Domain convergence
    if contract.source is not None:
        report.add_item(domain_convergence(
            source=contract.source,
            base_grid=contract.grid,
            wave=contract.wave,
            z=z_val,
            config=contract.propagation_config,
            tolerance=tolerance,
            roi=contract.roi,
        ))

    # Padding convergence
    if contract.field is not None:
        report.add_item(padding_convergence(
            field=contract.field,
            wave=contract.wave,
            z=z_val,
            config=contract.propagation_config,
            tolerance=tolerance,
            roi=contract.roi,
        ))


def _grid_unit(key: str) -> Optional[str]:
    """Return SI unit for a grid-derived key."""
    units = {
        "dx": "m", "dy": "m",
        "Lx": "m", "Ly": "m",
        "dfx": "1/m", "dfy": "1/m",
        "nyquist_x": "1/m", "nyquist_y": "1/m",
    }
    return units.get(key)
