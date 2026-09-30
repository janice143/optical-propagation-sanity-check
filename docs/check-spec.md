# Checker Specification — V1

This document specifies every validation check in the toolkit.
Each check has a clear assessment type, traceable threshold provenance,
and documented applicability.

## Assessment Type Taxonomy

| Type | Meaning | Allowed Status Outputs |
|---|---|---|
| DERIVED | Direct mathematical identity | INFO (value only) |
| DIAGNOSTIC | Risk indicator; informative, not conclusive | INFO, risk_hint |
| FORMAL_CRITERION | Literature-derived bound with clear assumptions | PASS / FAIL |
| CONVERGENCE | Numerical refinement experiment | CONVERGED_AT_TOLERANCE / NOT_CONVERGED / UNVERIFIED |
| CROSS_REFERENCE | Comparison with independent computation | AGREES_AT_TOLERANCE / DISAGREES / UNVERIFIED |
| SCOPE_CHECK | Applicability boundary | INFO / OUT_OF_SCOPE |

## Threshold Provenance Hierarchy

| Provenance | Meaning |
|---|---|
| THEORETICAL | Derived from mathematical theorem or exact identity |
| LITERATURE | Published in peer-reviewed paper with derivation |
| PROJECT_DEFAULT | Engineering heuristic chosen by this project |
| USER_DEFINED | Explicitly set by the user |

---

## Checker Specification Table

### C01 — Grid Identities

| Field | Value |
|---|---|
| **ID** | `grid.identities` |
| **Type** | DERIVED |
| **Failure Mode** | — (exact computation) |
| **Formula** | $L_x = N_x \Delta x$, $\Delta f_x = 1/L_x$, $f_{N,x} = 1/(2\Delta x)$ |
| **Applicability** | All methods |
| **Required Inputs** | Grid (N, Δx) |
| **Threshold** | None |
| **Threshold Provenance** | THEORETICAL |
| **Source** | DFT definition |
| **Validation** | Unit test: exact arithmetic |
| **False Positive** | None |
| **False Negative** | None |
| **Recommended Action** | N/A — pure derived values |

---

### C02 — Input Spectral Edge Energy

| Field | Value |
|---|---|
| **ID** | `spectrum.edge_energy` |
| **Type** | DIAGNOSTIC |
| **Failure Mode** | Spectral crowding near Nyquist — potential aliasing |
| **Formula** | $\eta_{\rm edge} = \frac{\sum_{|f_x|>\alpha f_{N,x} \lor |f_y|>\alpha f_{N,y}} |A|^2}{\sum |A|^2}$ |
| **Applicability** | All sampled fields |
| **Required Inputs** | Sampled field, Grid, α (default 0.8) |
| **Threshold** | None (configurable α) |
| **Threshold Provenance** | PROJECT_DEFAULT (α = 0.8 from original article) |
| **Source** | Project exploratory analysis |
| **Validation** | Synthetic near-Nyquist sinusoid |
| **False Positive** | Legitimately broadband fields may have significant edge energy without aliasing issues |
| **False Negative** | Pre-existing aliasing (folded into low frequencies) cannot be detected |
| **Recommended Action** | Run resolution convergence if η_edge is high |

---

### C03 — Effective Spectrum (Energy Quantiles)

| Field | Value |
|---|---|
| **ID** | `spectrum.effective_bandwidth` |
| **Type** | DIAGNOSTIC |
| **Failure Mode** | Field bandwidth relative to Nyquist |
| **Formula** | Radial and projected (x/y) frequency quantiles at configurable coverage (95%, 99%, 99.9%) |
| **Applicability** | All sampled fields |
| **Required Inputs** | Sampled field, Grid, coverage level |
| **Threshold** | None |
| **Threshold Provenance** | NONE |
| **Source** | Standard spectral analysis |
| **Validation** | Known band-limited synthetic field |
| **False Positive** | N/A (informational) |
| **False Negative** | Pre-aliased spectrum hides true bandwidth |
| **Recommended Action** | Compare effective bandwidth to Nyquist frequency |

---

### C04 — Input Resolution (Feature Pixels)

