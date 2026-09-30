"""Tests for Accelerating Beam Benchmark (§63–§64, §92)."""

import numpy as np
import pytest

from propagation_sanity.core.field import AiryBeam
from propagation_sanity.benchmarks.accelerating_beam import (
    build_airy_beam_contract,
    run_airy_beam_suite,
)


class TestAiryBeamProperties:
    def test_non_compact_support(self):
        source = AiryBeam(scale=20e-6, decay=0.05)
        assert source.compact_support is False

    def test_domain_regeneration_vs_zero_padding(self):
        """Plan §64: field is non-compact, so on a doubled domain,

        the regenerated field has non-zero tails in the outer domain.
        """
        source = AiryBeam(scale=20e-6, decay=0.05)
        contract = build_airy_beam_contract(scale=20e-6, nx=128, ny=128)

        base_grid = contract.grid
        doubled_grid = base_grid.with_domain(2)

        # Regenerated field
        field_doubled = source.sample(doubled_grid)

        # At the outer boundary of the doubled grid, amplitude is non-zero
        outer_strip = field_doubled.amplitude[:10, :10]
        assert np.any(outer_strip > 0)


class TestAiryBeamPropagationTrajectory:
    def test_parabolic_acceleration_shift(self):
        """Plan §63/§92: As z increases, the main lobe of the Airy beam accelerates

        (shifts laterally) following the ballistic trajectory.
        """
        suite = run_airy_beam_suite(z_list=[0.0, 10e-3, 20e-3])

        p0_x = suite["z_0mm"]["peak_x"]
        p10_x = suite["z_10mm"]["peak_x"]
        p20_x = suite["z_20mm"]["peak_x"]

        # The peak shifts as propagation distance increases
        # In the Airy beam standard form, trajectory curves laterally
        assert p0_x != p10_x or p10_x != p20_x
        # The shift magnitude increases monotonically with z
        shift_10 = abs(p10_x - p0_x)
        shift_20 = abs(p20_x - p0_x)
        assert shift_20 >= shift_10
