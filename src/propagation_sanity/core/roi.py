"""Region of Interest in physical coordinates.

All coordinates are in metres.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple, Optional

import numpy as np

from propagation_sanity.core.grid import Grid


@dataclass(frozen=True)
class ROI:
    """Rectangular region of interest in physical space.

    Parameters
    ----------
    x_min, x_max : float
        Physical x extent (m).
    y_min, y_max : float
        Physical y extent (m).
    """

    x_min: float
    x_max: float
    y_min: float
    y_max: float

    def __post_init__(self) -> None:
        if self.x_min >= self.x_max:
            raise ValueError(f"x_min ({self.x_min}) must be < x_max ({self.x_max})")
        if self.y_min >= self.y_max:
            raise ValueError(f"y_min ({self.y_min}) must be < y_max ({self.y_max})")

    @classmethod
    def from_grid_center(cls, grid: Grid, fraction: float = 0.5) -> ROI:
        """ROI centred at origin spanning *fraction* of the grid extent."""
        if not (0 < fraction <= 1.0):
            raise ValueError(f"fraction must be in (0, 1], got {fraction}")
        hx = grid.Lx * fraction / 2.0
        hy = grid.Ly * fraction / 2.0
        return cls(x_min=-hx, x_max=hx, y_min=-hy, y_max=hy)

    @classmethod
    def common(cls, grid_a: Grid, grid_b: Grid) -> ROI:
        """Largest centred ROI common to both grids."""
        hx = min(grid_a.Lx, grid_b.Lx) / 2.0
        hy = min(grid_a.Ly, grid_b.Ly) / 2.0
        return cls(x_min=-hx, x_max=hx, y_min=-hy, y_max=hy)

    def mask(self, grid: Grid) -> np.ndarray:
        """Boolean mask of shape ``(ny, nx)`` for the ROI on *grid*."""
        X, Y = grid.xy_meshgrid()
        return (
            (X >= self.x_min) & (X <= self.x_max)
            & (Y >= self.y_min) & (Y <= self.y_max)
        )

    def slice_indices(self, grid: Grid) -> Tuple[slice, slice]:
        """Row and column slices that tightly bound the ROI.

        Returns ``(row_slice, col_slice)`` suitable for
        ``array[row_slice, col_slice]``.
        """
        x = grid.x_coords()
        y = grid.y_coords()
        col_start = int(np.searchsorted(x, self.x_min, side="left"))
        col_end = int(np.searchsorted(x, self.x_max, side="right"))
        row_start = int(np.searchsorted(y, self.y_min, side="left"))
        row_end = int(np.searchsorted(y, self.y_max, side="right"))
        return slice(row_start, row_end), slice(col_start, col_end)

    @property
    def width_x(self) -> float:
        return self.x_max - self.x_min

    @property
    def width_y(self) -> float:
        return self.y_max - self.y_min
