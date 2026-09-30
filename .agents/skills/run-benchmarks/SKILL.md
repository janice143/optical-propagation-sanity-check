---
name: run-benchmarks
description: Execute standard benchmark suites (square aperture, Airy beam, differentiable optics) and verify deliberate failure modes and diagnostic reports.
---

# Run Benchmarks & Failure Modes Skill

This skill guides agents in running, analyzing, and validating regression benchmarks within `propagation_sanity.benchmarks`.

## Why Run Benchmarks?
Benchmarks are not just sanity checks; they systematically inject known numerical hazards (under-sampling, boundary wrap-around, beam window escape) to verify that our checkers detect them accurately without producing false passes.

Refer to [references/benchmarks-and-failure-modes.md](file:///Users/janicelan/obsidian/opticsMe/numerical-calculation/optical-propagation-sanity-check/.agents/skills/run-benchmarks/references/benchmarks-and-failure-modes.md) for full scenario physics and parameters.

---

## How to Execute Benchmarks

### 1. Square Aperture Regression
Verify near-field, mid-field, and far-field diffraction:
```python
from propagation_sanity.benchmarks.square_aperture import run_square_aperture_benchmark

# Runs z = [1mm, 10mm, 100mm, 150mm]
results = run_square_aperture_benchmark()
for r in results:
    print(f"z={r['z']*1e3:.1f} mm | ASM BLAS valid: {r['blas_valid']} | Diff to ref: {r['diff_norm']:.4e}")
```

### 2. Self-Accelerating Airy Beam
Verify transverse curved trajectory and window boundary leakage detection:
```python
from propagation_sanity.benchmarks.accelerating_beam import run_accelerating_beam_benchmark

results = run_accelerating_beam_benchmark()
print("Boundary leakage diagnostics across z:", results)
```

### 3. Differentiable Optics Contrast (Weak vs Supported)
Compare optimization behavior between numerically ill-posed and well-posed configurations:
```python
from propagation_sanity.benchmarks.diff_optics import run_diff_optics_comparison

summary = run_diff_optics_comparison()
print("Case A (Weak):", summary["case_a"])
print("Case B (Supported):", summary["case_b"])
```

---

## Verification Checklist for Agent
When reviewing benchmark outcomes:
- [ ] Ensure that for $z=100\,\mathrm{mm}$ with `bandlimit=False`, the Matsushima criterion reports `FAIL`.
- [ ] Ensure that for $z=100\,\mathrm{mm}$ with `bandlimit=True`, the Matsushima criterion reports `PASS`.
- [ ] Confirm that Airy beam lateral acceleration at large $z$ triggers a spatial boundary warning when energy approaches the edge.
- [ ] Confirm structured JSON reports serialize cleanly without NaNs or unpicklable objects.
