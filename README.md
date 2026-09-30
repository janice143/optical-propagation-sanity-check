# Numerical Scalar Wave Propagation Sanity Check Toolkit

> **Primary Disclaimer:**  
> **This toolkit does not prove physical correctness.** It only provides evidence about numerical stability, sampling adequacy, and known discretization risks within the tested scalar wave propagation model.

---

## 1. Why This Project Exists

In computational optics, scalar diffraction simulations (such as the Angular Spectrum Method, Fresnel diffraction, or Rayleigh-Sommerfeld integration) are widely used in metasurface design, holography, beam propagation, and differentiable optical neural networks.

However, simulations routinely suffer from silent numerical failure modes:
1. **Chirp aliasing**: The transfer function oscillates faster than the Nyquist sampling rate (common in standard ASM at moderate-to-large distances).
2. **Circular convolution artifacts**: FFT-based methods assume periodic boundaries; without adequate zero-padding, diffracted energy wraps around.
3. **Domain truncation**: Non-compact beams or widely diffracted lobes truncate against the edge of the numerical window.
4. **Model approximation error**: Using the paraxial Fresnel approximation outside its validity domain.
5. **Numerical overfitting in inverse design**: Optimizers exploit spurious numerical artifacts (like unbandlimited ASM transfer function chirps) to achieve artificially low training losses.

This toolkit provides an **evidence-oriented validation framework** that detects, diagnoses, and reports these numerical risks before conclusions are drawn from simulations.

---

## 2. Quick Start (Python & CLI)

### Python API

```python
from propagation_sanity.core import (
    Grid, Wave, SquareAperture, PropagationConfig, PropagationMethod, SimulationContract
)
from propagation_sanity.validate import validate
from propagation_sanity.core.report import ValidationReport

# 1. Define the simulation contract
contract = SimulationContract(
    grid=Grid(nx=512, ny=512, dx=2e-6, dy=2e-6),
    wave=Wave(wavelength=532e-9),
    z=100e-3,  # 100 mm propagation
    propagation_config=PropagationConfig(method=PropagationMethod.ASM, bandlimit=False),
    source=SquareAperture(half_width=50e-6),
    characteristic_size=100e-6,
)

# 2. Run validation with convergence experiments
report = validate(contract, run_convergence=True)

# 3. Print terminal summary
print(report.summary())

# 4. Save structured JSON report
report.save("validation_report.json")

# 5. Export interactive Notion-style HTML dashboard
report.save_html("validation_dashboard.html")

# 6. View interactively in browser or terminal
# report.view(format="html", open_browser=True)  # Pops open browser
report.view(format="terminal")                 # Formatted box-drawn console view

# 7. Reload report anytime from JSON
loaded_report = ValidationReport.load("validation_report.json")
```

### Command Line Interface (CLI)

```bash
# Run validation check with terminal summary
propagation-sanity check --scenario square --z-mm 100

# Run validation and save structured JSON
propagation-sanity check --scenario square --z-mm 100 --convergence -o report.json

# Run validation and export Notion-style HTML visualizer
propagation-sanity check --scenario square --z-mm 100 --convergence --html dashboard.html

# Render existing JSON report in formatted terminal mode
propagation-sanity view report.json

# Render existing JSON report as interactive HTML dashboard and open browser
propagation-sanity view report.json --browser

# Convert existing JSON report to HTML file
propagation-sanity view report.json --format html -o dashboard.html

# Run benchmark suites and export results to JSON
propagation-sanity benchmark --scenario square -o square_benchmark.json
```

---

## 3. Reporting & Visualization Layer (Notion Style)

The toolkit features a dedicated **view layer** (`propagation_sanity.viewer`) designed in a **minimalist Notion aesthetic** (black-and-white, clean typography, spacious layout, zero loud neon elements).

### Core Viewer Capabilities

1. **Interactive Standalone HTML Dashboard (`html_viewer.py`)**:
   - **Self-contained**: Single HTML file with embedded report JSON data and pure SVG/CSS components. Operates offline without external web servers.
   - **Notion Page Properties**: Clean header displaying status badge, propagator method, distance ($z$), wavelength ($\lambda$), resolution, spatial extent ($L$), and Fresnel number ($N_F$).
   - **Executive Callout**: Distinct Notion callout block summarizing numerical health and actionable physical warnings.
   - **Convergence Progression Bars**: Minimalist step-by-step progress bars comparing intensity relative error across grid resolutions, physical domains, and FFT padding against the $1.0\%$ tolerance threshold.
   - **Spectral Support vs. Matsushima Limit**: Ruler-style spectrum diagram displaying the $99\%$ field energy boundary relative to the Matsushima admissible bandlimit ($f_{\text{limit}}$) and Nyquist frequency ($f_{\text{Nyq}}$).
   - **Toggle List Checklist (`▶ / ▼`)**: Notion-style collapsible list of all checks, complete with formula blocks, mathematical assumptions, physical interpretation, and literature citations.
   - **Universal Drag & Drop**: Drop **any** `*.json` report file directly into the browser window to instantly parse and visualize it client-side.
   - **Light / Dark Mode**: Full support for classic Notion white paper mode (`#ffffff`) and Notion dark mode (`#191919`).

2. **Formatted Terminal Viewer (`terminal_viewer.py`)**:
   - Clean Unicode box-drawing characters (`┌─┐`, `│`, `└─┘`).
   - Clear ANSI status indicators (`[ PASS ]`, `[ FAIL ]`, `[ CONVERGED ]`, `[ INFO ]`).
   - Automatic TTY detection with fallback to plain text when piped.

