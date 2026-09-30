"""Defensive runtime patches for upstream waveprop library.

Known upstream issues in waveprop (<= v0.1.0):
1. In `waveprop.rs.angular_spectrum_np`, when `pad=False`, `Ny` and `Nx` are only defined
   inside `if pad:`, resulting in `UnboundLocalError: local variable 'Ny' referenced before assignment`
   when `sample_points` is called.
2. In `waveprop.rs.fft_di`, `u_in_pad` is allocated as a float array by default,
   which silently discards the imaginary part of complex input fields and emits `ComplexWarning`.

This module automatically inspects the loaded `waveprop` library at runtime and dynamically
applies safe patches if either defect is detected. Once upstream releases a fixed version,
these patches automatically become no-ops.
"""

from __future__ import annotations

import functools
import inspect
import logging
import warnings
from typing import Any, Callable, Dict, Tuple

import numpy as np

logger = logging.getLogger(__name__)

_PATCHED_STATE = {
    "asm_pad_checked": False,
    "asm_pad_patched": False,
    "fft_di_complex_checked": False,
    "fft_di_complex_patched": False,
}


def _needs_asm_pad_patch() -> bool:
    """Check if `waveprop.rs.angular_spectrum_np` raises UnboundLocalError with `pad=False`."""
    try:
        from waveprop.rs import angular_spectrum_np

        dummy = np.ones((2, 2), dtype=complex)
        angular_spectrum_np(dummy, wv=1e-6, d1=1e-6, dz=1e-3, pad=False)
        return False
    except UnboundLocalError:
        return True
    except Exception:
        return False


def _needs_fft_di_complex_patch() -> bool:
    """Check if `waveprop.rs.fft_di` discards the imaginary part of complex input fields."""
    try:
        from waveprop.rs import fft_di

        dummy = np.ones((3, 3), dtype=complex) * (1.0 + 1.0j)
        with warnings.catch_warnings(record=True) as ws:
            warnings.simplefilter("always")
            out, _, _ = fft_di(dummy, wv=1e-6, d1=1e-6, dz=1e-3)
            has_warning = any(issubclass(w.category, np.ComplexWarning) for w in ws)
            lost_imag = not np.iscomplexobj(out) or np.all(np.abs(out.imag) < 1e-12)
            return has_warning or lost_imag
    except Exception:
        return False


def _patch_asm_pad() -> bool:
    """Patch `angular_spectrum_np` so `pad=False` correctly defines grid dimensions."""
    try:
        import waveprop.rs as rs
    except ImportError:
        return False

    orig_func = rs.angular_spectrum_np

    # Approach 1: Try source-level recompilation to preserve full function behavior
    try:
        src = inspect.getsource(orig_func)
        pattern = "    if pad:\n        # zero pad to simulate linear convolution\n        Ny, Nx = u_in.shape"
        replacement = "    Ny, Nx = u_in.shape\n    if pad:\n        # zero pad to simulate linear convolution"
        if pattern in src:
            fixed_src = src.replace(pattern, replacement)
            locs: Dict[str, Any] = {}
            exec(fixed_src, rs.__dict__, locs)
            rs.angular_spectrum_np = locs["angular_spectrum_np"]
            logger.info("Successfully patched waveprop.rs.angular_spectrum_np via source rewrite.")
            return True
    except Exception as exc:
        logger.debug(f"Source rewrite for angular_spectrum_np failed: {exc}, using wrapper fallback.")

    # Approach 2: Robust wrapper fallback
    @functools.wraps(orig_func)
    def safe_angular_spectrum_np(
        u_in: np.ndarray, *args: Any, **kwargs: Any
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        pad = kwargs.get("pad", True)
        if not pad:
            from waveprop.util import sample_points
            from waveprop.util import ft2, ift2

            d1 = kwargs.get("d1") if "d1" in kwargs else (args[1] if len(args) > 1 else None)
            wv = kwargs.get("wv") if "wv" in kwargs else (args[0] if len(args) > 0 else None)
            dz = kwargs.get("dz") if "dz" in kwargs else (args[2] if len(args) > 2 else None)
            bandlimit = kwargs.get("bandlimit", True)
            out_shift = kwargs.get("out_shift", 0)

            if isinstance(d1, (float, int)):
                d1 = [d1, d1]
            if isinstance(out_shift, (float, int)):
                out_shift = [out_shift, out_shift]

            Ny, Nx = u_in.shape
            H = orig_func(u_in, *args, **{**kwargs, "return_H": True, "pad": False})
            U1 = ft2(u_in, delta=d1)
            U2 = H * U1
            dfX = 1.0 / (d1[1] * float(Nx))
            dfY = 1.0 / (d1[0] * float(Ny))
            u_out = ift2(U2, delta_f=[dfY, dfX])
            x2, y2 = sample_points(N=[Ny, Nx], delta=d1, shift=out_shift)
            return u_out, x2, y2
        return orig_func(u_in, *args, **kwargs)

    rs.angular_spectrum_np = safe_angular_spectrum_np
    return True


def _patch_fft_di() -> bool:
    """Patch `fft_di` so complex fields are accurately propagated without phase truncation."""
    try:
        import waveprop.rs as rs
    except ImportError:
        return False

    orig_func = rs.fft_di

    @functools.wraps(orig_func)
    def safe_fft_di(
        u_in: np.ndarray,
        wv: float,
        d1: Any,
        dz: float,
        N_out: Any = None,
        use_simpson: bool = True,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        if np.iscomplexobj(u_in):
            # Linearity of the diffraction integral: L[re + i*im] == L[re] + i*L[im].
            # This mathematically avoids the upstream `np.zeros(..., dtype=float)` truncation.
            out_re, x2, y2 = orig_func(
                np.real(u_in), wv, d1, dz, N_out=N_out, use_simpson=use_simpson
            )
            out_im, _, _ = orig_func(
                np.imag(u_in), wv, d1, dz, N_out=N_out, use_simpson=use_simpson
            )
            return out_re + 1j * out_im, x2, y2
        return orig_func(u_in, wv, d1, dz, N_out=N_out, use_simpson=use_simpson)

    rs.fft_di = safe_fft_di
    return True


def ensure_waveprop_patched() -> Dict[str, Any]:
    """Ensure that waveprop runtime patches are applied if needed.

    Safe to call repeatedly (idempotent).
    """
    try:
        import waveprop.rs  # noqa: F401
    except ImportError:
        return {"status": "waveprop_not_installed"}

    if not _PATCHED_STATE["asm_pad_checked"]:
        if _needs_asm_pad_patch():
            _PATCHED_STATE["asm_pad_patched"] = _patch_asm_pad()
        _PATCHED_STATE["asm_pad_checked"] = True

    if not _PATCHED_STATE["fft_di_complex_checked"]:
        if _needs_fft_di_complex_patch():
            _PATCHED_STATE["fft_di_complex_patched"] = _patch_fft_di()
        _PATCHED_STATE["fft_di_complex_checked"] = True

    return dict(_PATCHED_STATE)
