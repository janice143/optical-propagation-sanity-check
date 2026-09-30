---
name: mature-library-research
description: Boundary guidelines and checklist for researching mature optical propagation libraries (waveprop, TorchOptics, Diffractio, OpticStudio POP) without scope creep.
---

# Mature Library Research Skill

This skill guides agents when researching, evaluating, or writing adapters for external wave-optics libraries (`waveprop`, `TorchOptics`, `Diffractio`, `OpticStudio POP`).

## Core Directives & Hard Redlines

1. **Reference Only**: Mature libraries serve **strictly as engineering design and literature positioning references**.
2. **Anti-Scope Creep**: **NEVER expand the V1 scope** based on features found in surveyed libraries. Out-of-scope features (polarization, vector propagation, lens optimization, Maxwell/FDTD solvers, polychromatic propagation) must remain marked as `OUT_OF_SCOPE`.
3. **Core Independence**: The core validation engine must remain agnostic of backend structures. Third-party libraries are isolated behind backend adapters in `src/optical_propagation_sanity_check/adapters/`.

---

## Research Checklist per Library

When investigating any library, focus exclusively on the specific numerical dimensions listed below:

### 1. waveprop
- [ ] **Coordinate convention**: Row/y vs column/x indexing, origin centering (`np.arange(-N/2, N/2) * delta`).
- [ ] **Padding strategy**: How linear convolution is emulated (e.g. $2N \times 2N \to N \times N$ zero-padding & cropping).
- [ ] **Bandlimit**: Matsushima & Shimobaba (2009) BLAS filter design, cutoff frequency calculations.
- [ ] **DI (Direct Integration)**: Quadrature implementation, numerical baseline characteristics, FFT-DI (Shen & Wang 2006).
- [ ] **ASM**: Angular spectrum transfer function, evanescent wave damping.
- [ ] **Output coordinates**: Single-step / two-step Fresnel scaling vs fixed ASM spacing.

### 2. TorchOptics
- [ ] **Data model**: PyTorch tensor layout, batch dimensions, complex representation.
- [ ] **Grid representation**: Explicit coordinate grid tensors vs scalar sample intervals.
- [ ] **Padding**: Frequency/spatial padding implementations.
- [ ] **Output plane**: Variable sampling and custom detector pitch support.
- [ ] **Method selection**: Algorithmic thresholds for switching between ASM, Fresnel, and Fraunhofer.

### 3. Diffractio
- [ ] **`quality_factor` design**: Mathematical formulations of quality metrics.
- [ ] **User warning exposure**: How numerical warnings (aliasing, under-sampling) are surfaced to users in logs or outputs.

### 4. OpticStudio POP
- [ ] **Sampling vs Array Width**: Note that increasing array width is not an unconditional improvement (excessive width leads to inadequate beam sampling; insufficient width causes aliasing).
- [ ] **Guard band**: Recommended margin ratios to prevent boundary reflections/aliasing.
- [ ] **Engineering warnings**: Warning conditions for phase aliasing, beam edge clipping, and waist resolution.

---

## Workflow Instructions

When tasked with studying an external library:
1. **Target Inspection**: Limit source code inspection to the mathematical kernels, grid models, and boundary handlers.
2. **Record Findings**: Write or update summary notes under `docs/<library>-notes.md`.
3. **Quirks & Bugs**: Document any discovered upstream quirks, dtype casting issues, or edge cases.
4. **Adapter Mapping**: Map external inputs/outputs cleanly to the project's `FieldSource` and `Grid` contracts without altering the core contract.
