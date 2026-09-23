"""The six evidence-producing checks and the main ``sanity_check`` API."""

from __future__ import annotations

import numpy as np
from scipy.interpolate import RegularGridInterpolator

from .grids import fft2c, frequency_grid
from .propagators import ASM_MODEL
from .types import (
    CheckResult,
    GridSpec,
    PropagationModel,
    PropagationResult,
    PropagationSpec,
    SanityReport,
    SanityThresholds,
)

STATUS_ORDER = {"INFO": 0, "PASS": 1, "SKIP": 2, "WARN": 3, "FAIL": 4}
CHECK_NAMES = (
    "Grid summary",
    "Input sampling",
    "Window / FOV",
    "Frequency sampling",
    "Propagator sampling",
    "Model validity",
)


def _worst_status(*statuses: str) -> str:
    return max(statuses, key=lambda status: STATUS_ORDER[status])


def _threshold_status(value, warn, fail, *, higher_is_worse=True) -> str:
    if not np.isfinite(value):
        return "FAIL"
    if higher_is_worse:
        return "FAIL" if value >= fail else "WARN" if value >= warn else "PASS"
    return "FAIL" if value < fail else "WARN" if value < warn else "PASS"


def _validate_inputs(field, grid, propagation) -> np.ndarray:
    field = np.asarray(field)
    if field.ndim != 2:
        raise ValueError("U0 must be a two-dimensional array")
    if field.size == 0 or not np.any(np.abs(field) > 0):
        raise ValueError("U0 must contain non-zero field values")
    if not np.all(np.isfinite(field)):
        raise ValueError("U0 contains non-finite values")
    if grid.dx <= 0 or grid.resolved_dy <= 0:
        raise ValueError("dx and dy must be positive")
    if propagation.wavelength <= 0:
        raise ValueError("wavelength must be positive")
    if propagation.z == 0 or not np.isfinite(propagation.z):
        raise ValueError("z must be finite and non-zero")
    return field.astype(np.complex128, copy=False)


def _energy_ratio(values: np.ndarray, mask: np.ndarray) -> float:
    energy = np.abs(values) ** 2
    total = energy.sum()
    return float(energy[mask].sum() / total) if total > 0 else 0.0


def _edge_mask(shape: tuple[int, int], fraction: float) -> np.ndarray:
    ny, nx = shape
    by = max(1, int(np.ceil(ny * fraction)))
    bx = max(1, int(np.ceil(nx * fraction)))
    mask = np.zeros(shape, dtype=bool)
    mask[:by, :] = mask[-by:, :] = True
    mask[:, :bx] = mask[:, -bx:] = True
    return mask


def _axis_energy_limit(axis, marginal_energy, fraction) -> float:
    order = np.argsort(np.abs(axis))
    cumulative = np.cumsum(marginal_energy[order])
    if cumulative[-1] <= 0:
        return 0.0
    index = np.searchsorted(cumulative, fraction * cumulative[-1], side="left")
    return float(abs(axis[order[min(index, len(order) - 1)]]))


def _spectrum_context(field, grid, thresholds):
    spectrum = fft2c(field)
    (fx_grid, fy_grid), fx, fy = frequency_grid(field.shape, grid)
    energy = np.abs(spectrum) ** 2
    active_fx = _axis_energy_limit(
        fx, energy.sum(axis=0), thresholds.spectrum_energy_fraction
    )
    active_fy = _axis_energy_limit(
        fy, energy.sum(axis=1), thresholds.spectrum_energy_fraction
    )
    active = (np.abs(fx_grid) <= active_fx) & (np.abs(fy_grid) <= active_fy)
    return spectrum, fx_grid, fy_grid, fx, fy, active, active_fx, active_fy


