from dataclasses import replace

import numpy as np
import pytest
from waveprop.rs import _bandpass as waveprop_bandpass

import propagation_sanity.propagators as propagators

from propagation_sanity import (
    ASM_MODEL,
    ASM_PADDED_MODEL,
    ASM_UNBANDED_MODEL,
    FRESNEL_MODEL,
    GridSpec,
    PropagationSpec,
    SanityThresholds,
    check_by_name,
    gaussian_field,
    sanity_check,
    square_aperture,
)


@pytest.mark.parametrize("model", [ASM_MODEL, ASM_PADDED_MODEL])
def test_asm_models_preserve_field_shape_and_axes(model):
    grid = GridSpec(dx=8e-6, dy=10e-6)
    field = gaussian_field((32, 40), grid, waist=0.08e-3)
    result = model.propagate(field, grid, PropagationSpec(532e-9, 2e-3))
    assert result.field.shape == field.shape
    assert result.x.shape == (field.shape[1],)
    assert result.y.shape == (field.shape[0],)
    assert np.all(np.isfinite(result.field))


def test_fresnel_requires_square_sampling():
    grid = GridSpec(dx=8e-6, dy=10e-6)
    field = gaussian_field((16, 16), grid, waist=0.05e-3)
    with pytest.raises(ValueError, match="square spatial sampling"):
        FRESNEL_MODEL.propagate(field, grid, PropagationSpec(532e-9, 2e-3))


def test_direct_integration_requires_square_array():
    from propagation_sanity import DIRECT_INTEGRATION_MODEL

    grid = GridSpec(dx=8e-6)
    field = gaussian_field((12, 16), grid, waist=0.05e-3)
    with pytest.raises(ValueError, match="square grid"):
        DIRECT_INTEGRATION_MODEL.propagate(
            field, grid, PropagationSpec(532e-9, 2e-3)
        )


def test_asm_sampling_uses_waveprop_frequency_grid_for_odd_shapes():
    shape = (31, 41)
    grid = GridSpec(dx=8e-6, dy=10e-6)
    field = np.ones(shape, dtype=np.complex128)
    captured = {}

    def capture_phase(fx, fy, propagation):
        captured["fx"] = fx
        captured["fy"] = fy
        return np.zeros(shape)

    model = replace(ASM_UNBANDED_MODEL, transfer_phase=capture_phase)
    sanity_check(
        field,
        grid=grid,
        propagation=PropagationSpec(532e-9, 2e-3),
        model=model,
    )

    expected_fx, expected_fy = propagators.waveprop_asm_frequency_grid(shape, grid)
    assert np.array_equal(captured["fx"], expected_fx)
    assert np.array_equal(captured["fy"], expected_fy)


def test_blas_support_matches_waveprop_boundary_rules(monkeypatch):
    grid = GridSpec(dx=1.0)
    propagation = PropagationSpec(wavelength=1.0, z=3 * np.sqrt(15.0) / 2)
    axis = np.array([-0.25, 0.0, 0.25])
    fx, fy = np.meshgrid(axis, axis)
    support = propagators.blas_spectral_support(fx, fy, grid, propagation)

    transfer = np.ones((3, 3), dtype=np.complex128)
    filtered = waveprop_bandpass(
        transfer,
        fx,
        fy,
        Sx=2.0,
        Sy=2.0,
        x0=0.0,
        y0=0.0,
        z0=propagation.z,
        wv=propagation.wavelength,
    )
    assert np.array_equal(support, filtered != 0)


def test_blas_sampling_verdict_uses_retained_spectral_support():
    grid = GridSpec(dx=2e-6)
    field = square_aperture((128, 128), grid, width=100e-6)
    propagation = PropagationSpec(532e-9, 20e-3)
    thresholds = SanityThresholds(
        propagator_phase_warn_pi=1.0,
        propagator_phase_fail_pi=1.25,
    )
    unbanded = sanity_check(
        field,
        grid=grid,
        propagation=propagation,
        model=ASM_UNBANDED_MODEL,
        thresholds=thresholds,
    )
    bandlimited = sanity_check(
        field,
        grid=grid,
        propagation=propagation,
        model=ASM_MODEL,
        thresholds=thresholds,
    )
    raw_check = check_by_name(unbanded, "Propagator sampling")
    blas_check = check_by_name(bandlimited, "Propagator sampling")
    assert raw_check.status == "FAIL"
    assert blas_check.status == "WARN"
    assert blas_check.metrics["max_active_phase_step_over_pi"] >= (
        thresholds.propagator_phase_fail_pi
    )
    assert blas_check.metrics["max_supported_phase_step_over_pi"] < (
        thresholds.propagator_phase_warn_pi
    )
    assert 0 < blas_check.metrics["retained_input_spectral_energy"] <= 1


def test_square_aperture_improved_run_clears_original_blockers():
    grid = GridSpec(dx=2e-6, dy=2e-6, min_feature_size=100e-6)
    thresholds = SanityThresholds(
        spectral_edge_warn=5e-3,
        spectral_edge_fail=1e-2,
        edge_energy_warn=5e-2,
        edge_energy_fail=1e-1,
        propagator_phase_warn_pi=1.0,
        propagator_phase_fail_pi=1.25,
    )
    distances = (1e-3, 10e-3, 100e-3, 150e-3)

    run1_field = square_aperture((512, 512), grid, width=100e-6)
    run1_statuses = [
        sanity_check(
            run1_field,
            grid=grid,
            propagation=PropagationSpec(532e-9, z),
            model=ASM_UNBANDED_MODEL,
            thresholds=thresholds,
        ).overall
        for z in distances
    ]

    run2_field = square_aperture((1024, 1024), grid, width=100e-6)
    run2_reports = [
        sanity_check(
            run2_field,
            grid=grid,
            propagation=PropagationSpec(532e-9, z),
            model=ASM_PADDED_MODEL,
            thresholds=thresholds,
        )
        for z in distances
    ]

    assert run1_statuses == ["PASS", "FAIL", "FAIL", "FAIL"]
    assert [report.overall for report in run2_reports] == [
        "PASS",
        "PASS",
        "WARN",
        "WARN",
    ]
    long_distance_checks = [
        check_by_name(report, "Propagator sampling") for report in run2_reports[2:]
    ]
    assert all(check.status == "WARN" for check in long_distance_checks)
    assert all(
        check.metrics["max_active_phase_step_over_pi"]
        >= thresholds.propagator_phase_fail_pi
        for check in long_distance_checks
    )
    assert all(
        check.metrics["max_supported_phase_step_over_pi"]
        < thresholds.propagator_phase_warn_pi
        for check in long_distance_checks
    )
    assert [
        check.metrics["retained_input_spectral_energy"]
        for check in long_distance_checks
    ] == pytest.approx([0.9511, 0.9278], abs=5e-4)
