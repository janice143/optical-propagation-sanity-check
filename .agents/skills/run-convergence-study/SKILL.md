---
name: run-convergence-study
description: Design, execute, and analyze numerical convergence experiments (resolution, physical domain, algorithmic padding) for optical propagation.
---

# Run Convergence Study Skill

This skill guides agents in setting up and executing rigorous numerical convergence experiments using [`propagation_sanity.convergence.engine`](file:///Users/janicelan/obsidian/opticsMe/numerical-calculation/optical-propagation-sanity-check/src/propagation_sanity/convergence/engine.py).

## Background & Principles

Before running experiments, understand the three orthogonal convergence dimensions documented in detail in [references/convergence-taxonomy.md](file:///Users/janicelan/obsidian/opticsMe/numerical-calculation/optical-propagation-sanity-check/.agents/skills/run-convergence-study/references/convergence-taxonomy.md):
1. **Resolution Convergence**: Fixed physical domain $L$, decreasing $\Delta x$. Requires resampling from a continuous `FieldSource`.
2. **Physical-Domain Convergence**: Fixed $\Delta x$, increasing $L$. For noncompact beams (Gaussian, Airy), requires resampling from `FieldSource` (zero-padding is invalid).
3. **Algorithmic-Padding Convergence**: Fixed physical domain and $\Delta x$, increasing internal FFT zero-padding to eliminate circular wrap-around.

---

## Execution Workflow

### Step 1: Check Input Form & FieldSource
Verify whether the input is a regenerable `FieldSource` or a static discrete array.
- If static array without `FieldSource`: Resolution convergence cannot be performed. Return status `UNVERIFIED` for resolution convergence.
- If `FieldSource` is available: Proceed with full 3-axis convergence study.

### Step 2: Configure Base Simulation Parameters
Define the base grid, wave, distance, and configuration:
```python
from propagation_sanity.core.grid import Grid
from propagation_sanity.core.wave import Wave
from propagation_sanity.core.field import GaussianBeam  # or custom FieldSource
from propagation_sanity.core.propagation_config import PropagationConfig, PropagationMethod
from propagation_sanity.convergence.engine import (
    resolution_convergence,
    domain_convergence,
    padding_convergence,
    run_all_convergence,
)

grid = Grid(nx=512, ny=512, dx=2e-6, dy=2e-6)
wave = Wave(wavelength=532e-9)
source = GaussianBeam(waist_radius=50e-6)
config = PropagationConfig(method=PropagationMethod.ASM, backend="waveprop")
```

### Step 3: Run Convergence Experiments
Execute the individual engines or all at once:
```python
results = run_all_convergence(
    source=source,
    base_grid=grid,
    wave=wave,
    z=50e-3,
    config=config,
    tolerance=0.01,  # 1% relative error threshold
)

for item in results:
    print(f"[{item.assessment_type.name}] {item.name}: {item.status.value}")
    print(f"  Details: {item.details}")
```

### Step 4: Interpret Results & Handle Failure Modes

1. **`NOT_CONVERGED` on Resolution**:
   - Cause: Spatial Nyquist sampling violated or rapid phase oscillations.
   - Action: Reduce $\Delta x$ (increase $N$), check Fresnel/ASM sampling limits.
2. **`NOT_CONVERGED` on Physical Domain**:
   - Cause: Field energy truncated at the computational window boundaries, generating spurious diffraction fringes.
   - Action: Increase physical window width $L$.
3. **`NOT_CONVERGED` on Algorithmic Padding**:
   - Cause: Circular convolution wrap-around artifacts contaminating the field ROI.
   - Action: Increase internal FFT padding factor (e.g. from 1.0 to 2.0).
