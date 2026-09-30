"""Tests for Grid — verifying all DFT identities and conventions."""

import numpy as np
import pytest

from propagation_sanity.core.grid import Grid


# ------------------------------------------------------------------
# Grid identities
# ------------------------------------------------------------------

class TestGridIdentities:
    """Fundamental DFT grid relations."""

    def test_physical_extent(self):
        """L = N * dx"""
        g = Grid(nx=512, ny=256, dx=2e-6, dy=3e-6)
        assert g.Lx == pytest.approx(512 * 2e-6)
        assert g.Ly == pytest.approx(256 * 3e-6)

    def test_frequency_spacing(self):
        """Δf = 1 / L"""
        g = Grid(nx=512, ny=256, dx=2e-6, dy=3e-6)
        assert g.dfx == pytest.approx(1.0 / g.Lx)
        assert g.dfy == pytest.approx(1.0 / g.Ly)

    def test_nyquist(self):
        """f_N = 1 / (2 dx)"""
        g = Grid(nx=512, ny=256, dx=2e-6, dy=3e-6)
        assert g.nyquist_x == pytest.approx(1.0 / (2 * 2e-6))
        assert g.nyquist_y == pytest.approx(1.0 / (2 * 3e-6))

    def test_benchmark_parameters(self):
        """Standard benchmark parameters: N=512, dx=2μm → L=1.024mm, etc."""
        g = Grid(nx=512, ny=512, dx=2e-6, dy=2e-6)
        assert g.Lx == pytest.approx(1.024e-3)
        assert g.Ly == pytest.approx(1.024e-3)
        assert g.dfx == pytest.approx(1.0 / 1.024e-3, rel=1e-10)
        assert g.nyquist_x == pytest.approx(250e3)  # 250 mm⁻¹ = 250000 m⁻¹


# ------------------------------------------------------------------
# Padding relation
# ------------------------------------------------------------------

class TestPaddingRelation:
    """If N→2N with dx constant, then L→2L and Δf→Δf/2."""

    def test_domain_doubling(self):
        g1 = Grid(nx=512, ny=512, dx=2e-6, dy=2e-6)
        g2 = g1.with_domain(2)

        assert g2.nx == 1024
        assert g2.ny == 1024
        assert g2.dx == g1.dx
        assert g2.dy == g1.dy
        assert g2.Lx == pytest.approx(2 * g1.Lx)
        assert g2.Ly == pytest.approx(2 * g1.Ly)
        assert g2.dfx == pytest.approx(g1.dfx / 2)
        assert g2.dfy == pytest.approx(g1.dfy / 2)

    def test_resolution_doubling(self):
        """With L fixed: N→2N, dx→dx/2, Δf stays same, Nyquist→2x."""
        g1 = Grid(nx=512, ny=512, dx=2e-6, dy=2e-6)
        g2 = g1.with_resolution(2)

        assert g2.nx == 1024
        assert g2.dx == pytest.approx(1e-6)
        assert g2.Lx == pytest.approx(g1.Lx)
        assert g2.dfx == pytest.approx(g1.dfx)
        assert g2.nyquist_x == pytest.approx(2 * g1.nyquist_x)


# ------------------------------------------------------------------
# Coordinate arrays
# ------------------------------------------------------------------

class TestCoordinateArrays:
    def test_x_coords_shape_and_symmetry(self):
        g = Grid(nx=128, ny=64, dx=1e-6, dy=1e-6)
        x = g.x_coords()
        assert x.shape == (128,)
        # For even N the array is antisymmetric around index N//2
        assert x[0] == pytest.approx(-64e-6)

    def test_y_coords_shape(self):
        g = Grid(nx=128, ny=64, dx=1e-6, dy=1e-6)
        y = g.y_coords()
        assert y.shape == (64,)

    def test_meshgrid_shape(self):
        g = Grid(nx=128, ny=64, dx=1e-6, dy=1e-6)
        X, Y = g.xy_meshgrid()
        assert X.shape == (64, 128)
        assert Y.shape == (64, 128)

    def test_freq_matches_fftfreq(self):
        g = Grid(nx=128, ny=64, dx=2e-6, dy=3e-6)
        fx = g.fx_coords()
        expected = np.fft.fftfreq(128, d=2e-6)
        np.testing.assert_allclose(fx, expected)

        fy = g.fy_coords()
        expected_y = np.fft.fftfreq(64, d=3e-6)
        np.testing.assert_allclose(fy, expected_y)

    def test_freq_meshgrid_shape(self):
        g = Grid(nx=128, ny=64, dx=1e-6, dy=1e-6)
        FX, FY = g.fxy_meshgrid()
        assert FX.shape == (64, 128)
        assert FY.shape == (64, 128)


# ------------------------------------------------------------------
# Validation
# ------------------------------------------------------------------

class TestGridValidation:
    def test_negative_dx(self):
        with pytest.raises(ValueError):
            Grid(nx=128, ny=128, dx=-1e-6, dy=1e-6)

    def test_zero_nx(self):
        with pytest.raises(ValueError):
            Grid(nx=0, ny=128, dx=1e-6, dy=1e-6)

    def test_frozen(self):
        g = Grid(nx=128, ny=128, dx=1e-6, dy=1e-6)
        with pytest.raises(AttributeError):
            g.dx = 2e-6  # type: ignore


class TestGridDerivedReport:
    def test_report_keys(self):
        g = Grid(nx=512, ny=512, dx=2e-6, dy=2e-6)
        r = g.derived_report()
        for key in ("nx", "ny", "dx", "dy", "Lx", "Ly", "dfx", "dfy",
                     "nyquist_x", "nyquist_y"):
            assert key in r


class TestGridStr:
    def test_str(self):
        g = Grid(nx=512, ny=512, dx=2e-6, dy=2e-6)
        s = str(g)
        assert "512" in s
        assert "μm" in s
