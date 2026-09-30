"""Tests for Differentiable Optics benchmark."""

import pytest
import torch

from propagation_sanity.benchmarks.diff_optics import (
    PhaseModulator,
    optimize_diffractive_element,
    run_differentiable_optics_comparison,
)


class TestDifferentiableOptics:
    def test_phase_modulator_gradient(self):
        mod = PhaseModulator(16, 16)
        x = torch.ones((16, 16), dtype=torch.complex64)
        out = mod(x)
        loss = out.abs().sum()
        loss.backward()
        assert mod.phase.grad is not None

    def test_optimization_decreases_loss(self):
        target = torch.zeros((24, 24), dtype=torch.float32)
        target[10:14, 10:14] = 1.0

        mod, losses = optimize_diffractive_element(
            target_intensity=target,
            nx=24,
            ny=24,
            dx=4e-6,
            dy=4e-6,
            wavelength=532e-9,
            z=15e-3,
            bandlimit=True,
            pad=True,
            n_steps=10,
            lr=0.3,
        )
        assert len(losses) == 10
        assert losses[-1] < losses[0]

    def test_diff_optics_comparison_runs(self):
        """Both cases run and demonstrate optimization progress."""
        res = run_differentiable_optics_comparison(
            nx=24, ny=24, dx=4e-6, dy=4e-6, wavelength=532e-9, z=20e-3, n_steps=8
        )
        assert res["case_a_training_loss_final"] < res["losses_a"][0]
        assert res["case_b_training_loss_final"] < res["losses_b"][0]
        assert "case_a_on_validated_propagator" in res
        assert "case_b_on_validated_propagator" in res
