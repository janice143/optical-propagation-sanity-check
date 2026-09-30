"""Plotting and visualization helpers for propagation fields and diagnostics."""

from __future__ import annotations

from typing import Optional
import numpy as np
import matplotlib.pyplot as plt

from propagation_sanity.core.field import SampledField
from propagation_sanity.core.grid import Grid
from propagation_sanity.diagnostics.spectrum import compute_spectrum


def plot_field_intensity(
    field: SampledField,
    title: str = "Field Intensity",
    cmap: str = "inferno",
    ax: Optional[plt.Axes] = None,
) -> plt.Axes:
    """Plot the spatial intensity distribution of a SampledField."""
    if ax is None:
        fig, ax = plt.subplots(figsize=(6, 5))

    grid = field.grid
    extent = [
        -grid.Lx / 2.0 * 1e3,
        grid.Lx / 2.0 * 1e3,
        -grid.Ly / 2.0 * 1e3,
        grid.Ly / 2.0 * 1e3,
    ]

    im = ax.imshow(
        field.intensity,
        extent=extent,
        origin="lower",
        cmap=cmap,
        aspect="auto",
    )
    plt.colorbar(im, ax=ax, label="Intensity (a.u.)")
    ax.set_title(title)
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("y (mm)")
    return ax


def plot_spectrum_with_nyquist(
    field: SampledField,
    alpha: float = 0.8,
    ax: Optional[plt.Axes] = None,
) -> plt.Axes:
    """Plot the 2D power spectrum with Nyquist and alpha diagnostic boundaries."""
    if ax is None:
        fig, ax = plt.subplots(figsize=(6, 5))

    grid = field.grid
    S = compute_spectrum(field)
    log_S = np.log10(S + 1e-12)

    extent = [
        -grid.nyquist_x * 1e-3,
        grid.nyquist_x * 1e-3,
        -grid.nyquist_y * 1e-3,
        grid.nyquist_y * 1e-3,
    ]

    im = ax.imshow(
        log_S,
        extent=extent,
        origin="lower",
        cmap="viridis",
        aspect="auto",
    )
    plt.colorbar(im, ax=ax, label="log10 Power Spectrum")

    # Draw alpha * Nyquist boundary
    ax.axvline(alpha * grid.nyquist_x * 1e-3, color="r", linestyle="--", alpha=0.7)
    ax.axvline(-alpha * grid.nyquist_x * 1e-3, color="r", linestyle="--", alpha=0.7)
    ax.axhline(alpha * grid.nyquist_y * 1e-3, color="r", linestyle="--", alpha=0.7, label=f"α={alpha} Nyquist")
    ax.axhline(-alpha * grid.nyquist_y * 1e-3, color="r", linestyle="--", alpha=0.7)

    ax.set_title("Power Spectrum & Edge Band")
    ax.set_xlabel("fx (cycles/mm)")
    ax.set_ylabel("fy (cycles/mm)")
    ax.legend(loc="upper right")
    return ax