| Field | Value |
|---|---|
| **ID** | `input.feature_pixels` |
| **Type** | DIAGNOSTIC |
| **Failure Mode** | Characteristic feature undersampled |
| **Formula** | $N_{\rm feat} = a / \Delta x$ (pixels per characteristic size) |
| **Applicability** | When characteristic_size is provided |
| **Required Inputs** | Grid, characteristic_size |
| **Threshold** | None (no universal ">10 pixels = PASS" rule) |
| **Threshold Provenance** | NONE |
| **Source** | Sampling theory (informational) |
| **Validation** | Trivial arithmetic |
| **False Positive** | Large N_feat does not prove absence of aliasing |
| **False Negative** | N/A |
| **Recommended Action** | Use resolution convergence for definitive assessment |

---

### C05 — Spatial Boundary Energy

| Field | Value |
|---|---|
| **ID** | `spatial.boundary_energy` |
| **Type** | DIAGNOSTIC |
| **Failure Mode** | Field truncation at computation-domain edge |
| **Formula** | $\eta_{\rm spatial-edge} = E_{\rm edge} / E_{\rm total}$, edge strip = outer p% of domain |
| **Applicability** | All fields |
| **Required Inputs** | Sampled field, Grid, edge fraction p (default 5%) |
| **Threshold** | None |
| **Threshold Provenance** | PROJECT_DEFAULT |
| **Source** | Project heuristic; cf. Zemax POP guard-band guidance |
| **Validation** | Aperture smaller/larger than domain |
| **False Positive** | Some fields naturally extend to boundary |
| **False Negative** | Cannot detect if field *should* extend beyond domain |
| **Recommended Action** | Run physical-domain convergence |

---

### C06 — Paraxial FOV Preview (f_safe)

| Field | Value |
|---|---|
| **ID** | `spatial.paraxial_fov` |
| **Type** | DIAGNOSTIC |
| **Failure Mode** | Diffracted field may exceed computation window |
| **Formula** | $f_{\rm safe} = L / (2\lambda z)$ (paraxial estimate) |
| **Applicability** | FFT propagation methods |
| **Required Inputs** | Grid, wavelength, z |
| **Threshold** | None |
| **Threshold Provenance** | NONE |
| **Source** | Paraxial diffraction relation $x \approx \lambda z f$ |
| **Validation** | Compare with domain convergence |
| **Assumptions** | Paraxial; does not account for full field support or interference |
| **False Positive** | Overestimates risk for compact-support inputs |
| **False Negative** | Underestimates for wide-angle scattering |
| **Recommended Action** | Cannot replace convergence experiments |

---

### C07 — ASM Phase-Step Diagnostic

| Field | Value |
|---|---|
| **ID** | `asm.phase_step` |
| **Type** | DIAGNOSTIC |
| **Failure Mode** | ASM transfer-function undersampling |
| **Formula** | $\Delta\phi_x = |\phi(f_x+\Delta f_x, f_y) - \phi(f_x, f_y)|$ using **unwrapped analytical** phase $\phi = 2\pi z \sqrt{1/\lambda^2 - f_x^2 - f_y^2}$ |
| **Applicability** | ASM only |
| **Required Inputs** | Grid, wavelength, z |
| **Threshold** | None (Δφ < π is an engineering heuristic, NOT formal criterion) |
| **Threshold Provenance** | PROJECT_DEFAULT |
| **Source** | Original article + sampling theory |
| **Validation** | Comparison with BLAS results |
| **False Positive** | Large phase step does not automatically mean wrong result (BLAS may correct it) |
| **False Negative** | Small max phase step does not guarantee overall sampling adequacy |
| **Recommended Action** | Run ASM formal criterion (C08) if available; run convergence |

---

### C08 — ASM Admissible Band (Matsushima Criterion)

| Field | Value |
|---|---|
| **ID** | `asm.admissible_band` |
| **Type** | FORMAL_CRITERION |
| **Failure Mode** | ASM transfer-function aliasing |
| **Formula** | Admissible frequency region from Matsushima & Shimobaba 2009, Eq. 13/20. Implemented in waveprop `_bandpass()` function using limit frequencies: $u_{\rm limit} = [(x \pm S/2)^{-2} z^2 + 1]^{-1/2} / \lambda$ |
| **Applicability** | ASM only |
| **Required Inputs** | Grid, wavelength, z, physical window size S |
| **Threshold** | Paper-derived spectral region boundary |
| **Threshold Provenance** | LITERATURE |
| **Source** | Matsushima & Shimobaba, "Band-Limited Angular Spectrum Method", Opt. Express 17, 19662–19673 (2009). DOI: 10.1364/OE.17.019662 |
| **Validation** | Reproduce standard ASM vs BLAS difference; compare with waveprop implementation |
| **Assumptions** | Free-space propagation; on-axis (off-axis generalisation in Matsushima 2010) |
| **False Positive** | Frequencies outside admissible band may have negligible input energy |
| **False Negative** | Band limit alone does not fix all sampling issues |
| **Recommended Action** | Enable BLAS or verify via convergence |

