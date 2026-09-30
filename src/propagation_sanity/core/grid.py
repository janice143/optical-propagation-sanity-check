"""2-D computational grid for scalar wave propagation.

All quantities are in SI units (metres, 1/m).

Convention
----------
- First array axis  → y  (row index)
- Second array axis → x  (column index)
- Frequency grids follow ``numpy.fft.fftfreq`` ordering;
  use ``numpy.fft.fftshift`` for centred display.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple

import numpy as np


@dataclass(frozen=True)
class Grid:
    """Uniform rectangular sampling grid.

    Parameters
    ----------
    nx, ny : int
        Number of sample points along x and y.
    dx, dy : float
        Sample spacing (m) along x and y.
    """

    nx: int
    ny: int
    dx: float
    dy: float

    # ---- derived (computed once, cached) --------------------------------
    Lx: float = field(init=False, repr=False)
    Ly: float = field(init=False, repr=False)
    dfx: float = field(init=False, repr=False)
    dfy: float = field(init=False, repr=False)
    nyquist_x: float = field(init=False, repr=False)
    nyquist_y: float = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.nx <= 0 or self.ny <= 0:
            raise ValueError(f"Grid dimensions must be positive, got nx={self.nx}, ny={self.ny}")
        if self.dx <= 0 or self.dy <= 0:
            raise ValueError(f"Grid spacings must be positive, got dx={self.dx}, dy={self.dy}")

        # Use object.__setattr__ because the dataclass is frozen.
        object.__setattr__(self, "Lx", self.nx * self.dx)
        object.__setattr__(self, "Ly", self.ny * self.dy)
        object.__setattr__(self, "dfx", 1.0 / self.Lx)
        object.__setattr__(self, "dfy", 1.0 / self.Ly)
        object.__setattr__(self, "nyquist_x", 1.0 / (2.0 * self.dx))
        object.__setattr__(self, "nyquist_y", 1.0 / (2.0 * self.dy))

    # ---- spatial coordinates -------------------------------------------

    def x_coords(self) -> np.ndarray:
        """1-D physical x coordinates centred on zero."""
        return (np.arange(self.nx) - self.nx // 2) * self.dx

    def y_coords(self) -> np.ndarray:
        """1-D physical y coordinates centred on zero."""
        return (np.arange(self.ny) - self.ny // 2) * self.dy

    def xy_meshgrid(self) -> Tuple[np.ndarray, np.ndarray]:
        """2-D meshgrids ``(X, Y)`` with *xy* indexing.

        ``X.shape == Y.shape == (ny, nx)``.
        """
        return np.meshgrid(self.x_coords(), self.y_coords(), indexing="xy")

    # ---- frequency coordinates -----------------------------------------

    def fx_coords(self) -> np.ndarray:
        """1-D frequency coordinates matching ``numpy.fft.fftfreq``."""
        return np.fft.fftfreq(self.nx, d=self.dx)

    def fy_coords(self) -> np.ndarray:
        """1-D frequency coordinates matching ``numpy.fft.fftfreq``."""
        return np.fft.fftfreq(self.ny, d=self.dy)

    def fxy_meshgrid(self) -> Tuple[np.ndarray, np.ndarray]:
        """2-D frequency meshgrids ``(FX, FY)`` in FFT order."""
        return np.meshgrid(self.fx_coords(), self.fy_coords(), indexing="xy")

    def fxy_meshgrid_shifted(self) -> Tuple[np.ndarray, np.ndarray]:
        """2-D frequency meshgrids centred (fftshift applied)."""
        fx = np.fft.fftshift(self.fx_coords())
        fy = np.fft.fftshift(self.fy_coords())
        return np.meshgrid(fx, fy, indexing="xy")

    # ---- derived report ------------------------------------------------

    def derived_report(self) -> dict:
        """Dictionary of derived grid quantities for the report."""
        return {
            "nx": self.nx,
            "ny": self.ny,
            "dx": self.dx,
            "dy": self.dy,
            "Lx": self.Lx,
            "Ly": self.Ly,
            "dfx": self.dfx,
            "dfy": self.dfy,
            "nyquist_x": self.nyquist_x,
            "nyquist_y": self.nyquist_y,
        }

    # ---- utilities -----------------------------------------------------

    def with_resolution(self, factor: int) -> Grid:
        """Return a new grid with resolution increased by *factor*.

        Physical domain ``L`` stays constant; ``dx`` decreases.
        This is used for resolution convergence experiments.
        """
        if factor <= 0:
            raise ValueError(f"Resolution factor must be positive, got {factor}")
        return Grid(
            nx=self.nx * factor,
            ny=self.ny * factor,
            dx=self.dx / factor,
            dy=self.dy / factor,
        )

    def with_domain(self, factor: int) -> Grid:
        """Return a new grid with physical domain expanded by *factor*.

        ``dx`` stays constant; ``N`` and ``L`` increase.
        This is used for physical-domain convergence experiments.
        """
        if factor <= 0:
            raise ValueError(f"Domain factor must be positive, got {factor}")
        return Grid(
            nx=self.nx * factor,
            ny=self.ny * factor,
            dx=self.dx,
            dy=self.dy,
        )

    def __str__(self) -> str:
        return (
            f"Grid({self.nx}×{self.ny}, "
            f"dx={self.dx*1e6:.3f} μm, "
            f"L={self.Lx*1e3:.4f}×{self.Ly*1e3:.4f} mm)"
        )
