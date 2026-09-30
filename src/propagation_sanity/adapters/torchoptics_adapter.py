"""Propagation adapter for the TorchOptics library.

TorchOptics architecture and conventions:
- Decouples field geometry (``Field``, ``PlanarGrid``, ``shape``, ``spacing``, ``offset``)
  from propagation configuration (``propagation_method``, ``asm_pad``, ``interpolation_mode``).
- Array layout: PyTorch tensor with planar dimensions along the trailing axes (-2: rows/y, -1: cols/x).
- ``shape = (ny, nx)`` and ``spacing = (dy, dx)``.
- Methods:
  - ``ASM``: Rayleigh–Sommerfeld transfer function angular spectrum method.
  - ``DIM``: Rayleigh–Sommerfeld direct integration method (impulse response FFT convolution).
  - ``ASM_FRESNEL``: Fresnel transfer function angular spectrum method.
  - ``DIM_FRESNEL``: Fresnel impulse response FFT convolution.
  - ``AUTO`` / ``AUTO_FRESNEL``: Automatic selection between ASM and DIM based on
    Voelz critical propagation distance z_c = 2 * |x_max| * Delta / lambda.
- Boundary effect management:
  - Mature production library design: ASM defaults to ``asm_pad = (2*ny, 2*nx)``, padding by
    2x the field size on each side to suppress periodic wrap-around boundary artifacts.
- Output sampling:
  - Propagates on the computational plane and resamples onto arbitrary output plane
    geometry via ``plane_sample`` (bilinear, nearest, bicubic).
- Autograd / differentiable optics:
  - Native PyTorch tensor operations support end-to-end automatic differentiation.
"""

from __future__ import annotations

from typing import Optional, Dict, Any, Tuple, Union
import numpy as np

try:
    import torch
    import torchoptics
    from torchoptics import Field as TOField, PlanarGrid
    import torchoptics.propagation as to_prop
    _TORCHOPTICS_AVAILABLE = True
except ImportError:
    _TORCHOPTICS_AVAILABLE = False

from propagation_sanity.core.grid import Grid
from propagation_sanity.core.field import SampledField
from propagation_sanity.core.wave import Wave
from propagation_sanity.core.propagation_config import (
    PropagationConfig,
    PropagationMethod,
)
from propagation_sanity.adapters.waveprop_adapter import PropagationResult


