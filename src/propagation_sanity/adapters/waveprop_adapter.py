"""Propagation adapter for the waveprop library.

waveprop conventions (from source inspection):
- Array layout: first dimension = y (rows), second = x (columns)
- ``sample_points(N, delta)`` where N = [Nx, Ny], returns (x[1,Nx], y[Ny,1])
  BUT the output array is always [Ny, Nx]
- ``ft2 / ift2`` use fftshift-centred convention
- ``angular_spectrum_np`` with ``pad=True`` zero-pads to 2N and crops back
- ``bandlimit=True`` applies Matsushima BLAS
- ``d1`` can be scalar or [dy, dx] list
- Output of all propagators: ``(u_out, x2, y2)``
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple

import numpy as np

from propagation_sanity.core.grid import Grid
from propagation_sanity.core.field import SampledField
from propagation_sanity.core.wave import Wave
from propagation_sanity.core.propagation_config import (
    PropagationConfig,
    PropagationMethod,
)


@dataclass
class PropagationResult:
    """Result of a propagation computation.

    Parameters
    ----------
    field : SampledField
        Output complex field on the output grid.
    output_grid : Grid
        Grid of the output field (may differ from input for
        Fresnel single-step or rescaled BLAS).
    metadata : dict
        Backend-specific metadata (method used, padding, etc.).
    """

    field: SampledField
    output_grid: Grid
    metadata: Dict[str, Any]


class WavepropAdapter:
    """Adapter wrapping waveprop library functions.

    Provides a uniform interface for ASM, Fresnel, Fraunhofer,
    DI, and FFT-DI propagation.
    """

    def propagate(
        self,
        field: SampledField,
        wave: Wave,
        z: float,
        config: PropagationConfig,
    ) -> PropagationResult:
        """Run propagation and return result.

        Parameters
        ----------
        field : SampledField
            Input complex field.
        wave : Wave
            Monochromatic wave parameters.
        z : float
            Propagation distance (m).
        config : PropagationConfig
            Propagation algorithm settings.
        """
        method = config.method

        if method == PropagationMethod.ASM:
            return self._propagate_asm(field, wave, z, config)
        elif method == PropagationMethod.FRESNEL:
            return self._propagate_fresnel(field, wave, z, config)
        elif method == PropagationMethod.FRAUNHOFER:
            return self._propagate_fraunhofer(field, wave, z, config)
        elif method == PropagationMethod.DI:
            return self._propagate_di(field, wave, z, config)
        elif method == PropagationMethod.FFT_DI:
            return self._propagate_fft_di(field, wave, z, config)
        else:
            raise ValueError(f"Unsupported method: {method}")

    def _propagate_asm(
        self,
        field: SampledField,
        wave: Wave,
        z: float,
        config: PropagationConfig,
    ) -> PropagationResult:
        from waveprop.rs import angular_spectrum_np

        grid = field.grid
        # waveprop d1 convention: [dy, dx]
        d1 = [grid.dy, grid.dx]

        # Determine padding from config
        use_pad = config.padding > 1.0

        u_out, x2, y2 = angular_spectrum_np(
            u_in=field.data,
            wv=wave.wavelength_medium,
            d1=d1,
            dz=z,
            bandlimit=config.bandlimit,
            pad=use_pad,
        )

        # Determine output grid
        # waveprop ASM returns same-size output with same spacing
        out_grid = Grid(
            nx=u_out.shape[1],
            ny=u_out.shape[0],
            dx=grid.dx,
            dy=grid.dy,
        )

        return PropagationResult(
            field=SampledField(data=u_out, grid=out_grid),
            output_grid=out_grid,
            metadata={
                "method": "asm",
                "backend": "waveprop",
                "bandlimit": config.bandlimit,
                "pad": use_pad,
                "z": z,
                "wavelength": wave.wavelength,
            },
        )

    def _propagate_fresnel(
        self,
        field: SampledField,
        wave: Wave,
        z: float,
        config: PropagationConfig,
    ) -> PropagationResult:
        from waveprop.fresnel import fresnel_one_step

        grid = field.grid
        d1 = [grid.dy, grid.dx]

        u_out, x2, y2 = fresnel_one_step(
            u_in=field.data,
            wv=wave.wavelength_medium,
            d1=d1,
            dz=z,
        )

        # Fresnel one-step changes the output spacing
        # d2 = λz / (N * d1)
        dx_out = wave.wavelength_medium * abs(z) / (grid.nx * grid.dx)
        dy_out = wave.wavelength_medium * abs(z) / (grid.ny * grid.dy)

        out_grid = Grid(
            nx=u_out.shape[1],
            ny=u_out.shape[0],
            dx=dx_out,
            dy=dy_out,
        )

        return PropagationResult(
            field=SampledField(data=u_out, grid=out_grid),
            output_grid=out_grid,
            metadata={
                "method": "fresnel_one_step",
                "backend": "waveprop",
                "z": z,
                "wavelength": wave.wavelength,
                "note": "Output spacing differs from input (Fresnel one-step)",
            },
        )

    def _propagate_fraunhofer(
        self,
        field: SampledField,
        wave: Wave,
        z: float,
        config: PropagationConfig,
    ) -> PropagationResult:
        from waveprop.fraunhofer import fraunhofer

        grid = field.grid
        d1 = [grid.dy, grid.dx]

        u_out, x2, y2 = fraunhofer(
            u_in=field.data,
            wv=wave.wavelength_medium,
            d1=d1,
            dz=z,
        )

        # Fraunhofer output coordinates: x2 = fx * λ * z
        # Output spacing: Δx_out = λz / (N * dx)
        dx_out = wave.wavelength_medium * abs(z) / (grid.nx * grid.dx)
        dy_out = wave.wavelength_medium * abs(z) / (grid.ny * grid.dy)

        out_grid = Grid(
            nx=u_out.shape[1],
            ny=u_out.shape[0],
            dx=dx_out,
            dy=dy_out,
        )

        return PropagationResult(
            field=SampledField(data=u_out, grid=out_grid),
            output_grid=out_grid,
            metadata={
                "method": "fraunhofer",
                "backend": "waveprop",
                "z": z,
                "wavelength": wave.wavelength,
            },
        )

    def _propagate_di(
        self,
        field: SampledField,
        wave: Wave,
        z: float,
        config: PropagationConfig,
    ) -> PropagationResult:
        from waveprop.rs import direct_integration
        from waveprop.util import sample_points

        grid = field.grid
        d1 = [grid.dy, grid.dx]

        # Output coordinates: same grid as input
        x, y = sample_points(N=[grid.nx, grid.ny], delta=d1)

        u_out = direct_integration(
            u_in=field.data,
            wv=wave.wavelength_medium,
            d1=d1[0],  # DI takes scalar d1
            dz=z,
            x=np.squeeze(x),
            y=np.squeeze(y),
        )

        out_grid = Grid(nx=grid.nx, ny=grid.ny, dx=grid.dx, dy=grid.dy)

        return PropagationResult(
            field=SampledField(data=u_out, grid=out_grid),
            output_grid=out_grid,
            metadata={
                "method": "di",
                "backend": "waveprop",
                "z": z,
                "wavelength": wave.wavelength,
                "warning": "DI is O(N⁴) — very slow for large grids",
            },
        )

    def _propagate_fft_di(
        self,
        field: SampledField,
        wave: Wave,
        z: float,
        config: PropagationConfig,
    ) -> PropagationResult:
        from waveprop.rs import fft_di

        grid = field.grid
        d1 = [grid.dy, grid.dx]

        u_out, x2, y2 = fft_di(
            u_in=field.data,
            wv=wave.wavelength_medium,
            d1=d1,
            dz=z,
        )

        out_grid = Grid(
            nx=u_out.shape[1],
            ny=u_out.shape[0],
            dx=grid.dx,
            dy=grid.dy,
        )

        return PropagationResult(
            field=SampledField(data=u_out, grid=out_grid),
            output_grid=out_grid,
            metadata={
                "method": "fft_di",
                "backend": "waveprop",
                "z": z,
                "wavelength": wave.wavelength,
            },
        )