def _grid_summary(field, grid, model_result) -> CheckResult:
    ny, nx = field.shape
    output_dx = float(np.median(np.diff(model_result.x)))
    output_dy = float(np.median(np.diff(model_result.y)))
    return CheckResult(
        "Grid summary",
        "INFO",
        {
            "Nx": nx,
            "Ny": ny,
            "dx_m": grid.dx,
            "dy_m": grid.resolved_dy,
            "Lx_m": nx * grid.dx,
            "Ly_m": ny * grid.resolved_dy,
            "dfx_per_m": 1 / (nx * grid.dx),
            "dfy_per_m": 1 / (ny * grid.resolved_dy),
            "fx_nyquist_per_m": 1 / (2 * grid.dx),
            "fy_nyquist_per_m": 1 / (2 * grid.resolved_dy),
            "output_dx_m": output_dx,
            "output_dy_m": output_dy,
            "output_Lx_m": float(np.ptp(model_result.x) + output_dx),
            "output_Ly_m": float(np.ptp(model_result.y) + output_dy),
        },
        "Grid quantities are descriptive, not a validity verdict.",
    )


def _input_sampling(field, grid, thresholds, context) -> CheckResult:
    spectrum, fx_grid, fy_grid, _, _, _, active_fx, active_fy = context
    fnx = 1 / (2 * grid.dx)
    fny = 1 / (2 * grid.resolved_dy)
    high_mask = (np.abs(fx_grid) >= 0.8 * fnx) | (np.abs(fy_grid) >= 0.8 * fny)
    high_energy = _energy_ratio(spectrum, high_mask)
    amplitude = np.abs(field)
    support = amplitude >= thresholds.amplitude_mask_fraction * amplitude.max()
    phase_steps = []
    pair_x = support[:, 1:] & support[:, :-1]
    pair_y = support[1:, :] & support[:-1, :]
    if np.any(pair_x):
        phase_steps.append(np.max(np.abs(np.angle(field[:, 1:] * np.conj(field[:, :-1]))[pair_x])))
    if np.any(pair_y):
        phase_steps.append(np.max(np.abs(np.angle(field[1:, :] * np.conj(field[:-1, :]))[pair_y])))
    phase_step_pi = float(max(phase_steps, default=0.0) / np.pi)
    status = _worst_status(
        _threshold_status(high_energy, thresholds.spectral_edge_warn, thresholds.spectral_edge_fail),
        _threshold_status(phase_step_pi, thresholds.input_phase_warn_pi, thresholds.input_phase_fail_pi),
    )
    metrics = {
        "high_frequency_energy_ratio": high_energy,
        "max_input_phase_step_over_pi": phase_step_pi,
        "active_fx_per_m": active_fx,
        "active_fy_per_m": active_fy,
        "active_fx_over_nyquist": active_fx / fnx,
        "active_fy_over_nyquist": active_fy / fny,
    }
    if grid.min_feature_size is not None:
        samples = min(grid.min_feature_size / grid.dx, grid.min_feature_size / grid.resolved_dy)
        metrics["samples_per_min_feature"] = samples
        status = _worst_status(status, "FAIL" if samples < 2 else "WARN" if samples < 4 else "PASS")
    recommendations = []
    if status in ("WARN", "FAIL"):
        recommendations.append("Reduce dx/dy or construct the input on a finer physical grid; increasing dx is not a remedy.")
    return CheckResult(
        "Input sampling",
        status,
        metrics,
        "The checker can expose danger in the sampled array but cannot recover pre-sampling aliasing.",
        recommendations,
    )


def _window_check(field, grid, propagation, model, thresholds):
    input_edge = _energy_ratio(field, _edge_mask(field.shape, thresholds.edge_fraction))
    result = model.propagate(field, grid, propagation)
    if result.field.ndim != 2 or len(result.x) != result.field.shape[1] or len(result.y) != result.field.shape[0]:
        raise ValueError("propagator result field and coordinate axes have inconsistent shapes")
    output_edge = _energy_ratio(result.field, _edge_mask(result.field.shape, thresholds.edge_fraction))
    status = _worst_status(
        _threshold_status(input_edge, thresholds.edge_energy_warn, thresholds.edge_energy_fail),
        _threshold_status(output_edge, thresholds.edge_energy_warn, thresholds.edge_energy_fail),
    )
    recommendations = []
    if status in ("WARN", "FAIL"):
        recommendations.extend(
            [
                "Use a padding-enabled propagator or a larger N at fixed dx/dy.",
                "If the model already pads, enlarge the physical field of view.",
            ]
        )
    return (
        CheckResult(
            "Window / FOV",
            status,
            {"input_edge_energy_ratio": input_edge, "output_edge_energy_ratio": output_edge},
            "Edge-energy comparison between input and propagated output; the model owns its padding policy.",
            recommendations,
        ),
        result,
    )


