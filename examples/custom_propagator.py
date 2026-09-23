"""Wrap an arbitrary propagation function in the public model contract."""

from propagation_sanity import (
    GridSpec,
    PropagationModel,
    PropagationSpec,
    gaussian_field,
    propagate_asm,
    sanity_check,
)


def my_black_box(field, grid, propagation):
    # Replace this function body with another simulator. It must return a
    # PropagationResult whose x/y axes match the output field dimensions.
    return propagate_asm(field, grid, propagation)


if __name__ == "__main__":
    grid = GridSpec(dx=7e-6, dy=9e-6)
    field = gaussian_field((80, 112), grid, waist=0.10e-3)
    model = PropagationModel("My black-box propagator", my_black_box)
    report = sanity_check(
        field,
        grid=grid,
        propagation=PropagationSpec(wavelength=633e-9, z=5e-3),
        model=model,
    )
    print(report.to_text())
    print("\nThe two analytic-hook checks are SKIP because this adapter supplies no hooks.")

