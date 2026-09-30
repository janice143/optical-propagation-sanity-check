"""Differentiable Optics Demo.

Demonstrates numerical overfitting in computational/differentiable optics:
- Case A (Weak Setup): unbandlimited ASM at large z, where the optimizer
  exploits high-frequency transfer function aliasing to achieve a low training loss.
- Case B (Validated Setup): band-limited ASM (BLAS) preventing spurious aliased channels.
- Cross-Verification: evaluating both trained phase profiles under an independent,
  strictly validated propagator reveals that Case A fails dramatically (numerical overfitting),
  while Case B preserves its target performance.
"""

from __future__ import annotations

from typing import Dict, Any, Tuple
import numpy as np
import torch
import torch.nn as nn

from waveprop.rs import angular_spectrum


class PhaseModulator(nn.Module):
    """Trainable phase-only spatial light modulator / diffractive element."""

    def __init__(self, nx: int, ny: int) -> None:
        super().__init__()
        # Initialise phase randomly or zero
        self.phase = nn.Parameter(torch.zeros((ny, nx), dtype=torch.float32))

    def forward(self, input_field: torch.Tensor) -> torch.Tensor:
        # Modulate phase: U_out = U_in * exp(i * phase)
        phasor = torch.exp(1j * self.phase.to(torch.complex64))
        return input_field * phasor


def optimize_diffractive_element(
    target_intensity: torch.Tensor,
    nx: int = 48,
    ny: int = 48,
    dx: float = 4e-6,
    dy: float = 4e-6,
    wavelength: float = 532e-9,
    z: float = 30e-3,
    bandlimit: bool = True,
    pad: bool = True,
    backend: str = "waveprop",
    n_steps: int = 25,
    lr: float = 0.2,
) -> Tuple[PhaseModulator, list[float]]:
    """Train a phase modulator to match a target intensity pattern."""
    device = "cpu"
    modulator = PhaseModulator(nx, ny)
    optimizer = torch.optim.Adam(modulator.parameters(), lr=lr)
    loss_fn = nn.MSELoss()

    input_wave = torch.ones((ny, nx), dtype=torch.complex64, device=device)
    loss_history = []

    if backend == "torchoptics":
        from propagation_sanity.adapters.torchoptics_adapter import TorchOpticsAdapter
        from propagation_sanity.core.grid import Grid
        from propagation_sanity.core.wave import Wave
        from propagation_sanity.core.propagation_config import PropagationConfig, PropagationMethod

        to_adapter = TorchOpticsAdapter()
        to_grid = Grid(nx=nx, ny=ny, dx=dx, dy=dy)
        to_wave = Wave(wavelength=wavelength)
        to_cfg = PropagationConfig(
            method=PropagationMethod.ASM,
            backend="torchoptics",
            padding=2.0 if pad else 1.0,
            bandlimit=bandlimit,
        )

    for step in range(n_steps):
        optimizer.zero_grad()
        modulated = modulator(input_wave)

        # Forward propagation
        if backend == "torchoptics":
            propagated = to_adapter.propagate_tensor(
                u_in=modulated,
                grid=to_grid,
                wave=to_wave,
                z=z,
                config=to_cfg,
            )
        else:
            propagated, _, _ = angular_spectrum(
                u_in=modulated,
                wv=wavelength,
                d1=[dy, dx],
                dz=z,
                bandlimit=bandlimit,
                pad=pad,
                device=device,
            )

        intensity = torch.abs(propagated) ** 2
        # Normalise peak to 1 for loss comparison
        intensity_norm = intensity / (intensity.max() + 1e-12)

        loss = loss_fn(intensity_norm, target_intensity)
        loss.backward()
        optimizer.step()

        loss_history.append(float(loss.item()))

    return modulator, loss_history


def evaluate_phase_profile(
    modulator: PhaseModulator,
    target_intensity: torch.Tensor,
    nx: int = 48,
    ny: int = 48,
    dx: float = 4e-6,
    dy: float = 4e-6,
    wavelength: float = 532e-9,
    z: float = 30e-3,
    bandlimit: bool = True,
    pad: bool = True,
    backend: str = "waveprop",
) -> float:
    """Evaluate a trained phase modulator under a specific forward propagator."""
    device = "cpu"
    input_wave = torch.ones((ny, nx), dtype=torch.complex64, device=device)

    with torch.no_grad():
        modulated = modulator(input_wave)
        if backend == "torchoptics":
            from propagation_sanity.adapters.torchoptics_adapter import TorchOpticsAdapter
            from propagation_sanity.core.grid import Grid
            from propagation_sanity.core.wave import Wave
            from propagation_sanity.core.propagation_config import PropagationConfig, PropagationMethod

            to_adapter = TorchOpticsAdapter()
            to_grid = Grid(nx=nx, ny=ny, dx=dx, dy=dy)
            to_wave = Wave(wavelength=wavelength)
            to_cfg = PropagationConfig(
                method=PropagationMethod.ASM,
                backend="torchoptics",
                padding=2.0 if pad else 1.0,
                bandlimit=bandlimit,
            )
            propagated = to_adapter.propagate_tensor(
                u_in=modulated,
                grid=to_grid,
                wave=to_wave,
                z=z,
                config=to_cfg,
            )
        else:
            propagated, _, _ = angular_spectrum(
                u_in=modulated,
                wv=wavelength,
                d1=[dy, dx],
                dz=z,
                bandlimit=bandlimit,
                pad=pad,
                device=device,
            )
        intensity = torch.abs(propagated) ** 2
        intensity_norm = intensity / (intensity.max() + 1e-12)
        loss = nn.MSELoss()(intensity_norm, target_intensity)
        return float(loss.item())


