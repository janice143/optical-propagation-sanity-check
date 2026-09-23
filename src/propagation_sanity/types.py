"""Public data contracts for propagation sanity checks."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable
import json

import numpy as np


@dataclass(frozen=True)
class GridSpec:
    """Spatial sampling of a two-dimensional field, in metres."""

    dx: float
    dy: float | None = None
    min_feature_size: float | None = None

    @property
    def resolved_dy(self) -> float:
        return self.dx if self.dy is None else self.dy


@dataclass(frozen=True)
class PropagationSpec:
    """Monochromatic free-space propagation parameters, in SI units."""

    wavelength: float
    z: float


@dataclass
class PropagationResult:
    """Complex output field and its one-dimensional x/y coordinate axes."""

    field: np.ndarray
    x: np.ndarray
    y: np.ndarray


TransferPhaseHook = Callable[[np.ndarray, np.ndarray, PropagationSpec], np.ndarray]
ValidityHook = Callable[
    [np.ndarray, GridSpec, PropagationSpec, np.ndarray, np.ndarray, np.ndarray],
    dict[str, Any],
]
Propagator = Callable[[np.ndarray, GridSpec, PropagationSpec], PropagationResult]


@dataclass(frozen=True)
class PropagationModel:
    """Adapter around a propagator plus optional analytic evidence hooks."""

    name: str
    propagate: Propagator
    transfer_phase: TransferPhaseHook | None = None
    validity_hook: ValidityHook | None = None
    description: str = ""


@dataclass(frozen=True)
class SanityThresholds:
    """Engineering decision thresholds used by the six checks."""

    spectral_edge_warn: float = 1e-3
    spectral_edge_fail: float = 1e-2
    input_phase_warn_pi: float = 0.5
    input_phase_fail_pi: float = 0.8
    edge_energy_warn: float = 1e-3
    edge_energy_fail: float = 1e-2
    min_frequency_samples_warn: float = 4.0
    min_frequency_samples_fail: float = 2.0
    propagator_phase_warn_pi: float = 0.5
    propagator_phase_fail_pi: float = 1.0
    model_phase_warn_rad: float = 0.1
    model_phase_fail_rad: float = 1.0
    spectrum_energy_fraction: float = 0.999
    edge_fraction: float = 0.10
    amplitude_mask_fraction: float = 0.05
    reference_intensity_warn: float = 0.30
    reference_intensity_fail: float = 1.00
    reference_complex_warn: float = 2.0
    reference_complex_fail: float = 5.0


@dataclass
class CheckResult:
    """One check's status, measurements, rationale, and suggested actions."""

    name: str
    status: str
    metrics: dict[str, Any] = field(default_factory=dict)
    reason: str = ""
    recommendations: list[str] = field(default_factory=list)


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, float) and not np.isfinite(value):
        return str(value)
    return value


def _format_metric(value: Any) -> str:
    if isinstance(value, float):
        if value == 0:
            return "0"
        if abs(value) < 1e-3 or abs(value) >= 1e4:
            return f"{value:.3e}"
        return f"{value:.5g}"
    return str(value)


@dataclass
class SanityReport:
    """Complete result returned by :func:`sanity_check`."""

    model: str
    checks: list[CheckResult]
    overall: str
    note: str = (
        "Thresholds are configurable engineering criteria, not universal physical laws."
    )

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))

    def to_text(self) -> str:
        lines = [
            "Optical Propagation Health Check",
            "=" * 36,
            f"model   : {self.model}",
            f"overall : {self.overall}",
            "",
        ]
        for check in self.checks:
            lines.append(f"[{check.status:4}] {check.name}")
            for key, value in check.metrics.items():
                lines.append(f"       {key:30s} {_format_metric(value)}")
            if check.reason:
                lines.append(f"       {check.reason}")
            for recommendation in check.recommendations:
                lines.append(f"       -> {recommendation}")
            lines.append("")
        lines.append(self.note)
        return "\n".join(lines)

    def save_json(self, path: str | Path) -> None:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

