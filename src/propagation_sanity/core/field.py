"""Sampled field representation and field-source protocol.

Two fundamental types:

* ``SampledField`` — an already-discretised complex array on a Grid.
  Resolution convergence is *not* possible with only a SampledField.
* ``FieldSource`` — an object that can be re-sampled on any Grid,
  enabling true resolution refinement.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

import numpy as np

from propagation_sanity.core.grid import Grid


# ---------------------------------------------------------------------------
# Sampled field
# ---------------------------------------------------------------------------

@dataclass
class SampledField:
    """Complex field on a discrete grid.

    Parameters
    ----------
    data : np.ndarray
        Complex field array of shape ``(ny, nx)``.
    grid : Grid
        Spatial grid on which the field is sampled.
    """

    data: np.ndarray
    grid: Grid

    def __post_init__(self) -> None:
        expected = (self.grid.ny, self.grid.nx)
        if self.data.shape != expected:
            raise ValueError(
                f"Field data shape {self.data.shape} does not match "
                f"grid shape {expected}"
            )
        # Ensure complex dtype.
        if not np.iscomplexobj(self.data):
            self.data = self.data.astype(np.complex128)

    @property
    def intensity(self) -> np.ndarray:
        """Intensity |U|²."""
        return np.abs(self.data) ** 2

    @property
    def amplitude(self) -> np.ndarray:
        """Amplitude |U|."""
        return np.abs(self.data)

    @property
    def phase(self) -> np.ndarray:
        """Wrapped phase angle (radians)."""
        return np.angle(self.data)

    @property
    def power(self) -> float:
        """Total discrete power Σ|U|² dx dy."""
        return float(np.sum(self.intensity) * self.grid.dx * self.grid.dy)


# ---------------------------------------------------------------------------
# Field source protocol (abstract base)
# ---------------------------------------------------------------------------

class FieldSource(ABC):
    """Interface for re-sampleable continuous/parametric field sources.

    Implementations must provide ``sample(grid)`` which evaluates
    the *continuous* field description at the physical coordinates of
    ``grid``.  This is essential for resolution convergence — the
    field is re-generated at finer dx, not interpolated.
    """

    @abstractmethod
    def sample(self, grid: Grid) -> SampledField:
        """Evaluate the source on *grid* and return a SampledField."""
        ...

    @property
    @abstractmethod
    def compact_support(self) -> bool:
        """Whether the field has strictly compact spatial support.

        Compact-support sources allow domain convergence by simple
        zero-extension; non-compact sources must regenerate with
        ``sample(larger_grid)``.
        """
        ...


# ---------------------------------------------------------------------------
# Built-in field sources
# ---------------------------------------------------------------------------

class SquareAperture(FieldSource):
    """Binary square aperture centred at the origin.

    Parameters
    ----------
    half_width : float
        Half-width *a* of the aperture (m).  The aperture spans
        [-a, a] in both x and y.
    amplitude : complex
        Constant complex amplitude inside the aperture.
    """

    def __init__(
        self,
        half_width: float,
        amplitude: complex = 1.0 + 0j,
    ) -> None:
        if half_width <= 0:
            raise ValueError(f"half_width must be positive, got {half_width}")
        self.half_width = half_width
        self.amplitude = complex(amplitude)

    def sample(self, grid: Grid) -> SampledField:
        X, Y = grid.xy_meshgrid()
        mask = (np.abs(X) <= self.half_width) & (np.abs(Y) <= self.half_width)
        data = np.zeros((grid.ny, grid.nx), dtype=np.complex128)
        data[mask] = self.amplitude
        return SampledField(data=data, grid=grid)

    @property
    def compact_support(self) -> bool:
        return True

    @property
    def characteristic_size(self) -> float:
        """Full aperture width (2a)."""
        return 2.0 * self.half_width


class UniformField(FieldSource):
    """Spatially uniform complex field.

    Parameters
    ----------
    amplitude : complex
        Constant complex value everywhere.
    """

    def __init__(self, amplitude: complex = 1.0 + 0j) -> None:
        self.amplitude = complex(amplitude)

    def sample(self, grid: Grid) -> SampledField:
        data = np.full((grid.ny, grid.nx), self.amplitude, dtype=np.complex128)
        return SampledField(data=data, grid=grid)

    @property
    def compact_support(self) -> bool:
        return False


class GaussianBeam(FieldSource):
    """Gaussian beam field source.

    Parameters
    ----------
    waist : float
        Beam waist w₀ (m) — the 1/e field radius.
    amplitude : complex
        Peak complex amplitude.
    """

    def __init__(
        self,
        waist: float,
        amplitude: complex = 1.0 + 0j,
    ) -> None:
        if waist <= 0:
            raise ValueError(f"waist must be positive, got {waist}")
        self.waist = waist
        self.amplitude = complex(amplitude)

    def sample(self, grid: Grid) -> SampledField:
        X, Y = grid.xy_meshgrid()
        r2 = X**2 + Y**2
        data = self.amplitude * np.exp(-r2 / self.waist**2)
        return SampledField(data=data.astype(np.complex128), grid=grid)

    @property
    def compact_support(self) -> bool:
        return False

    @property
    def characteristic_size(self) -> float:
        """Beam diameter at 1/e² intensity (2w₀)."""
        return 2.0 * self.waist


class AiryBeam(FieldSource):
    """Finite-energy 2D Airy beam field source.

    .. math::
        U(x, y) = \\text{Ai}\\left(\\frac{x}{x_0}\\right) e^{a x / x_0} \\cdot
                  \\text{Ai}\\left(\\frac{y}{y_0}\\right) e^{a y / y_0}

    Parameters
    ----------
    scale : float
        Transverse scale parameter x₀ = y₀ (m).
    decay : float
        Exponential decay parameter a (dimensionless, typically 0.05 - 0.1).
    amplitude : complex
        Peak complex amplitude scaling.
    """

    def __init__(
        self,
        scale: float = 20e-6,
        decay: float = 0.05,
        amplitude: complex = 1.0 + 0j,
    ) -> None:
        if scale <= 0:
            raise ValueError(f"scale must be positive, got {scale}")
        if decay <= 0:
            raise ValueError(f"decay must be positive, got {decay}")
        self.scale = float(scale)
        self.decay = float(decay)
        self.amplitude = complex(amplitude)

    def sample(self, grid: Grid) -> SampledField:
        from scipy.special import airy

        X, Y = grid.xy_meshgrid()
        sx = X / self.scale
        sy = Y / self.scale

        ai_x, _, _, _ = airy(sx)
        ai_y, _, _, _ = airy(sy)

        # Exponential decay factor to ensure finite energy
        # Note: decaying factor e^{a s} dampens the positive s tail
        env_x = np.exp(self.decay * sx)
        env_y = np.exp(self.decay * sy)

        data = (self.amplitude * (ai_x * env_x) * (ai_y * env_y)).astype(np.complex128)
        return SampledField(data=data, grid=grid)

    @property
    def compact_support(self) -> bool:
        return False

    @property
    def characteristic_size(self) -> float:
        return self.scale

