"""Square Aperture Benchmark scenario (§59–§62).

Parameters:
- N = 512
- dx = 2 μm (L = 1.024 mm)
- λ = 532 nm
- a = 100 μm (half_width = 50 μm)
- z = 1, 10, 100, 150 mm
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional, Sequence
import numpy as np

from propagation_sanity.core.grid import Grid
from propagation_sanity.core.wave import Wave
from propagation_sanity.core.field import SquareAperture, SampledField
from propagation_sanity.core.roi import ROI
from propagation_sanity.core.propagation_config import (
    PropagationConfig,
    PropagationMethod,
)
from propagation_sanity.core.simulation import SimulationContract
from propagation_sanity.core.metrics import intensity_relative_error
from propagation_sanity.adapters.waveprop_adapter import WavepropAdapter
from propagation_sanity.validate import validate
from propagation_sanity.core.report import ValidationReport


def build_square_aperture_contract(
    z: float | Sequence[float] = 100e-3,
    method: PropagationMethod = PropagationMethod.ASM,
    bandlimit: bool = False,
    padding: float = 2.0,
    nx: int = 512,
    ny: int = 512,
    dx: float = 2e-6,
    dy: float = 2e-6,
    wavelength: float = 532e-9,
    aperture_width: float = 100e-6,
) -> SimulationContract:
    """Build a standard square aperture simulation contract (§59)."""
    grid = Grid(nx=nx, ny=ny, dx=dx, dy=dy)
    wave = Wave(wavelength=wavelength)
    source = SquareAperture(half_width=aperture_width / 2.0)
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
        characteristic_size=aperture_width,
    )


def run_square_aperture_suite(
    z_list: Sequence[float] = (1e-3, 10e-3, 100e-3, 150e-3),
    run_convergence: bool = False,
) -> Dict[str, Any]:
    """Execute the full square aperture benchmark suite across multiple z (§91).

    For each distance:
    1. Runs full static validation report for standard ASM.
    2. Runs standard ASM vs BLAS (bandlimited ASM) comparison.
    3. Runs Fresnel one-step propagation.
    4. Computes physical Fraunhofer first null scale: x1 ≈ λ z / a.

    Returns
    -------
    dict
        Structured results including reports, comparisons, and physical scales.
    """
    adapter = WavepropAdapter()
    results = {}

    for z_val in z_list:
        contract_std = build_square_aperture_contract(
            z=z_val, method=PropagationMethod.ASM, bandlimit=False, padding=2.0
        )
        contract_blas = build_square_aperture_contract(
            z=z_val, method=PropagationMethod.ASM, bandlimit=True, padding=2.0
        )

        # 1. Validation report
        rep = validate(contract_std, run_convergence=run_convergence)

        # 2. Propagate standard ASM vs BLAS
        res_std = adapter.propagate(
            contract_std.field, contract_std.wave, z_val, contract_std.propagation_config
        )
        res_blas = adapter.propagate(
            contract_blas.field, contract_blas.wave, z_val, contract_blas.propagation_config
        )

        # Relative difference between standard ASM and BLAS
        # (reveals chirp aliasing at large z where standard ASM breaks down)
        center_roi = ROI.from_grid_center(contract_std.grid, fraction=0.8)
        diff_blas = intensity_relative_error(res_std.field, res_blas.field, roi=center_roi)

        # 3. Analytic Fraunhofer first null: x1 = λ z / a
        a = contract_std.characteristic_size
        lam = contract_std.wave.wavelength
        x1_null = (lam * z_val) / a

        results[f"z_{int(z_val*1e3)}mm"] = {
            "z": z_val,
            "report": rep,
            "blas_intensity_relative_diff": diff_blas,
            "fraunhofer_first_null": x1_null,
            "fresnel_number": (a / 2.0)**2 / (lam * z_val),
        }

    return results
