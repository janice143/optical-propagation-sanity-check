"""Diagnostic checkers — risk indicators without formal PASS/FAIL.

Provides spectrum analysis, spatial boundary checks, ASM phase-step
analysis, and model-regime indicators.
"""

from propagation_sanity.diagnostics.spectrum import (
    compute_spectrum,
    spectral_edge_energy,
    effective_bandwidth,
    evanescent_diagnostic,
)
from propagation_sanity.diagnostics.boundaries import (
    boundary_energy,
    paraxial_fov_preview,
)
from propagation_sanity.diagnostics.asm_phase import asm_phase_step
from propagation_sanity.diagnostics.model_regime import (
    fresnel_phase_remainder,
    fresnel_number,
)

__all__ = [
    "compute_spectrum",
    "spectral_edge_energy",
    "effective_bandwidth",
    "evanescent_diagnostic",
    "boundary_energy",
    "paraxial_fov_preview",
    "asm_phase_step",
    "fresnel_phase_remainder",
    "fresnel_number",
]
