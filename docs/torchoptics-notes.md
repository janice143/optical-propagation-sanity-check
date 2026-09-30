# TorchOptics Architecture and Adapter Technical Notes

## 1. Executive Summary

TorchOptics is a PyTorch-native wave optics simulation library designed for differentiable computational optics and wave propagation. This document records the architectural survey, numerical invariants, boundary treatment, output sampling mechanics, and cross-verification results for the `TorchOpticsAdapter` in `optical-propagation-sanity-check`.

---

## 2. Decoupled Architecture: Geometry vs. Propagation

Unlike many classical wave optics tools that intertwine array dimensions with propagation settings, TorchOptics enforces a clear architectural separation:

1. **Field Geometry (`PlanarGrid`, `Field`)**:
   - Manages spatial properties: `shape`, `spacing`, `offset`, and `z` coordinate.
   - Operates on PyTorch tensors whose trailing two dimensions correspond to the transverse plane: axis `-2` for rows ($y$), axis `-1` for columns ($x$).
   - Explicit spatial step sizes: `spacing = (dy, dx)`.
   - Grid bounds: centered on `offset` (default `(0.0, 0.0)`).

2. **Propagation Configuration**:
   - `propagation_method`: Algorithm family (`"ASM"`, `"DIM"`, `"ASM_FRESNEL"`, `"DIM_FRESNEL"`, `"AUTO"`, `"AUTO_FRESNEL"`).
   - `asm_pad`: Spatial padding along both planar dimensions specifically designed to mitigate FFT circular convolution wrap-around.
   - `interpolation_mode`: Interpolation kernel (`"nearest"`, `"bilinear"`, `"bicubic"`) applied when resampling onto an arbitrary target output plane.

---

## 3. Propagation Methods and Critical Regime Switching

TorchOptics provides both exact Rayleigh–Sommerfeld (RS) formulations and Fresnel approximations:

| Method String | Mathematical Formulation | Computational Complexity |
| :--- | :--- | :--- |
| `ASM` | Rayleigh–Sommerfeld transfer function: $H(f_x, f_y) = \exp\left(i 2\pi z \sqrt{\lambda^{-2} - f_x^2 - f_y^2}\right)$ | $O(N^2 \log N)$ FFT |
| `DIM` | Direct integration / impulse response convolution: $h(x, y) = \frac{z}{2\pi r^2}\left(\frac{1}{r} - ik\right)e^{ikr}$ via FFT | $O(N^2 \log N)$ FFT |
| `ASM_FRESNEL` | Fresnel transfer function: $H(f_x, f_y) = e^{ikz} \exp\left(-i\pi \lambda z (f_x^2 + f_y^2)\right)$ | $O(N^2 \log N)$ FFT |
| `DIM_FRESNEL` | Fresnel impulse response convolution | $O(N^2 \log N)$ FFT |
| `AUTO` | Automatic regime selection based on Voelz critical propagation distance $z_c$ | Adaptive |

### Voelz Critical Distance Criterion
TorchOptics implements the critical distance criterion from David Voelz, *Computational Fourier Optics: A MATLAB Tutorial* (SPIE Press, 2011), Eq. (A.17):
$$z_c = \frac{2 |x_{\max}| \Delta}{\lambda}$$
- When $z < z_c$: transfer function phase variation stays within Nyquist limits; `AUTO` selects **ASM**.
- When $z \ge z_c$: transfer function chirping aliases high frequencies; `AUTO` selects impulse-response convolution (**DIM**).

---

## 4. Boundary Effect Mitigation: The `asm_pad` Parameter

A central engineering insight from mature optics libraries is that discrete FFT propagation fundamentally computes circular convolution. Wave energy that propagates past the computational boundary wraps around to the opposite edge unless adequate zero-padding is applied.

TorchOptics exposes this directly via `asm_pad`:
- **Default Behavior**: When `asm_pad=None`, TorchOptics pads by **$2\times$ the input field size** on each side:
  $$\text{Padded Shape} = (N_y + 2 \cdot 2N_y, N_x + 2 \cdot 2N_x) = (5N_y, 5N_x)$$
  This conservative $5\times$ computational window guarantees suppression of edge wrap-around even for strongly diverging diffraction fields.
- **Configurable Padding**: `TorchOpticsAdapter` maps `PropagationConfig.padding` to `asm_pad`:
  - `padding = 1.0`: Strictly unpadded (`asm_pad = (0, 0)`), exposing raw circular convolution.
  - `padding = 2.0`: Standard $2\times$ computational window (`asm_pad = (Ny // 2, Nx // 2)`).
  - Explicit `asm_pad` override: `config.extra["asm_pad"] = (pad_y, pad_x)`.

---

## 5. Output Sampling and Geometry Resampling

TorchOptics explicitly decouples propagation physics from detector geometry:
1. Field is propagated onto an internal propagation plane with identical sampling spacing $\Delta_{\rm prop} = \Delta_{\rm in}$.
2. If the user specifies an `output_grid` with different shape, spacing, or offset, TorchOptics calls `plane_sample` (wrapping PyTorch's `grid_sample`) to interpolate the propagated field onto the requested detector plane.
3. When output grid points align with the central region of the computational domain, interpolation introduces zero numerical error.

---

## 6. Numerical Cross-Validation Against `waveprop`

Independent verification between `TorchOpticsAdapter` and `WavepropAdapter` confirms:
1. **Unpadded ASM**: Exact agreement to machine precision ($\sim 6.5 \times 10^{-13}$ absolute error) across isotropic and anisotropic grids.
2. **Direct Integration (DIM vs. FFT-DI)**:
   - For compactly supported fields with zero boundary energy (e.g. square aperture), agreement is within $\sim 6.8 \times 10^{-14}$ relative error.
   - For non-zero boundary fields (e.g. wide Gaussian beam touching grid edges), small deviations ($\sim 0.14\%$) occur due to waveprop's optional Simpson/trapezoidal 0.5 endpoint quadrature weighting (`use_simpson=True`), whereas TorchOptics implements pure midpoint discrete convolution.
3. **Power Conservation**: Total discrete power $\sum |U|^2 \Delta x \Delta y$ is conserved within $< 2\%$ for propagating Gaussian beams.

---

## 7. Differentiable Optics Integration

Because TorchOptics operates natively on PyTorch tensors, `TorchOpticsAdapter` provides:
- `propagate(SampledField, ...)` for standard NumPy-based validation pipelines, reports, and 3-axis convergence studies.
- `propagate_tensor(u_in, ...)` and `propagate_field(to_field, ...)` for PyTorch autograd pipelines, preserving computational graphs for phase modulator optimization, diffractive optical element (DOE) design, and end-to-end differentiable optics.
