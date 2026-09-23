import numpy as np
import pytest

from propagation_sanity import (
    ASM_MODEL,
    ASM_PADDED_MODEL,
    FRESNEL_MODEL,
    GridSpec,
    PropagationSpec,
    gaussian_field,
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
