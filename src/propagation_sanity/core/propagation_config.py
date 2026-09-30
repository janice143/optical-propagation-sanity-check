"""Propagation configuration descriptors."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class PropagationMethod(Enum):
    """Supported numerical propagation methods."""
    ASM = "asm"                # Angular Spectrum Method
    FRESNEL = "fresnel"        # Fresnel propagation
    FRAUNHOFER = "fraunhofer"  # Fraunhofer far-field
    DI = "di"                  # Direct Integration (Rayleigh–Sommerfeld)
    FFT_DI = "fft_di"          # FFT-based Direct Integration


class EvanescentPolicy(Enum):
    """How evanescent spectral components are handled."""
    RETAIN = "retain"    # Keep as-is (may blow up for large z)
    DROP = "drop"        # Set to zero
    DECAY = "decay"      # Apply exponential decay


@dataclass(frozen=True)
class PropagationConfig:
    """Complete propagation configuration.

    Parameters
    ----------
    method : PropagationMethod
        Numerical propagation algorithm.
    backend : str
        Library name (e.g. ``"waveprop"``, ``"torchoptics"``).
    padding : float
        Padding factor.  ``1.0`` means no additional padding,
        ``2.0`` means the computational array is doubled, etc.
    bandlimit : bool
        Whether band-limited ASM is enabled (relevant for ASM only).
    evanescent_policy : EvanescentPolicy
        Treatment of evanescent spectral components.
    interpolation : Optional[str]
        Interpolation method if output grid differs from propagation
        grid (e.g. ``"linear"``, ``"cubic"``).
    extra : dict
        Backend-specific parameters.
    """

    method: PropagationMethod
    backend: str = "waveprop"
    padding: float = 1.0
    bandlimit: bool = False
    evanescent_policy: EvanescentPolicy = EvanescentPolicy.DROP
    interpolation: Optional[str] = None
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "method": self.method.value,
            "backend": self.backend,
            "padding": self.padding,
            "bandlimit": self.bandlimit,
            "evanescent_policy": self.evanescent_policy.value,
            "interpolation": self.interpolation,
            **self.extra,
        }

    def __str__(self) -> str:
        parts = [
            f"method={self.method.value}",
            f"backend={self.backend}",
            f"padding={self.padding}x",
        ]
        if self.bandlimit:
            parts.append("bandlimited")
        return f"PropagationConfig({', '.join(parts)})"
