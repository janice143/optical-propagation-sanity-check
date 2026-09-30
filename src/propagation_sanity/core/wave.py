"""Wave parameters for monochromatic scalar propagation.

V1 scope: monochromatic, scalar, free-space (n = 1).
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Wave:
    """Monochromatic wave descriptor.

    Parameters
    ----------
    wavelength : float
        Vacuum wavelength λ₀ (m).
    n : float
        Refractive index of the medium (default 1.0 for vacuum).
    """

    wavelength: float
    n: float = 1.0

    def __post_init__(self) -> None:
        if self.wavelength <= 0:
            raise ValueError(f"Wavelength must be positive, got {self.wavelength}")
        if self.n <= 0:
            raise ValueError(f"Refractive index must be positive, got {self.n}")

    @property
    def wavelength_medium(self) -> float:
        """Wavelength inside the medium: λ = λ₀ / n."""
        return self.wavelength / self.n

    @property
    def k(self) -> float:
        """Vacuum wavenumber k₀ = 2π / λ₀."""
        return 2.0 * math.pi / self.wavelength

    @property
    def k_medium(self) -> float:
        """Medium wavenumber k = 2π n / λ₀."""
        return 2.0 * math.pi * self.n / self.wavelength

    @property
    def freq_cutoff(self) -> float:
        """Maximum propagating spatial frequency 1/λ_medium."""
        return 1.0 / self.wavelength_medium

    def __str__(self) -> str:
        if self.n == 1.0:
            return f"Wave(λ={self.wavelength*1e9:.1f} nm)"
        return f"Wave(λ₀={self.wavelength*1e9:.1f} nm, n={self.n})"