def _half_max_width_samples(field) -> float:
    target_y, target_x = 2 * field.shape[0], 2 * field.shape[1]
    pad_y, pad_x = target_y - field.shape[0], target_x - field.shape[1]
    padded = np.pad(
        field,
        (
            (pad_y // 2, pad_y - pad_y // 2),
            (pad_x // 2, pad_x - pad_x // 2),
        ),
    )
    spectrum = np.abs(fft2c(padded)) ** 2
    cy, cx = np.unravel_index(np.argmax(spectrum), spectrum.shape)

    def width(profile) -> float:
        indices = np.flatnonzero(profile >= 0.5 * profile.max())
        return float((indices[-1] - indices[0] + 1) / 2) if len(indices) else 0.0

    return min(width(spectrum[cy]), width(spectrum[:, cx]))


def _frequency_sampling(field, grid, thresholds, window_status) -> CheckResult:
    samples = _half_max_width_samples(field)
    status = _threshold_status(
        samples,
        thresholds.min_frequency_samples_warn,
        thresholds.min_frequency_samples_fail,
        higher_is_worse=False,
    )
    reason = "A 2x zero-padded FFT estimates samples across the narrowest half-power spectral feature."
    if window_status in ("WARN", "FAIL") and status == "PASS":
        status = "WARN"
        reason += " The Window/FOV check also fired, so this evidence is not independent."
    ny, nx = field.shape
    return CheckResult(
        "Frequency sampling",
        status,
        {
            "dfx_per_m": 1 / (nx * grid.dx),
            "dfy_per_m": 1 / (ny * grid.resolved_dy),
            "min_half_power_feature_samples": samples,
        },
        reason,
        ["Increase N at fixed dx/dy when the spectrum is too coarsely sampled."] if status in ("WARN", "FAIL") else [],
    )


def _propagator_sampling(model, propagation, thresholds, context) -> CheckResult:
    if model.transfer_phase is None:
        return CheckResult(
            "Propagator sampling",
            "SKIP",
            reason="No analytic transfer-phase hook was supplied for this model.",
            recommendations=["Provide transfer_phase(FX, FY, propagation) to enable this check."],
        )
    _, fx_grid, fy_grid, _, _, active, _, _ = context
    phase = model.transfer_phase(fx_grid, fy_grid, propagation)
    steps = []
    active_x = active[:, 1:] & active[:, :-1]
    active_y = active[1:, :] & active[:-1, :]
    if np.any(active_x):
        steps.append(np.max(np.abs(np.diff(phase, axis=1)[active_x])))
    if np.any(active_y):
        steps.append(np.max(np.abs(np.diff(phase, axis=0)[active_y])))
    ratio = float(max(steps, default=0.0) / np.pi)
    status = _threshold_status(ratio, thresholds.propagator_phase_warn_pi, thresholds.propagator_phase_fail_pi)
    return CheckResult(
        "Propagator sampling",
        status,
        {"max_active_phase_step_over_pi": ratio},
        "Analytic, unwrapped transfer-phase steps over the field's active spectrum.",
        ["Increase N at fixed dx/dy, shorten z, or use a defensible band limit."] if status in ("WARN", "FAIL") else [],
    )


def _resample_result(result: PropagationResult, x_target, y_target) -> np.ndarray:
    points = np.stack(np.meshgrid(y_target, x_target, indexing="ij"), axis=-1)
    real = RegularGridInterpolator((result.y, result.x), result.field.real, bounds_error=False, fill_value=np.nan)
    imag = RegularGridInterpolator((result.y, result.x), result.field.imag, bounds_error=False, fill_value=np.nan)
    return real(points) + 1j * imag(points)


def field_errors(reference: np.ndarray, candidate: np.ndarray) -> tuple[float, float]:
    """Return peak-normalized intensity NRMSE and phase-aligned complex NRMSE."""

    valid = np.isfinite(reference) & np.isfinite(candidate)
    if not np.any(valid):
        return float("inf"), float("inf")
    ref = reference[valid]
    cand = candidate[valid]
    i_ref, i_cand = np.abs(ref) ** 2, np.abs(cand) ** 2
    if i_ref.max() > 0:
        i_ref = i_ref / i_ref.max()
    if i_cand.max() > 0:
        i_cand = i_cand / i_cand.max()
    intensity_nrmse = float(np.sqrt(np.mean((i_ref - i_cand) ** 2)))
    ref_n = ref / np.abs(ref).max() if np.abs(ref).max() > 0 else ref
    cand_n = cand / np.abs(cand).max() if np.abs(cand).max() > 0 else cand
    overlap = np.vdot(cand_n, ref_n)
    aligned = cand_n * (overlap / abs(overlap) if abs(overlap) > 0 else 1.0)
    denominator = np.linalg.norm(ref_n)
    complex_nrmse = float(np.linalg.norm(aligned - ref_n) / denominator) if denominator > 0 else float("inf")
    return intensity_nrmse, complex_nrmse


def _model_validity(field, grid, propagation, model, reference_model, thresholds, context, model_result):
    _, fx_grid, fy_grid, _, _, active, _, _ = context
    metrics = {}
    statuses = []
    reasons = []
    if model.validity_hook is not None:
        hook_metrics = model.validity_hook(field, grid, propagation, active, fx_grid, fy_grid)
        metrics.update(hook_metrics)
        if "phase_error_rad" in hook_metrics:
            statuses.append(_threshold_status(hook_metrics["phase_error_rad"], thresholds.model_phase_warn_rad, thresholds.model_phase_fail_rad))
        reasons.append(str(hook_metrics.get("criterion", "analytic model criterion")))
    if reference_model is not None:
        reference = reference_model.propagate(field, grid, propagation)
        reference_on_model = _resample_result(reference, model_result.x, model_result.y)
        intensity_error, complex_error = field_errors(reference_on_model, model_result.field)
        metrics.update(
            {
                "reference_model": reference_model.name,
                "reference_intensity_nrmse": intensity_error,
                "reference_complex_nrmse": complex_error,
            }
        )
        statuses.append(_worst_status(
            _threshold_status(intensity_error, thresholds.reference_intensity_warn, thresholds.reference_intensity_fail),
            _threshold_status(complex_error, thresholds.reference_complex_warn, thresholds.reference_complex_fail),
        ))
        reasons.append("peak-normalized comparison on the model's physical output coordinates")
    if not statuses:
        return CheckResult(
            "Model validity",
            "SKIP",
            metrics,
            "No model-validity hook or reference model was supplied.",
            ["Provide validity_hook and/or reference_model for an evidence-based model check."],
        )
    metrics.pop("criterion", None)
    status = _worst_status(*statuses)
    return CheckResult(
        "Model validity",
        status,
        metrics,
        "; ".join(reasons),
        ["Choose a model whose approximation error is below the experiment's tolerance."] if status in ("WARN", "FAIL") else [],
    )


def sanity_check(
    U0,
    *,
    grid: GridSpec,
    propagation: PropagationSpec,
    model: PropagationModel = ASM_MODEL,
    thresholds: SanityThresholds | None = None,
    reference_model: PropagationModel | None = None,
) -> SanityReport:
    """Run all six checks for one field/grid/propagation configuration."""

    resolved_thresholds = SanityThresholds() if thresholds is None else thresholds
    field = _validate_inputs(U0, grid, propagation)
    context = _spectrum_context(field, grid, resolved_thresholds)
    input_check = _input_sampling(field, grid, resolved_thresholds, context)
    window_check, model_result = _window_check(field, grid, propagation, model, resolved_thresholds)
    checks = [
        _grid_summary(field, grid, model_result),
        input_check,
        window_check,
        _frequency_sampling(field, grid, resolved_thresholds, window_check.status),
        _propagator_sampling(model, propagation, resolved_thresholds, context),
        _model_validity(field, grid, propagation, model, reference_model, resolved_thresholds, context, model_result),
    ]
    decision_statuses = [check.status for check in checks if check.status != "INFO"]
    overall = "FAIL" if "FAIL" in decision_statuses else "WARN" if any(status in ("WARN", "SKIP") for status in decision_statuses) else "PASS"
    return SanityReport(model=model.name, checks=checks, overall=overall)


def check_by_name(report: SanityReport, name: str) -> CheckResult:
    """Fetch one named result from a report."""

    return next(check for check in report.checks if check.name == name)
