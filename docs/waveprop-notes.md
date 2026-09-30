# waveprop Research & API Notes

## 1. Overview & Conventions

- **Repository**: `waveprop` (Python optical wave propagation library)
- **Coordinate Convention**:
  - Array shape: `(Ny, Nx)` — first dimension is $y$ (row), second dimension is $x$ (column).
  - Spatial sampling: `d1` can be scalar or `[dy, dx]`.
  - Centering: coordinates are zero-centered `np.arange(-N/2, N/2) * delta`.
- **Fourier Transforms**:
  - `ft2(g, delta)`: centered 2D DFT with `fftshift(fft2(fftshift(g))) * delta_y * delta_x`.
  - `ift2(G, delta_f)`: centered inverse 2D DFT with `ifftshift(ifft2(ifftshift(G))) * Ny * Nx * df_y * df_x`.

## 2. Available Propagators

### Angular Spectrum Method (ASM)
- Function: `waveprop.rs.angular_spectrum_np` (and PyTorch version `angular_spectrum`)
- Signature: `u_out, x2, y2 = angular_spectrum_np(u_in, wv, d1, dz, bandlimit=True, pad=True, ...)`
- Features:
  - `bandlimit=True`: Applies Matsushima & Shimobaba (2009) Band-Limited Angular Spectrum Method (BLAS).
  - `pad=True`: Zero-pads input to $2N_x \times 2N_y$ before FFT, then crops back to $N_x \times N_y$ after IFFT to simulate linear convolution without circular wrap-around artifacts.
  - Retains evanescent waves by analytical decay: $\exp(-k z \sqrt{\lambda^2 f^2 - 1})$.

### Rayleigh-Sommerfeld Direct Integration (DI)
- Function: `waveprop.rs.direct_integration(u_in, wv, d1, dz, x, y)`
- Exact $O(N_x N_y N_{x,out} N_{y,out})$ brute-force quadrature.
- Highly accurate baseline for small grids, but scales as $O(N^4)$ — prohibited for large arrays ($N \ge 256$).

### Fast-Fourier-Transform Direct Integration (FFT-DI)
- Function: `waveprop.rs.fft_di(u_in, wv, d1, dz, N_out=None, use_simpson=True)`
- Implements Shen & Wang (2006) method.
- Evaluates RS convolution via FFT of free space impulse response with Simpson/trapezoidal weights.

### Fresnel Propagation
- Functions: `waveprop.fresnel.fresnel_one_step(u_in, wv, d1, dz)` and `fresnel_two_step`
- Single-step Fresnel changes output grid spacing:
  $$\Delta x_{\rm out} = \frac{\lambda z}{N_x \Delta x_{\rm in}}$$
- Suitable for large $z$ / paraxial regime.

### Fraunhofer Propagation
- Function: `waveprop.fraunhofer.fraunhofer(u_in, wv, d1, dz)`
- Single FFT far-field approximation:
  $$x_2 = f_x \lambda z, \quad \Delta x_{\rm out} = \frac{\lambda z}{N_x \Delta x_{\rm in}}$$

## 3. Upstream Quirks & Fixes

1. **`pad=False` scoping**: In `waveprop.rs.angular_spectrum_np`, `Ny, Nx = u_in.shape` was originally located inside `if pad:`. If `pad=False`, accessing `Ny, Nx` in `sample_points` at the function end resulted in `UnboundLocalError`. Patched locally to extract shape before `if pad:`.
2. **`fft_di` dtype**: In `waveprop.rs.fft_di`, `u_in_pad` was initialized with default `np.float64`, discarding imaginary parts of complex input. Patched to `dtype=np.complex128`.
