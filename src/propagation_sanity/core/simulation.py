"""Simulation contract — the complete numerical problem description.

A SimulationContract captures everything needed to describe *and*
reproduce a scalar free-space propagation simulation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Union, Sequence

import numpy as np

from propagation_sanity.core.grid import Grid
from propagation_sanity.core.wave import Wave
from propagation_sanity.core.field import SampledField, FieldSource
from propagation_sanity.core.roi import ROI
from propagation_sanity.core.propagation_config import PropagationConfig


@dataclass
class SimulationContract:
    """Complete description of a propagation simulation.

    Parameters
    ----------
    grid : Grid
        Input (source-plane) grid.
    wave : Wave
        Monochromatic wave parameters.
    z : float or sequence of float
        Propagation distance(s) (m).
    propagation_config : PropagationConfig
        Propagation algorithm and backend settings.
    source : FieldSource, optional
        Re-sampleable field source.  Enables resolution convergence.
    field : SampledField, optional
        Pre-sampled field.  At least one of *source* / *field* must
        be provided.
    output_grid : Grid, optional
        If the propagator produces output on a different grid.
    roi : ROI, optional
        Region of interest for comparison metrics.
    characteristic_size : float, optional
        Application-specific length scale (m) such as aperture width
        or beam diameter.  Used only for Fresnel-number diagnostics.
    dtype : str
        Numerical precision (``"float64"`` or ``"float32"``).
    """

    grid: Grid
    wave: Wave
    z: Union[float, Sequence[float]]
    propagation_config: PropagationConfig
    source: Optional[FieldSource] = None
    field: Optional[SampledField] = None
    output_grid: Optional[Grid] = None
    roi: Optional[ROI] = None
    characteristic_size: Optional[float] = None
    dtype: str = "float64"

    def __post_init__(self) -> None:
        if self.source is None and self.field is None:
            raise ValueError(
                "At least one of 'source' or 'field' must be provided."
            )
        # Materialise field from source if not given.
        if self.field is None and self.source is not None:
            self.field = self.source.sample(self.grid)

    @property
    def z_values(self) -> np.ndarray:
        """Propagation distances as 1-D array."""
        return np.atleast_1d(np.asarray(self.z, dtype=float))

    @property
    def has_source(self) -> bool:
        """Whether a re-sampleable field source is available."""
        return self.source is not None

    @property
    def resolution_convergence_available(self) -> bool:
        """True if resolution convergence can be performed."""
        return self.has_source

    def derived_report(self) -> dict:
        """Full derived-quantities report dictionary."""
        report = self.grid.derived_report()
        report["wavelength"] = self.wave.wavelength
        report["wavelength_medium"] = self.wave.wavelength_medium
        report["n"] = self.wave.n
        report["z"] = self.z_values.tolist()
        report["method"] = self.propagation_config.method.value
        report["backend"] = self.propagation_config.backend
        report["padding"] = self.propagation_config.padding
        report["bandlimit"] = self.propagation_config.bandlimit
        report["evanescent_policy"] = self.propagation_config.evanescent_policy.value
        report["dtype"] = self.dtype
        if self.characteristic_size is not None:
            report["characteristic_size"] = self.characteristic_size
        if self.output_grid is not None:
            report["output_grid"] = self.output_grid.derived_report()
        return report