---

## 4. What This Project Can Validate

- **Sampling adequacy**: Whether spatial grid $\Delta x$ and frequency grid $\Delta f$ adequately capture the input field and propagation transfer function.
- **Matsushima BLAS sampling bounds**: Whether ASM transfer function chirp oscillations exceed the aliasing-free sampling bound.
- **Physical domain containment**: Whether energy leaks into the domain edges or diffracted lobes exceed the computation window.
- **Numerical convergence**: Whether results stabilize under grid refinement (resolution convergence), window enlargement (domain convergence), or FFT padding (algorithmic padding convergence).
- **Model validity indicator**: Discrepancy between ASM and the Fresnel paraxial approximation.

---

## 5. What It Cannot Validate

- **Vector / Maxwell physics**: Polarization, near-field evanescent coupling within sub-wavelength distances, or high-NA vector effects.
- **Medium inhomogeneities**: Complex inhomogeneous index distributions (FDTD/BPM scope).
- **Experimental reality**: Fabricated device aberrations, laser coherence length limits, detector noise.

---

## 6. Validation Hierarchy & Assessment Types

Checks are categorized strictly to avoid false confidence:

| Assessment Type | Meaning | Allowed Outputs |
|---|---|---|
| **DERIVED** | Exact analytical / DFT relations ($L = N\Delta x$, $\Delta f = 1/L$, $f_N = 1/(2\Delta x)$) | `INFO` |
| **DIAGNOSTIC** | Informative risk indicators (spectral edge energy, boundary energy, phase step) | `INFO` |
| **FORMAL_CRITERION** | Literature-derived mathematical bounds (e.g. Matsushima 2009 admissible band) | `PASS` / `FAIL` |
| **CONVERGENCE** | Refinement experiments (resolution, domain, padding) | `CONVERGED_AT_TOLERANCE` / `NOT_CONVERGED` / `UNVERIFIED` |
| **CROSS_REFERENCE** | Comparison against an independent baseline (DI, analytic, BLAS) | `AGREES_AT_TOLERANCE` / `DISAGREES` |
| **SCOPE_CHECK** | Checks if configuration exceeds scalar domain (e.g. evanescent dominance) | `INFO` / `OUT_OF_SCOPE` |

---

## 7. How to Interpret `UNVERIFIED`

If a convergence test returns `UNVERIFIED`:
- It means the toolkit did not have the necessary re-sampleable `FieldSource` to conduct refinement experiments (e.g. only an already-sampled array was supplied), or convergence execution was disabled (`run_convergence=False`).
- **`UNVERIFIED` is NOT a pass.** It explicitly informs the researcher that numerical stability has not yet been demonstrated at the requested tolerance.

---

## 8. Examples & Benchmarks

### Benchmark 1: Square Aperture Regression
Re-evaluates the classical square aperture ($N=512$, $\Delta x=2\,\mu\text{m}$, $\lambda=532\,\text{nm}$, $a=100\,\mu\text{m}$) across $z \in [1, 10, 100, 150]\,\text{mm}$:
```bash
propagation-sanity benchmark --scenario square
```
- At $z=1\,\text{mm}$: Standard ASM and BLAS match to $<0.01\%$.
- At $z=150\,\text{mm}$: Standard ASM suffers from severe chirp aliasing (discrepancy $>28\%$), while the Matsushima formal criterion flags `FAIL`.

### Benchmark 2: Self-Accelerating Airy Beam
Demonstrates non-compact field handling where physical-domain convergence requires field regeneration rather than simple zero-padding:
```bash
propagation-sanity benchmark --scenario airy
```

### Benchmark 3: Differentiable Optics Numerical Overfitting
Optimizes a phase element under a numerically weak propagator (unbandlimited ASM at large $z$) vs. a validated propagator (BLAS). Evaluating both designs under an independent, verified forward model proves that the weakly trained design suffered severe numerical overfitting.

---

## 9. Backends & Adapters

- **`WavepropAdapter` (`backend="waveprop"`)**: Production-ready CPU/NumPy propagation adapter supporting ASM, band-limited ASM (BLAS), single-step Fresnel, Fraunhofer, and Rayleigh–Sommerfeld Direct Integration (DI and FFT-DI).
- **`TorchOpticsAdapter` (`backend="torchoptics"`)**: PyTorch-native differentiable optics adapter cleanly decoupling field geometry (`Field`, `PlanarGrid`, `shape`, `spacing`) from propagation settings (`propagation_method`, `asm_pad`, output resampling). Supports ASM, DIM (impulse response convolution), Fresnel variants, Voelz critical distance automatic regime switching, and autograd gradient flow for inverse design.

---

## 10. References

1. **K. Matsushima and T. Shimobaba**, "Band-Limited Angular Spectrum Method for Numerical Simulation of Free-Space Propagation in Far and Near Fields," *Optics Express* 17, 19662–19673 (2009). DOI: [10.1364/OE.17.019662](https://doi.org/10.1364/OE.17.019662)
2. **F. Shen and A. Wang**, "Fast-Fourier-transform based numerical integration method for the Rayleigh–Sommerfeld diffraction formula," *Applied Optics* 45, 1102–1110 (2006). DOI: [10.1364/AO.45.001102](https://doi.org/10.1364/AO.45.001102)
3. **D. Voelz and M. Roggemann**, "Digital simulation of scalar optical diffraction: revisiting chirp function sampling criteria and consequences," *Applied Optics* 48, 6132–6142 (2009). DOI: [10.1364/AO.48.006132](https://doi.org/10.1364/AO.48.006132)