> **Status**: PENDING_VERIFICATION — The exact formula must be verified against the paper's Eq. 13 and 20 before marking as production FORMAL_CRITERION. Current implementation follows waveprop's `_bandpass()`.

---

### C09 — Fresnel Phase Remainder

| Field | Value |
|---|---|
| **ID** | `model.fresnel_remainder` |
| **Type** | DIAGNOSTIC |
| **Failure Mode** | Paraxial approximation error |
| **Formula** | $\Delta\phi_{A-F} = \phi_{\rm ASM}(f_x,f_y) - \phi_{\rm Fresnel}(f_x,f_y)$ over active spectral region |
| **Applicability** | Fresnel propagation |
| **Required Inputs** | Grid, wavelength, z, effective spectral support |
| **Threshold** | None (1 rad is a screening guideline, not a strict boundary) |
| **Threshold Provenance** | PROJECT_DEFAULT |
| **Source** | Fourier optics, paraxial expansion |
| **Validation** | ASM vs Fresnel direct comparison |
| **False Positive** | Phase error may cancel in intensity |
| **False Negative** | Small average error may hide localised large errors |
| **Recommended Action** | If Δφ is significant, prefer ASM or run cross-reference |

---

### C10 — Fresnel Number

| Field | Value |
|---|---|
| **ID** | `model.fresnel_number` |
| **Type** | DIAGNOSTIC |
| **Failure Mode** | Fraunhofer approximation misuse |
| **Formula** | $N_F = a^2 / (\lambda z)$ |
| **Applicability** | When characteristic_size is known |
| **Required Inputs** | characteristic_size, wavelength, z |
| **Threshold** | None (regime indicator, not boolean checker) |
| **Threshold Provenance** | NONE |
| **Source** | Standard Fourier optics |
| **Validation** | Analytic |
| **False Positive** | N_F is a global indicator; local field structure matters |
| **False Negative** | N/A |
| **Recommended Action** | Use to select propagation regime; not a standalone check |

---

### C11 — Evanescent Component Diagnostic

| Field | Value |
|---|---|
| **ID** | `scope.evanescent` |
| **Type** | SCOPE_CHECK / DIAGNOSTIC |
| **Failure Mode** | Significant sub-wavelength content |
| **Formula** | Fraction of spectral energy where $\sqrt{f_x^2 + f_y^2} > 1/\lambda$ |
| **Applicability** | All methods |
| **Required Inputs** | Sampled field, Grid, wavelength |
| **Threshold** | None |
| **Threshold Provenance** | NONE |
| **Source** | Wave equation |
| **Validation** | Synthetic sub-wavelength grating |
| **False Positive** | Numerical noise near cutoff |
| **False Negative** | Evanescent content may already have decayed |
| **Recommended Action** | If significant: scalar free-space V1 may not be sufficient |

---

### C12 — Resolution Convergence

| Field | Value |
|---|---|
| **ID** | `convergence.resolution` |
| **Type** | CONVERGENCE |
| **Failure Mode** | Spatial undersampling |
| **Formula** | Fix L, decrease Δx (increase N). Regenerate field from FieldSource. Compare output at common ROI. |
| **Applicability** | Requires FieldSource (not raw array) |
| **Required Inputs** | FieldSource, Grid sequence (1×, 2×, 4× resolution), propagator, tolerance |
| **Threshold** | User-defined relative tolerance |
| **Threshold Provenance** | USER_DEFINED |
| **Source** | Numerical analysis — Richardson-type convergence |
| **Validation** | Well-resolved benchmark should converge |
| **False Positive** | Convergence in intensity may hide phase errors |
| **False Negative** | May not detect aliasing if initial grid is too coarse |
| **Recommended Action** | Essential check; combine with diagnostics |

---

### C13 — Physical-Domain Convergence

