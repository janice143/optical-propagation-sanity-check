"""Self-Accelerating Beam Benchmark scenario (§63–§64, §92).

Demonstrates:
1. Non-compact field source where domain enlargement requires field regeneration,
   not just array zero-padding.
2. Multi-z propagation showing beam acceleration / trajectory shift across z.
"""

from __future__ import annotations

from typing import Dict, Any, Sequence
import numpy as np

from propagation_sanity.core.grid import Grid
from propagation_sanity.core.wave import Wave
from propagation_sanity.core.field import AiryBeam, SampledField
from propagation_sanity.core.roi import ROI
from propagation_sanity.core.propagation_config import (
    PropagationConfig,
    PropagationMethod,
)
from propagation_sanity.core.simulation import SimulationContract
from propagation_sanity.core.metrics import intensity_relative_error
from propagation_sanity.adapters.waveprop_adapter import WavepropAdapter
from propagation_sanity.validate import validate


def build_airy_beam_contract(
    z: float | Sequence[float] = 10e-3,
    scale: float = 20e-6,
    decay: float = 0.05,
    nx: int = 256,
    ny: int = 256,
    dx: float = 2e-6,
    dy: float = 2e-6,
    wavelength: float = 532e-9,
    method: PropagationMethod = PropagationMethod.ASM,
    bandlimit: bool = True,
    padding: float = 2.0,
) -> SimulationContract:
    """Construct an Airy beam simulation contract (§63)."""
    grid = Grid(nx=nx, ny=ny, dx=dx, dy=dy)
    wave = Wave(wavelength=wavelength)
    source = AiryBeam(scale=scale, decay=decay)
    config = PropagationConfig(
        method=method,
        backend="waveprop",
        padding=padding,
        bandlimit=bandlimit,
    )
    return SimulationContract(
        grid=grid,
        wave=wave,
        z=z,
        propagation_config=config,
        source=source,
        characteristic_size=scale,
    )


def run_airy_beam_suite(
    z_list: Sequence[float] = (0.0, 5e-3, 10e-3, 20e-3),
) -> Dict[str, Any]:
    """Execute the accelerating beam suite (§92).

    Tracks the peak intensity coordinate (acceleration trajectory)
    as a function of propagation distance z.
    """
    adapter = WavepropAdapter()
    results = {}

    for z_val in z_list:
        contract = build_airy_beam_contract(z=z_val)
        rep = validate(contract, run_convergence=False)

        res = adapter.propagate(
            contract.field, contract.wave, z_val, contract.propagation_config
        )

        # Find peak location in physical coordinates
        intensity = res.field.intensity
        peak_idx = np.unravel_index(np.argmax(intensity), intensity.shape)
        # peak_idx is (y_idx, x_idx)
        x_coords = res.output_grid.x_coords()
        y_coords = res.output_grid.y_coords()
        peak_x = float(x_coords[peak_idx[1]])
        peak_y = float(y_coords[peak_idx[0]])

        results[f"z_{int(z_val*1e3)}mm"] = {
            "z": z_val,
            "peak_x": peak_x,
            "peak_y": peak_y,
            "report": rep,
        }

    return results