class TorchOpticsAdapter:
    """Adapter wrapping TorchOptics for scalar optical propagation.

    Provides a uniform interface for ASM, DIM, Fresnel variants, automatic regime
    switching, configurable boundary padding (asm_pad), arbitrary output grid resampling,
    and differentiable PyTorch autograd integration.
    """

    def __init__(
        self,
        default_device: Union[str, "torch.device"] = "cpu",
        default_dtype: Optional["torch.dtype"] = None,
    ) -> None:
        if not _TORCHOPTICS_AVAILABLE:
            raise ImportError(
                "TorchOptics is not installed. Please install torchoptics: "
                "pip install torchoptics"
            )
        self.default_device = default_device
        self.default_dtype = default_dtype if default_dtype is not None else torch.complex128

    def propagate(
        self,
        field: SampledField,
        wave: Wave,
        z: float,
        config: PropagationConfig,
        output_grid: Optional[Grid] = None,
    ) -> PropagationResult:
        """Run propagation on a SampledField and return a PropagationResult.

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
        output_grid : Grid, optional
            Target output grid. If None, defaults to matching input grid
            (or config.extra["output_grid"]).

        Returns
        -------
        PropagationResult
            Standard result containing output SampledField, output Grid, and metadata.
        """
        grid = field.grid
        device = config.extra.get("device", self.default_device)
        dtype = config.extra.get("dtype", self.default_dtype)

        # Convert numpy array to torch tensor
        tensor_data = torch.as_tensor(field.data, dtype=dtype, device=device)

        # Determine target output grid
        target_grid = output_grid or config.extra.get("output_grid", grid)

        # Execute tensor-level propagation
        out_tensor, method_str, asm_pad, critical_z = self._propagate_core(
            tensor_data=tensor_data,
            input_grid=grid,
            output_grid=target_grid,
            wave=wave,
            z=z,
            config=config,
        )

        out_data = out_tensor.detach().cpu().numpy()
        out_field = SampledField(data=out_data, grid=target_grid)

        metadata: Dict[str, Any] = {
            "backend": "torchoptics",
            "method": method_str,
            "z": z,
            "wavelength": wave.wavelength,
            "wavelength_medium": wave.wavelength_medium,
            "padding": config.padding,
            "asm_pad": asm_pad,
            "interpolation": config.interpolation or config.extra.get("interpolation_mode", "nearest"),
            "critical_distance": critical_z,
            "torchoptics_version": getattr(torchoptics, "__version__", "unknown"),
            "torch_version": torch.__version__,
            "device": str(device),
            "dtype": str(dtype),
        }

        if config.bandlimit:
            metadata["bandlimit_requested"] = True
            metadata["bandlimit_note"] = (
                "TorchOptics relies on spatial padding (asm_pad) and AUTO method switching "
                "to DIM rather than frequency-domain Matsushima bandlimiting filters."
            )

        return PropagationResult(
            field=out_field,
            output_grid=target_grid,
            metadata=metadata,
        )

    def propagate_field(
        self,
        to_field: "TOField",
        z: float,
        config: PropagationConfig,
        output_plane: Optional["PlanarGrid"] = None,
    ) -> "TOField":
        """Propagate a TorchOptics Field directly, preserving autograd history.

        Parameters
        ----------
        to_field : torchoptics.Field
            Input TorchOptics Field instance.
        z : float
            Propagation distance (m).
        config : PropagationConfig
            Propagation settings.
        output_plane : PlanarGrid, optional
            Output PlanarGrid geometry. If None, preserves input geometry.

        Returns
        -------
        torchoptics.Field
            Propagated TorchOptics Field.
        """
        method_str = self._resolve_method(config)
        asm_pad = self._resolve_asm_pad(config, shape=(int(to_field.shape[0]), int(to_field.shape[1])))
        interpolation_mode = config.interpolation or config.extra.get("interpolation_mode", "nearest")

        if output_plane is not None:
            return to_field.propagate(
                shape=output_plane.shape,
                z=z,
                spacing=output_plane.spacing,
                offset=output_plane.offset,
                propagation_method=method_str,
                asm_pad=asm_pad,
                interpolation_mode=interpolation_mode,
            )
        else:
            return to_field.propagate(
                shape=to_field.shape,
                z=z,
                spacing=to_field.spacing,
                offset=to_field.offset,
                propagation_method=method_str,
                asm_pad=asm_pad,
                interpolation_mode=interpolation_mode,
            )

    def propagate_tensor(
        self,
        u_in: "torch.Tensor",
        grid: Grid,
        wave: Wave,
        z: float,
        config: PropagationConfig,
        output_grid: Optional[Grid] = None,
    ) -> "torch.Tensor":
        """Propagate a raw PyTorch tensor, maintaining gradient flow for differentiable optics.

        Parameters
        ----------
        u_in : torch.Tensor
            Complex field tensor of shape (..., ny, nx).
        grid : Grid
            Input spatial grid.
        wave : Wave
            Monochromatic wave parameters.
        z : float
            Propagation distance (m).
        config : PropagationConfig
            Propagation configuration.
        output_grid : Grid, optional
            Target output grid.

        Returns
        -------
        torch.Tensor
            Propagated tensor on the target grid.
        """
        target_grid = output_grid or config.extra.get("output_grid", grid)
        out_tensor, _, _, _ = self._propagate_core(
            tensor_data=u_in,
            input_grid=grid,
            output_grid=target_grid,
            wave=wave,
            z=z,
            config=config,
        )
        return out_tensor

    def calculate_critical_distance(
        self,
        grid: Grid,
        wave: Wave,
    ) -> Tuple[float, float]:
        """Compute the Voelz critical propagation distance z_c along y and x.

        .. math::
            z_{c, y} = \\frac{2 |y_{\\max}| \\Delta y}{\\lambda}, \\quad
            z_{c, x} = \\frac{2 |x_{\\max}| \\Delta x}{\\lambda}

        For z < z_c, ASM is typically the valid sampling regime; for z >= z_c,
        direct integration / impulse response (DIM) avoids transfer function aliasing.
        """
        half_ly = (grid.ny * grid.dy) / 2.0
        half_lx = (grid.nx * grid.dx) / 2.0
        zc_y = 2.0 * half_ly * grid.dy / wave.wavelength_medium
        zc_x = 2.0 * half_lx * grid.dx / wave.wavelength_medium
        return (float(zc_y), float(zc_x))

    def _resolve_method(self, config: PropagationConfig) -> str:
        """Map PropagationConfig to TorchOptics method string."""
        # Direct override takes precedence
        if "propagation_method" in config.extra:
            return str(config.extra["propagation_method"]).upper()

        method = config.method
        if method == PropagationMethod.ASM:
            if config.extra.get("fresnel", False):
                return "ASM_FRESNEL"
            return "ASM"
        elif method in (PropagationMethod.DI, PropagationMethod.FFT_DI):
            if config.extra.get("fresnel", False):
                return "DIM_FRESNEL"
            return "DIM"
        elif method == PropagationMethod.FRESNEL:
            if config.extra.get("use_dim", False) or config.extra.get("fresnel_variant") == "dim":
                return "DIM_FRESNEL"
            return "ASM_FRESNEL"
        elif method == PropagationMethod.FRAUNHOFER:
            raise NotImplementedError(
                "Fraunhofer propagation is not natively supported by TorchOptics. "
                "Use Fresnel methods, ASM, DIM, or WavepropAdapter."
            )
        else:
            raise ValueError(f"Unsupported propagation method: {method}")

    def _resolve_asm_pad(
        self,
        config: PropagationConfig,
        shape: Tuple[int, int],
    ) -> Optional[Tuple[int, int]]:
        """Calculate asm_pad parameter based on config and grid dimensions.

        TorchOptics interprets asm_pad as the number of pixels added to each side
        along planar dimensions (pad_y, pad_x).
        """
        ny, nx = shape

        # 1. Explicit asm_pad specified in extra dict
        if "asm_pad" in config.extra:
            raw_pad = config.extra["asm_pad"]
            if raw_pad is None:
                return None
            if isinstance(raw_pad, (int, float)):
                return (int(raw_pad), int(raw_pad))
            return (int(raw_pad[0]), int(raw_pad[1]))

        # 2. Flag to request TorchOptics native default padding (2x field size each side)
        if config.extra.get("use_default_asm_pad", False) or config.extra.get("torchoptics_default_pad", False):
            return None

        # 3. Standard padding factor from PropagationConfig
        # padding == 1.0 means strictly unpadded (0 padding added)
        if config.padding <= 1.0:
            return (0, 0)

        # padding > 1.0 expands computational domain by factor p.
        # Total size = p * N => added margin on each side = (p - 1)/2 * N.
        pad_y = int(round((config.padding - 1.0) * ny / 2.0))
        pad_x = int(round((config.padding - 1.0) * nx / 2.0))
        return (pad_y, pad_x)

    def _propagate_core(
        self,
        tensor_data: "torch.Tensor",
        input_grid: Grid,
        output_grid: Grid,
        wave: Wave,
        z: float,
        config: PropagationConfig,
    ) -> Tuple["torch.Tensor", str, Optional[Tuple[int, int]], Tuple[float, float]]:
        """Internal worker executing TorchOptics propagation."""
        method_str = self._resolve_method(config)
        asm_pad = self._resolve_asm_pad(config, shape=(input_grid.ny, input_grid.nx))
        interpolation_mode = config.interpolation or config.extra.get("interpolation_mode", "nearest")

        offset = config.extra.get("offset", (0.0, 0.0))
        out_offset = config.extra.get("output_offset", offset)

        # TorchOptics planar dimensions: axis -2 is rows/y, axis -1 is cols/x
        in_spacing = (input_grid.dy, input_grid.dx)
        out_spacing = (output_grid.dy, output_grid.dx)
        out_shape = (output_grid.ny, output_grid.nx)

        # Construct TorchOptics Field
        to_field = TOField(
            data=tensor_data,
            wavelength=wave.wavelength_medium,
            z=0.0,
            spacing=in_spacing,
            offset=offset,
        )

        critical_z = self.calculate_critical_distance(input_grid, wave)

        out_to_field = to_field.propagate(
            shape=out_shape,
            z=z,
            spacing=out_spacing,
            offset=out_offset,
            propagation_method=method_str,
            asm_pad=asm_pad,
            interpolation_mode=interpolation_mode,
        )

        return out_to_field.data, method_str, asm_pad, critical_z
