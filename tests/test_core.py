import json

import numpy as np
import pytest

from propagation_sanity import (
    GridSpec,
    PropagationModel,
    PropagationSpec,
    check_by_name,
    field_errors,
    gaussian_field,
    propagate_asm,
    sanity_check,
)


def test_report_is_deterministic_on_rectangular_grid():
    grid = GridSpec(dx=8e-6, dy=10e-6)
    propagation = PropagationSpec(wavelength=532e-9, z=8e-3)
    field = gaussian_field((48, 64), grid, waist=0.12e-3)
    first = sanity_check(field, grid=grid, propagation=propagation)
    second = sanity_check(field, grid=grid, propagation=propagation)
    assert first.to_dict() == second.to_dict()
    assert [check.name for check in first.checks] == [
        "Grid summary",
        "Input sampling",
        "Window / FOV",
        "Frequency sampling",
        "Propagator sampling",
        "Model validity",
    ]


def test_black_box_skips_checks_that_require_analytic_hooks():
    grid = GridSpec(dx=7e-6, dy=9e-6)
    field = gaussian_field((40, 56), grid, waist=0.10e-3)
    model = PropagationModel("black box", propagate_asm)
    report = sanity_check(
        field,
        grid=grid,
        propagation=PropagationSpec(633e-9, 5e-3),
        model=model,
    )
    assert check_by_name(report, "Propagator sampling").status == "SKIP"
    assert check_by_name(report, "Model validity").status == "SKIP"
    assert report.overall in {"WARN", "FAIL"}


@pytest.mark.parametrize(
    "field, grid, propagation, match",
    [
        (np.ones(4), GridSpec(1), PropagationSpec(1, 1), "two-dimensional"),
        (np.zeros((4, 4)), GridSpec(1), PropagationSpec(1, 1), "non-zero"),
        (np.full((4, 4), np.nan), GridSpec(1), PropagationSpec(1, 1), "non-zero|non-finite"),
        (np.ones((4, 4)), GridSpec(0), PropagationSpec(1, 1), "positive"),
        (np.ones((4, 4)), GridSpec(1), PropagationSpec(0, 1), "wavelength"),
        (np.ones((4, 4)), GridSpec(1), PropagationSpec(1, 0), "non-zero"),
    ],
)
def test_invalid_inputs_raise_value_error(field, grid, propagation, match):
    with pytest.raises(ValueError, match=match):
        sanity_check(field, grid=grid, propagation=propagation)


def test_report_serializes_to_json(tmp_path):
    grid = GridSpec(10e-6)
    report = sanity_check(
        gaussian_field((32, 32), grid, waist=0.08e-3),
        grid=grid,
        propagation=PropagationSpec(532e-9, 2e-3),
    )
    destination = tmp_path / "nested" / "report.json"
    report.save_json(destination)
    payload = json.loads(destination.read_text())
    assert payload["model"] == report.model
    assert len(payload["checks"]) == 6


def test_field_errors_ignore_global_scale_and_phase():
    rng = np.random.default_rng(2)
    reference = rng.normal(size=(8, 8)) + 1j * rng.normal(size=(8, 8))
    candidate = 3.5 * np.exp(1j * 0.73) * reference
    intensity, complex_error = field_errors(reference, candidate)
    assert intensity == pytest.approx(0.0, abs=1e-14)
    assert complex_error == pytest.approx(0.0, abs=1e-14)
