"""Convergence experiment engines.

Provides independent numerical stability experiments:
- Resolution convergence: refine spatial sampling with fixed physical window
- Physical-domain convergence: expand computational window with fixed sampling
- Algorithmic-padding convergence: vary FFT zero-padding to assess boundary wrap-around
"""

from __future__ import annotations

from typing import List, Optional, Sequence

import numpy as np

from propagation_sanity.core.grid import Grid
from propagation_sanity.core.field import SampledField, FieldSource
from propagation_sanity.core.wave import Wave
from propagation_sanity.core.roi import ROI
from propagation_sanity.core.propagation_config import PropagationConfig
from propagation_sanity.core.metrics import (
    intensity_relative_error,
    complex_field_relative_error,
)
from propagation_sanity.core.report import (
    ReportItem,
    AssessmentType,
    ThresholdProvenance,
    ResultStatus,
)
from propagation_sanity.adapters.waveprop_adapter import WavepropAdapter


def _make_adapter(config: PropagationConfig):
    """Instantiate the appropriate adapter."""
    if config.backend == "waveprop":
        return WavepropAdapter()
    elif config.backend == "torchoptics":
        from propagation_sanity.adapters.torchoptics_adapter import TorchOpticsAdapter
        return TorchOpticsAdapter()
    raise ValueError(f"Unknown backend: {config.backend}")


def resolution_convergence(
    source: FieldSource,
    base_grid: Grid,
    wave: Wave,
    z: float,
    config: PropagationConfig,
    factors: Sequence[int] = (1, 2, 4),
    tolerance: float = 0.01,
    roi: Optional[ROI] = None,
) -> ReportItem:
    """Resolution convergence experiment.

    Fixes physical domain L, decreases Δx by successive *factors*.
    Each run regenerates the field from the FieldSource.

    Parameters
    ----------
    source : FieldSource
        Re-sampleable field source.
    base_grid : Grid
        Starting grid.
    wave : Wave
        Wave parameters.
    z : float
        Propagation distance.
    config : PropagationConfig
        Propagation settings.
    factors : sequence of int
        Resolution multipliers (e.g. 1, 2, 4).
    tolerance : float
        Convergence tolerance for intensity relative error.
    roi : ROI, optional
        Comparison region.
    """
    adapter = _make_adapter(config)
    results = []
    errors = []

    for factor in factors:
        grid = base_grid.with_resolution(factor)
        field = source.sample(grid)
        result = adapter.propagate(field, wave, z, config)
        results.append(result)

    # Compare successive pairs at common ROI
    for i in range(1, len(results)):
        r_prev = results[i - 1]
        r_curr = results[i]

        # Determine common ROI
        compare_roi = roi
        if compare_roi is None:
            compare_roi = ROI.common(r_prev.output_grid, r_curr.output_grid)

        # Interpolate to common grid for comparison
        from propagation_sanity.core.coordinates import interpolate_field

        # Use the finer grid as the comparison grid
        finer_grid = r_curr.output_grid
        coarser_data, _ = interpolate_field(
            r_prev.field.data, r_prev.output_grid, finer_grid
        )
        coarser_on_fine = SampledField(data=coarser_data, grid=finer_grid)

        err = intensity_relative_error(coarser_on_fine, r_curr.field, compare_roi)
        errors.append({
            "factor_from": int(factors[i - 1]),
            "factor_to": int(factors[i]),
            "intensity_relative_error": err,
        })

    # Determine convergence status
    final_err = errors[-1]["intensity_relative_error"] if errors else float("inf")
    if final_err <= tolerance:
        status = ResultStatus.CONVERGED_AT_TOLERANCE
        interp = (
            f"Resolution convergence achieved: final error {final_err:.2e} "
            f"≤ tolerance {tolerance:.2e}."
        )
    else:
        status = ResultStatus.NOT_CONVERGED
        interp = (
            f"Resolution convergence NOT achieved: final error {final_err:.2e} "
            f"> tolerance {tolerance:.2e}. "
            "Consider finer resolution."
        )

    return ReportItem(
        id="convergence.resolution",
        title="Input resolution",
        category="convergence",
        assessment_type=AssessmentType.CONVERGENCE,
        value={"errors": errors, "factors": list(factors), "tolerance": tolerance},
        status=status,
        formula="Fix L, decrease Δx → regenerate from FieldSource → compare",
        threshold=tolerance,
        threshold_provenance=ThresholdProvenance.USER_DEFINED,
        source="numerical analysis",
        interpretation=interp,
    )


