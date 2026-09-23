"""Centered spatial/frequency grids and reusable field generators."""

from __future__ import annotations

import numpy as np

from .types import GridSpec


def centered_axes(shape: tuple[int, int], grid: GridSpec) -> tuple[np.ndarray, np.ndarray]:
    """Return centered x and y coordinate axes for ``shape``."""

    ny, nx = shape
    x = (np.arange(nx) - nx // 2) * grid.dx
    y = (np.arange(ny) - ny // 2) * grid.resolved_dy
    return x, y


def frequency_grid(
    shape: tuple[int, int], grid: GridSpec
) -> tuple[tuple[np.ndarray, np.ndarray], np.ndarray, np.ndarray]:
    """Return centered 2-D frequency grids followed by their axes."""

    ny, nx = shape
    fx = np.fft.fftshift(np.fft.fftfreq(nx, d=grid.dx))
    fy = np.fft.fftshift(np.fft.fftfreq(ny, d=grid.resolved_dy))
    return np.meshgrid(fx, fy), fx, fy


def fft2c(field: np.ndarray) -> np.ndarray:
    """Centered two-dimensional FFT."""

    return np.fft.fftshift(np.fft.fft2(np.fft.ifftshift(field)))


def ifft2c(spectrum: np.ndarray) -> np.ndarray:
    """Centered two-dimensional inverse FFT."""

    return np.fft.fftshift(np.fft.ifft2(np.fft.ifftshift(spectrum)))


def gaussian_field(
    shape: tuple[int, int],
    grid: GridSpec,
    waist: float,
    x0: float = 0.0,
    y0: float = 0.0,
    fx0: float = 0.0,
    fy0: float = 0.0,
) -> np.ndarray:
    """Create a Gaussian complex field, optionally shifted and tilted."""

    x, y = centered_axes(shape, grid)
    x_grid, y_grid = np.meshgrid(x, y)
    envelope = np.exp(-((x_grid - x0) ** 2 + (y_grid - y0) ** 2) / waist**2)
    return envelope * np.exp(1j * 2 * np.pi * (fx0 * x_grid + fy0 * y_grid))


def square_aperture(
    shape: tuple[int, int],
    grid: GridSpec,
    width: float,
) -> np.ndarray:
    """Create a centered square aperture as a complex field."""

    x, y = centered_axes(shape, grid)
    x_grid, y_grid = np.meshgrid(x, y)
    half_width = width / 2
    return (
        (np.abs(x_grid) <= half_width) & (np.abs(y_grid) <= half_width)
    ).astype(np.complex128)