def run_differentiable_optics_comparison(
    nx: int = 48,
    ny: int = 48,
    dx: float = 4e-6,
    dy: float = 4e-6,
    wavelength: float = 532e-9,
    z: float = 30e-3,
    backend: str = "waveprop",
    n_steps: int = 25,
) -> Dict[str, Any]:
    """Execute the full comparative experiment.

    Trains Case A (Weak, bandlimit=False) and Case B (Validated, bandlimit=True).
    Then cross-verifies both under the validated propagator (bandlimit=True).
    """
    # Create an off-axis target spot
    target = torch.zeros((ny, nx), dtype=torch.float32)
    # Bright spot around center
    target[ny // 2 - 2 : ny // 2 + 2, nx // 2 - 2 : nx // 2 + 2] = 1.0

    # 1. Train Case A: Weak setup (bandlimit=False)
    mod_a, losses_a = optimize_diffractive_element(
        target_intensity=target,
        nx=nx,
        ny=ny,
        dx=dx,
        dy=dy,
        wavelength=wavelength,
        z=z,
        bandlimit=False,
        pad=False,
        backend=backend,
        n_steps=n_steps,
    )

    # 2. Train Case B: Validated setup (bandlimit=True)
    mod_b, losses_b = optimize_diffractive_element(
        target_intensity=target,
        nx=nx,
        ny=ny,
        dx=dx,
        dy=dy,
        wavelength=wavelength,
        z=z,
        bandlimit=True,
        pad=True,
        backend=backend,
        n_steps=n_steps,
    )

    # 3. Independent Cross-Verification on strictly validated propagator (bandlimit=True, pad=True)
    eval_a_on_validated = evaluate_phase_profile(
        mod_a, target, nx=nx, ny=ny, dx=dx, dy=dy, wavelength=wavelength, z=z, bandlimit=True, pad=True, backend=backend
    )
    eval_b_on_validated = evaluate_phase_profile(
        mod_b, target, nx=nx, ny=ny, dx=dx, dy=dy, wavelength=wavelength, z=z, bandlimit=True, pad=True, backend=backend
    )

    return {
        "case_a_training_loss_final": losses_a[-1],
        "case_b_training_loss_final": losses_b[-1],
        "case_a_on_validated_propagator": eval_a_on_validated,
        "case_b_on_validated_propagator": eval_b_on_validated,
        "losses_a": losses_a,
        "losses_b": losses_b,
    }


def optimize_diffractive_element_torchoptics(
    target_intensity: torch.Tensor,
    nx: int = 48,
    ny: int = 48,
    dx: float = 4e-6,
    dy: float = 4e-6,
    wavelength: float = 532e-9,
    z: float = 30e-3,
    propagation_method: str = "ASM",
    asm_pad: Tuple[int, int] | None = None,
    n_steps: int = 25,
    lr: float = 0.2,
) -> Tuple[PhaseModulator, list[float]]:
    """Train a phase modulator using the TorchOptics propagation engine.

    Demonstrates differentiable propagation with TorchOptics's Field and PlanarGrid
    architecture, supporting ASM, DIM, and configurable asm_pad boundary control.
    """
    from torchoptics import Field

    device = "cpu"
    modulator = PhaseModulator(nx, ny)
    optimizer = torch.optim.Adam(modulator.parameters(), lr=lr)
    loss_fn = nn.MSELoss()

    input_wave = torch.ones((ny, nx), dtype=torch.complex64, device=device)
    loss_history = []

    for step in range(n_steps):
        optimizer.zero_grad()
        modulated = modulator(input_wave)

        # Forward propagation via TorchOptics Field
        field = Field(
            data=modulated,
            wavelength=wavelength,
            spacing=(dy, dx),
        )
        propagated_field = field.propagate(
            shape=(ny, nx),
            z=z,
            spacing=(dy, dx),
            propagation_method=propagation_method,
            asm_pad=asm_pad,
        )

        intensity = torch.abs(propagated_field.data) ** 2
        intensity_norm = intensity / (intensity.max() + 1e-12)

        loss = loss_fn(intensity_norm, target_intensity)
        loss.backward()
        optimizer.step()

        loss_history.append(float(loss.item()))

    return modulator, loss_history


def evaluate_phase_profile_torchoptics(
    modulator: PhaseModulator,
    target_intensity: torch.Tensor,
    nx: int = 48,
    ny: int = 48,
    dx: float = 4e-6,
    dy: float = 4e-6,
    wavelength: float = 532e-9,
    z: float = 30e-3,
    propagation_method: str = "ASM",
    asm_pad: Tuple[int, int] | None = None,
) -> float:
    """Evaluate a trained phase modulator using TorchOptics forward propagation."""
    from torchoptics import Field

    device = "cpu"
    input_wave = torch.ones((ny, nx), dtype=torch.complex64, device=device)

    with torch.no_grad():
        modulated = modulator(input_wave)
        field = Field(
            data=modulated,
            wavelength=wavelength,
            spacing=(dy, dx),
        )
        propagated_field = field.propagate(
            shape=(ny, nx),
            z=z,
            spacing=(dy, dx),
            propagation_method=propagation_method,
            asm_pad=asm_pad,
        )
        intensity = torch.abs(propagated_field.data) ** 2
        intensity_norm = intensity / (intensity.max() + 1e-12)
        loss = nn.MSELoss()(intensity_norm, target_intensity)
        return float(loss.item())

