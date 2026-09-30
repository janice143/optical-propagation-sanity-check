"""Tests for the Square Aperture Benchmark scenario."""

import pytest

from propagation_sanity.core.propagation_config import PropagationMethod
from propagation_sanity.core.report import ResultStatus
from propagation_sanity.benchmarks.square_aperture import (
    build_square_aperture_contract,
    run_square_aperture_suite,
)


class TestSquareApertureParameters:
    """Verifies that benchmark parameters produce exact derived quantities."""

    def test_derived_quantities(self):
        c = build_square_aperture_contract(z=100e-3)
        g = c.grid
        assert g.Lx == pytest.approx(1.024e-3)
        assert g.Ly == pytest.approx(1.024e-3)
        assert g.dfx == pytest.approx(1.0 / 1.024e-3)
        assert g.nyquist_x == pytest.approx(250e3)  # 250 mm⁻¹

    def test_analytic_scales(self):
        """Fraunhofer first null x1 = λ z / a."""
        suite = run_square_aperture_suite(z_list=[1e-3, 10e-3, 100e-3, 150e-3])

        # x1 = 532nm * z / 100μm
        assert suite["z_1mm"]["fraunhofer_first_null"] == pytest.approx(5.32e-6)
        assert suite["z_10mm"]["fraunhofer_first_null"] == pytest.approx(53.2e-6)
        assert suite["z_100mm"]["fraunhofer_first_null"] == pytest.approx(532e-6)
        assert suite["z_150mm"]["fraunhofer_first_null"] == pytest.approx(798e-6)


class TestSquareApertureTrends:
    """Verifies diffraction trends across propagation distances."""

    def test_blas_difference_grows_with_distance(self):
        """At z=1mm, standard ASM and BLAS agree closely.

        At z=150mm, standard ASM suffers from chirp aliasing,
        causing a large discrepancy with BLAS.
        """
        suite = run_square_aperture_suite(z_list=[1e-3, 150e-3])

        diff_1mm = suite["z_1mm"]["blas_intensity_relative_diff"]
        diff_150mm = suite["z_150mm"]["blas_intensity_relative_diff"]

        # At z=1mm, the difference is negligible
        assert diff_1mm < 0.05
        # At z=150mm, aliasing causes significant difference
        assert diff_150mm > diff_1mm
        assert diff_150mm > 0.1

    def test_matsushima_criterion_trend(self):
        """At z=1mm, Matsushima criterion should pass.

        At z=150mm without BLAS, it should fail.
        """
        suite = run_square_aperture_suite(z_list=[1e-3, 150e-3])

        rep_1mm = suite["z_1mm"]["report"]
        rep_150mm = suite["z_150mm"]["report"]

        crit_1mm = [it for it in rep_1mm.items if it.id == "asm.admissible_band"][0]
        crit_150mm = [it for it in rep_150mm.items if it.id == "asm.admissible_band"][0]

        assert crit_1mm.status == ResultStatus.PASS
        assert crit_150mm.status == ResultStatus.FAIL
