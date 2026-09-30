---
name: formula-audit
description: Verify mathematical formulas, physical conventions, and literature provenance before implementing or modifying optical propagation criteria.
---

# Formula Audit & Literature Provenance Skill

This skill guides agents when inspecting, implementing, or modifying physical formulas, criterion thresholds, or coordinate conventions in `propagation_sanity`.

## When to Use This Skill
- Adding a new validation check or diagnostic criterion.
- Encountering conflicting formulas across textbooks or repositories.
- Verifying sign conventions ($e^{-i\omega t}$ vs $e^{i\omega t}$) or Fourier transform normalizations.
- Reviewing PRs or code changes that touch numerical propagation kernels.

---

## 4-Step Formula Audit Protocol

Agents must complete all four steps before implementing any new numerical formula:

```
[ Step 1: Primary Source ] ──> [ Step 2: Assumptions ] ──> [ Step 3: Convention Align ] ──> [ Step 4: Tiny Reproduction ]
```

### Step 1: Trace to Primary Source
1. Find the earliest peer-reviewed paper defining the formula (refer to [references/literature-provenance.md](file:///Users/janicelan/obsidian/opticsMe/numerical-calculation/optical-propagation-sanity-check/.agents/skills/formula-audit/references/literature-provenance.md)).
2. Record the exact citation (Authors, Year, Journal, Volume, Equation Number).
3. Set `provenance=ThresholdProvenance.LITERATURE`.

### Step 2: Verify Underlying Assumptions
Check if the formula assumes:
- Paraxial regime ($\theta \ll 1$) or non-paraxial?
- Continuous space or discrete DFT grid?
- Monochromatic scalar wave or vector field?
- Homogeneous dielectric medium or vacuum?
If the user's simulation violates these assumptions, the check must report `OUT_OF_SCOPE` or `INFO`, never `FAIL`.

### Step 3: Align Sign & Coordinate Conventions
Cross-check against project invariants:
- Time dependency: $e^{-i\omega t} \implies$ propagation phase $+ikz$.
- 2D coordinate order: Array shape is `(ny, nx)` corresponding to $(y, x)$.
- Spatial frequency: $f_x = k_x / (2\pi) \in [-1/(2\Delta x), 1/(2\Delta x)]$.
- Continuous-discrete FT scale: $\Delta x \Delta y$ on forward FFT, $N_x N_y \Delta f_x \Delta f_y$ on IFFT.

### Step 4: Tiny Numerical Reproduction
Before incorporating into `src/`, verify the formula against an analytic case or small synthetic test (e.g. $64 \times 64$ grid).
- Confirm that changing grid units (e.g., m to mm) does not break dimensional scaling.
- Confirm that global constant phase shifts do not alter criterion outcomes.

---

## Prohibited Anti-Patterns
- **No Hallucinated Heuristics**: Do not invent arbitrary thresholds (e.g., "if boundary energy > 5%, throw FAIL"). Mark empirical hints as `AssessmentType.DIAGNOSTIC` with status `INFO`.
- **No Literature Guesswork**: If a paper's derivation is ambiguous, do not implement it as a `FORMAL_CRITERION`. Downgrade to `DIAGNOSTIC` or open an issue.
