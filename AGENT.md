# Agent.md


## Project status

The V1 implementation (Phases 0 through 10) is complete: core data models, diagnostics, Matsushima formal criterion, convergence engines, waveprop adapter, benchmark suites (square aperture, Airy beam, differentiable optics), and CLI are implemented and verified with 103 automated tests. All user-facing code and documentation are self-contained without internal plan section references.

## Development commands

- Install runtime and test dependencies: `python -m pip install -e ".[dev]"`
- Run the complete test suite once tests exist: `python -m pytest`
- Run one test file: `python -m pytest tests/test_<area>.py`
- Run one test: `python -m pytest tests/test_<area>.py::test_<name>`
- Build a distribution: `python -m build`

Python 3.10+ is required. Hatchling builds the package; runtime dependencies are NumPy, SciPy, Matplotlib, and waveprop. Pytest is configured to discover `tests/` and use `-ra`. No formatter, linter, type checker, coverage tool, console entry point, or CI workflow is currently configured.

## Scope and evidence semantics

This toolkit evaluates numerical reliability for monochromatic scalar 2D transverse fields under free-space FFT/diffraction propagation. Its initial methods are ASM, Fresnel, Fraunhofer, and Rayleigh–Sommerfeld/direct-integration references.

It provides evidence about stability under the tested discretization and tolerance; it must never claim that a result is physically correct. Polarization, vector/high-NA diffraction, Maxwell solvers, polychromatic propagation, lens/imaging validation, and experimental calibration are out of scope and should be reported as `OUT_OF_SCOPE` rather than absorbed into V1.

Keep these categories distinct throughout the API and reports:

- **Derived quantities:** exact grid facts, not PASS/FAIL.
- **Diagnostics:** explanatory risk indicators, normally `INFO`, not proof.
- **Formal criteria:** method-specific checks with verified assumptions, implementation, and literature/theoretical provenance.
- **Convergence:** stability under controlled discretization changes.
- **Cross-reference:** agreement with an analytic or independently converged reference.
- **Scope checks:** identify unsupported physical regimes.

Every threshold records provenance: `THEORETICAL`, `LITERATURE`, `PROJECT_DEFAULT`, or `USER_DEFINED`. Do not turn heuristics such as spectral-edge energy or ASM phase-step size into universal validity criteria. If a formal formula is uncertain, inspect the primary source, its assumptions and conventions, the backend implementation, and a numerical reproduction before implementing it; otherwise retain the result as a diagnostic or defer it.

## Intended architecture

Organize code by numerical responsibility, not by application case:

- **Core contract:** grids, sampled fields, regeneratable `FieldSource`, wave/propagation configuration, output plane, physical ROI, and structured report results.
- **Static diagnostics:** FFT/grid derived quantities, spectral and spatial-boundary measures, ASM analytical phase steps and evanescent content, and Fresnel/Fraunhofer regime information.
- **Metrics and coordinate alignment:** determine a common physical ROI and coordinates before calculating intensity, phase-aligned complex-field, phase-mask, or power metrics.
- **Convergence engine:** independently run resolution, physical-domain, algorithmic-padding, and—where supported—output-grid convergence.
- **Backend adapters:** isolate waveprop first and TorchOptics later behind one propagation contract. Adapters return complex output, physical x/y coordinates, and metadata.
- **References and reports:** represent the chain `contract → diagnostics → formal criteria → convergence → cross-reference`; support human-readable and JSON output.
- **Benchmarks/examples:** square aperture first, then self-accelerating-beam and differentiable-optics workflows, reusing the same validation core.

## Numerical invariants

- Define and test coordinate origin, rows/y vs. columns/x ordering, grid endpoints, FFT normalization, and shift conventions explicitly. Do not assume backend coordinate conventions match.
- A sampled array cannot establish whether continuous-to-discrete input aliasing already happened. Report input-resolution validation as `UNVERIFIED` unless a regeneratable `FieldSource` is available.
- Resolution convergence holds the physical window fixed while reducing spacing, and must resample the source on each refined grid.
- Physical-domain convergence holds spacing fixed while enlarging the physical window. For noncompact fields, zero-padding an old array is not domain enlargement; regenerate from `FieldSource`.
- Algorithmic-padding convergence keeps the physical problem fixed and changes only internal FFT padding. Do not merge it with physical-domain convergence.
- Preserve and report propagation-grid versus requested-output-grid geometry. Interpolation must be explicit and must not be misattributed to propagation error.
- Compare results over a common physical ROI, never merely matching array indices.
- Treat direct integration as a reference only after its own sampling, window, quadrature, and output-grid convergence are demonstrated.
- Benchmark references should default to float64/complex128 and record backend/package version, dtype, device, geometry, configuration, and tolerances for reproducibility.

## Implementation sequence

1. Audit candidate checks and create `docs/check-spec.md` before implementing formal checkers.
2. Build the core simulation contract.
3. Add derived quantities and static diagnostics independent of a propagator backend.
4. Implement physical-coordinate alignment and comparison metrics.
5. Implement resolution, domain, and padding convergence separately.
6. Add and test the waveprop adapter; add TorchOptics only for the differentiable-optics workflow.
7. Implement an ASM formal criterion only after reproducing its literature-derived behavior; otherwise retain diagnostics and convergence evidence.
8. Create the square-aperture regression with deliberate sampling, window, padding, and approximation failures before application demos.

## Testing expectations

Test grid identities, FFT/coordinate conventions, padding relationships, global-phase invariance of complex-field metrics, and scale invariance of normalized spectral diagnostics. Use synthetic numerical fields (band-limited fields, near-Nyquist sinusoids, plane waves) to test diagnostics themselves. Test convergence modes independently and include deliberate failure injection; a mitigation such as band-limiting must not convert evidence that the original setup failed into a PASS.

Each backend adapter needs coordinate, normalization, simple-propagation, and metadata tests.
 
## Documentation and Reference Hygiene
 
All source code, docstrings, unit tests, and user-facing documentation must be completely self-contained. Do not include internal references to private planning documents, chapter/section numbers (e.g. `§59`, `plan section 53`), or internal roadmaps. All mathematical formulations and physical concepts should be explained directly with standard physics/optics literature citations.