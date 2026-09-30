"""Coordinate utilities and grid alignment.

Functions for physical↔index transforms, common-ROI computation,
and field interpolation between grids.
"""

from __future__ import annotations

from typing import Optional, Tuple

import numpy as np
from scipy.interpolate import RegularGridInterpolator

from propagation_sanity.core.grid import Grid
from propagation_sanity.core.roi import ROI


def physical_to_index(coord: float, origin: float, spacing: float) -> int:
    """Convert a physical coordinate to nearest array index.

    Parameters
    ----------
    coord : float
        Physical position (m).
    origin : float
        Physical position of the first sample.
    spacing : float
        Sample spacing (m).
    """
    return int(round((coord - origin) / spacing))


def index_to_physical(idx: int, origin: float, spacing: float) -> float:
    """Convert an array index to physical coordinate."""
    return origin + idx * spacing


def common_roi(grid_a: Grid, grid_b: Grid) -> ROI:
    """Compute the largest centred ROI common to both grids."""
    return ROI.common(grid_a, grid_b)


def interpolate_field(
    data: np.ndarray,
    src_grid: Grid,
    dst_grid: Grid,
    method: str = "linear",
) -> Tuple[np.ndarray, str]:
    """Interpolate a 2-D complex field from *src_grid* to *dst_grid*.

    Parameters
    ----------
    data : np.ndarray
        Complex field of shape ``(src_grid.ny, src_grid.nx)``.
    src_grid : Grid
        Grid that *data* lives on.
    dst_grid : Grid
        Target grid.
    method : str
        Interpolation method (``"linear"``, ``"nearest"``,
        ``"slinear"``, ``"cubic"``, ``"quintic"``).

    Returns
    -------
    interpolated : np.ndarray
        Complex field on *dst_grid*.
    method_used : str
        Interpolation method string (for metadata recording).
    """
    # Source coordinates (1-D, must be sorted for RegularGridInterpolator).
    y_src = src_grid.y_coords()
    x_src = src_grid.x_coords()

    # Destination coordinates.
    X_dst, Y_dst = dst_grid.xy_meshgrid()
    pts = np.stack([Y_dst.ravel(), X_dst.ravel()], axis=-1)

    # Interpolate real and imaginary parts separately.
    real_interp = RegularGridInterpolator(
        (y_src, x_src), data.real, method=method, bounds_error=False, fill_value=0.0,
    )
    imag_interp = RegularGridInterpolator(
        (y_src, x_src), data.imag, method=method, bounds_error=False, fill_value=0.0,
    )
    out_real = real_interp(pts).reshape(dst_grid.ny, dst_grid.nx)
    out_imag = imag_interp(pts).reshape(dst_grid.ny, dst_grid.nx)
    return out_real + 1j * out_imag, method