| Field | Value |
|---|---|
| **ID** | `convergence.domain` |
| **Type** | CONVERGENCE |
| **Failure Mode** | Finite-domain truncation error |
| **Formula** | Fix Δx, increase L (increase N). For non-compact fields: regenerate from FieldSource on larger grid. Compare at common ROI. |
| **Applicability** | All methods |
| **Required Inputs** | FieldSource or compact-support indicator, Grid sequence, propagator, tolerance |
| **Threshold** | User-defined relative tolerance |
| **Threshold Provenance** | USER_DEFINED |
| **Source** | Numerical analysis |
| **Validation** | Large-domain benchmark should converge |
| **False Positive** | Convergence at small ROI may miss edge effects |
| **False Negative** | May converge to wrong result if other issues present |
| **Recommended Action** | Essential check |

---

### C14 — Algorithmic Padding Convergence

| Field | Value |
|---|---|
| **ID** | `convergence.padding` |
| **Type** | CONVERGENCE |
| **Failure Mode** | Circular convolution / periodic boundary artifact |
| **Formula** | Same physical problem; vary FFT padding factor (1×, 2×, 4×). Compare at common ROI. |
| **Applicability** | FFT-based methods (ASM, Fresnel) |
| **Required Inputs** | Field, Grid, padding factor sequence, propagator, tolerance |
| **Threshold** | User-defined relative tolerance |
| **Threshold Provenance** | USER_DEFINED |
| **Source** | FFT circular convolution theory |
| **Validation** | Compare with DI (no padding artifact) |
| **False Positive** | May converge quickly if field is well-contained |
| **False Negative** | N/A |
| **Recommended Action** | Standard FFT validation |

---

### C15 — Output-Grid Convergence (Conditional)

| Field | Value |
|---|---|
| **ID** | `convergence.output_grid` |
| **Type** | CONVERGENCE |
| **Failure Mode** | Output interpolation error |
| **Formula** | Fix physical observation window; decrease Δx_out. Compare at common ROI. |
| **Applicability** | Only when propagator supports different output grid |
| **Required Inputs** | Field, Grid, output grid sequence, propagator, tolerance |
| **Threshold** | User-defined relative tolerance |
| **Threshold Provenance** | USER_DEFINED |
| **Source** | Numerical analysis |
| **Validation** | Refine output sampling to convergence |
| **False Positive** | N/A |
| **False Negative** | N/A |
| **Recommended Action** | Conditional; not required for same-grid ASM |

---

### C16 — Reference Agreement

| Field | Value |
|---|---|
| **ID** | `reference.agreement` |
| **Type** | CROSS_REFERENCE |
| **Failure Mode** | Aggregate discrepancy with independent computation |
| **Formula** | Intensity relative error, complex-field relative error (with global phase alignment), phase error at user-specified tolerance |
| **Applicability** | When an independent reference is available |
| **Required Inputs** | Two fields on compatible grids, tolerance |
| **Threshold** | User-defined tolerance |
| **Threshold Provenance** | USER_DEFINED |
| **Source** | Numerical analysis |
| **Validation** | Benchmark cases |
| **False Positive** | Agreement at one z does not guarantee all z |
| **False Negative** | Disagreement may come from reference limitations |
| **Recommended Action** | Verify reference itself has converged |

---

## Reference Hierarchy (for Cross-Reference)

Priority order:

1. Analytic / semi-analytic reference
2. Independently converged high-accuracy numerical reference
3. Independently implemented alternative method
4. Same-library alternative method

---

## References

1. **Matsushima & Shimobaba** (2009). "Band-Limited Angular Spectrum Method for Numerical Simulation of Free-Space Propagation in Far and Near Fields." *Optics Express* 17, 19662–19673. DOI: [10.1364/OE.17.019662](https://doi.org/10.1364/OE.17.019662)

2. **Shen & Wang** (2006). "Fast-Fourier-transform based numerical integration method for the Rayleigh–Sommerfeld diffraction formula." *Applied Optics* 45, 1102–1110. DOI: [10.1364/AO.45.001102](https://doi.org/10.1364/AO.45.001102)

3. **Voelz & Roggemann** (2009). "Digital simulation of scalar optical diffraction: revisiting chirp function sampling criteria and consequences." *Applied Optics* 48, 6132–6142. DOI: [10.1364/AO.48.006132](https://doi.org/10.1364/AO.48.006132)

4. **waveprop** library — [GitHub](https://github.com/ebezzam/waveprop). Implements ASM (with BLAS), Fresnel, Fraunhofer, DI, FFT-DI. Dimension convention: first axis = y, second axis = x. Uses fftshift-centred FT convention.
