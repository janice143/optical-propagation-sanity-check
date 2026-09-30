"""Comparison metrics for output fields.

All metrics operate on physical coordinates and support an optional
ROI mask.  Functions follow plan sections 44–47.
"""

from __future__ import annotations

from typing import Optional

import numpy as np

from propagation_sanity.core.field import SampledField
from propagation_sanity.core.roi import ROI


def _apply_roi(arr: np.ndarray, field: SampledField, roi: Optional[ROI]) -> np.ndarray:
    """Flatten array to ROI pixels."""
    if roi is None:
        return arr.ravel()
    mask = roi.mask(field.grid)
    return arr[mask]


# ------------------------------------------------------------------
# §44  Intensity relative error
# ------------------------------------------------------------------

def intensity_relative_error(
    field_a: SampledField,
    field_b: SampledField,
    roi: Optional[ROI] = None,
) -> float:
    r"""Relative L2 error of intensity distributions.

    .. math::
        \varepsilon_I = \frac{\|I_a - I_b\|_2}{\|I_b\|_2}

    Parameters
    ----------
    field_a, field_b : SampledField
        The two fields to compare.  *field_b* is the reference.
    roi : ROI, optional
        Restrict comparison to this region.
    """
    Ia = _apply_roi(field_a.intensity, field_a, roi)
    Ib = _apply_roi(field_b.intensity, field_b, roi)
    norm_b = np.linalg.norm(Ib)
    if norm_b == 0:
        return float("inf") if np.linalg.norm(Ia) > 0 else 0.0
    return float(np.linalg.norm(Ia - Ib) / norm_b)


# ------------------------------------------------------------------
# §45  Global phase offset and complex-field relative error
# ------------------------------------------------------------------

def global_phase_offset(
    field_a: SampledField,
    field_b: SampledField,
    roi: Optional[ROI] = None,
) -> float:
    r"""Estimate global phase difference α between two fields.

    .. math::
        \alpha = \arg\left(\sum U_b^* U_a\right)
    """
    Ua = _apply_roi(field_a.data, field_a, roi)
    Ub = _apply_roi(field_b.data, field_b, roi)
    return float(np.angle(np.sum(np.conj(Ub) * Ua)))


def complex_field_relative_error(
    field_a: SampledField,
    field_b: SampledField,
    roi: Optional[ROI] = None,
) -> float:
    r"""Relative L2 error of complex fields after global-phase alignment.

    .. math::
        U'_a = U_a e^{-i\alpha}, \quad
        \varepsilon_U = \frac{\|U'_a - U_b\|_2}{\|U_b\|_2}
    """
    alpha = global_phase_offset(field_a, field_b, roi)
    Ua = _apply_roi(field_a.data, field_a, roi) * np.exp(-1j * alpha)
    Ub = _apply_roi(field_b.data, field_b, roi)
    norm_b = np.linalg.norm(Ub)
    if norm_b == 0:
        return float("inf") if np.linalg.norm(Ua) > 0 else 0.0
    return float(np.linalg.norm(Ua - Ub) / norm_b)


# ------------------------------------------------------------------
# §46  Phase error (masked)
# ------------------------------------------------------------------

def phase_error(
    field_a: SampledField,
    field_b: SampledField,
    intensity_threshold: float = 0.01,
    roi: Optional[ROI] = None,
) -> dict:
    r"""Phase error statistics where intensity is significant.

    Only pixels where ``I_b / max(I_b) > intensity_threshold`` are
    included.  Global phase is aligned first.

    Returns
    -------
    dict with keys:
        ``"mean_abs"``, ``"max_abs"``, ``"rms"``, ``"n_pixels"``
    """
    alpha = global_phase_offset(field_a, field_b, roi)

    if roi is not None:
        mask = roi.mask(field_b.grid)
        Ua = field_a.data[mask] * np.exp(-1j * alpha)
        Ub = field_b.data[mask]
    else:
        Ua = field_a.data.ravel() * np.exp(-1j * alpha)
        Ub = field_b.data.ravel()

    Ib = np.abs(Ub) ** 2
    if Ib.max() == 0:
        return {"mean_abs": 0.0, "max_abs": 0.0, "rms": 0.0, "n_pixels": 0}

    sig = Ib / Ib.max() > intensity_threshold
    if sig.sum() == 0:
        return {"mean_abs": 0.0, "max_abs": 0.0, "rms": 0.0, "n_pixels": 0}

    dphi = np.angle(Ua[sig]) - np.angle(Ub[sig])
    # Wrap to [-π, π]
    dphi = (dphi + np.pi) % (2 * np.pi) - np.pi
    abs_dphi = np.abs(dphi)
    return {
        "mean_abs": float(abs_dphi.mean()),
        "max_abs": float(abs_dphi.max()),
        "rms": float(np.sqrt(np.mean(dphi**2))),
        "n_pixels": int(sig.sum()),
    }


# ------------------------------------------------------------------
# §47  Power diagnostic
# ------------------------------------------------------------------

def power(field: SampledField) -> float:
    r"""Total discrete power :math:`P = \sum|U|^2 \Delta x \Delta y`."""
    return field.power