def domain_convergence(
    source: FieldSource,
    base_grid: Grid,
    wave: Wave,
    z: float,
    config: PropagationConfig,
    factors: Sequence[int] = (1, 2, 4),
    tolerance: float = 0.01,
    roi: Optional[ROI] = None,
) -> ReportItem:
    """Physical-domain convergence experiment.

    Fixes Δx, increases L by successive *factors*.
    For non-compact fields, regenerates from FieldSource.

    Parameters
    ----------
    source : FieldSource
        Re-sampleable field source.
    base_grid : Grid
        Starting grid.
    wave : Wave
        Wave parameters.
    z : float
        Propagation distance.
    config : PropagationConfig
        Propagation settings.
    factors : sequence of int
        Domain multipliers.
    tolerance : float
        Convergence tolerance.
    roi : ROI, optional
        Comparison region. If None, uses the base grid's central region.
    """
    adapter = _make_adapter(config)
    results = []
    errors = []

    # Default ROI: central region of the base grid
    if roi is None:
        roi = ROI.from_grid_center(base_grid, fraction=0.5)

    for factor in factors:
        grid = base_grid.with_domain(factor)
        field = source.sample(grid)
        result = adapter.propagate(field, wave, z, config)
        results.append(result)

    # Compare successive pairs
    for i in range(1, len(results)):
        r_prev = results[i - 1]
        r_curr = results[i]

        from propagation_sanity.core.coordinates import interpolate_field

        finer_grid = r_curr.output_grid
        coarser_data, _ = interpolate_field(
            r_prev.field.data, r_prev.output_grid, finer_grid
        )
        coarser_on_fine = SampledField(data=coarser_data, grid=finer_grid)

        err = intensity_relative_error(coarser_on_fine, r_curr.field, roi)
        errors.append({
            "factor_from": int(factors[i - 1]),
            "factor_to": int(factors[i]),
            "intensity_relative_error": err,
        })

    final_err = errors[-1]["intensity_relative_error"] if errors else float("inf")
    if final_err <= tolerance:
        status = ResultStatus.CONVERGED_AT_TOLERANCE
        interp = (
            f"Domain convergence achieved: final error {final_err:.2e} "
            f"≤ tolerance {tolerance:.2e}."
        )
    else:
        status = ResultStatus.NOT_CONVERGED
        interp = (
            f"Domain convergence NOT achieved: final error {final_err:.2e} "
            f"> tolerance {tolerance:.2e}. "
            "Consider larger physical domain."
        )

    return ReportItem(
        id="convergence.domain",
        title="Physical domain",
        category="convergence",
        assessment_type=AssessmentType.CONVERGENCE,
        value={"errors": errors, "factors": list(factors), "tolerance": tolerance},
        status=status,
        formula="Fix Δx, increase L → regenerate from FieldSource → compare",
        threshold=tolerance,
        threshold_provenance=ThresholdProvenance.USER_DEFINED,
        source="numerical analysis",
        interpretation=interp,
    )


def padding_convergence(
    field: SampledField,
    wave: Wave,
    z: float,
    config: PropagationConfig,
    padding_factors: Sequence[float] = (1.0, 2.0, 4.0),
    tolerance: float = 0.01,
    roi: Optional[ROI] = None,
) -> ReportItem:
    """Algorithmic padding convergence experiment.

    Same physical problem; varies internal FFT padding factor.

    Note: waveprop's ``pad=True`` doubles the array (2× padding).
    This function tests with/without padding.  For more granular
    control, manual padding of the input array may be needed.
    """
    from propagation_sanity.core.propagation_config import PropagationConfig as PC

    adapter = _make_adapter(config)
    results = []
    errors = []

    for pad_factor in padding_factors:
        # Create config variant with different padding
        cfg = PropagationConfig(
            method=config.method,
            backend=config.backend,
            padding=pad_factor,
            bandlimit=config.bandlimit,
            evanescent_policy=config.evanescent_policy,
            interpolation=config.interpolation,
            extra=config.extra,
        )
        result = adapter.propagate(field, wave, z, cfg)
        results.append(result)

    if roi is None:
        roi = ROI.from_grid_center(field.grid, fraction=0.5)

    for i in range(1, len(results)):
        r_prev = results[i - 1]
        r_curr = results[i]

        # Both should be on the same grid (ASM preserves grid)
        err = intensity_relative_error(r_prev.field, r_curr.field, roi)
        errors.append({
            "padding_from": float(padding_factors[i - 1]),
            "padding_to": float(padding_factors[i]),
            "intensity_relative_error": err,
        })

    final_err = errors[-1]["intensity_relative_error"] if errors else float("inf")
    if final_err <= tolerance:
        status = ResultStatus.CONVERGED_AT_TOLERANCE
        interp = (
            f"Padding convergence achieved: final error {final_err:.2e} "
            f"≤ tolerance {tolerance:.2e}."
        )
    else:
        status = ResultStatus.NOT_CONVERGED
        interp = (
            f"Padding convergence NOT achieved: final error {final_err:.2e} "
            f"> tolerance {tolerance:.2e}."
        )

    return ReportItem(
        id="convergence.padding",
        title="FFT padding",
        category="convergence",
        assessment_type=AssessmentType.CONVERGENCE,
        applicable_methods=["asm", "fresnel"],
        value={"errors": errors, "padding_factors": list(padding_factors), "tolerance": tolerance},
        status=status,
        formula="Same problem, vary FFT padding factor → compare",
        threshold=tolerance,
        threshold_provenance=ThresholdProvenance.USER_DEFINED,
        source="FFT circular convolution theory",
        interpretation=interp,
    )
