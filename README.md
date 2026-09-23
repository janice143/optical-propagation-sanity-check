# Optical Propagation Sanity Check

A small Python package for asking a narrow but important question:

> Is this sampled field, finite window, propagation grid, and propagation model numerically credible for the experiment I am about to run?

The package turns the original exploratory notebook into reusable Python code. It reports six independent groups of evidence:

1. grid geometry;
2. input-field sampling;
3. finite window / field of view;
4. frequency-grid sampling;
5. transfer-function sampling;
6. propagation-model validity.

`PASS` means that none of the configured engineering criteria fired. It is not proof that an already sampled continuous field was alias-free before it reached the checker.

## Project layout

```text
optical-propagation-sanity-check/
├── src/propagation_sanity/   # importable package
├── examples/                 # runnable Python examples
├── tests/                    # pytest acceptance and unit tests
├── docs/api.html             # static, browser-readable API guide
├── pyproject.toml
└── README.md
```

This follows the useful separation in [waveprop](https://github.com/ebezzam/waveprop): library code, runnable examples, and tests live independently. Packaging uses a modern `pyproject.toml` and a `src/` layout.

## Install for development

From this directory:

```bash
python -m pip install -e ".[dev]"
```

If you are working from the parent numerical-calculation environment, the checks can also be run without installing:

```bash
PYTHONPATH=src ../.venv/bin/python -m pytest
```

## Minimal use

```python
import numpy as np

from propagation_sanity import GridSpec, PropagationSpec, sanity_check

field = np.ones((128, 128), dtype=np.complex128)
report = sanity_check(
    field,
    grid=GridSpec(dx=2e-6),
    propagation=PropagationSpec(wavelength=532e-9, z=10e-3),
)

print(report.to_text())
report.save_json("report.json")
```

The default model is band-limited angular-spectrum propagation without internal padding. Use `ASM_PADDED_MODEL` when the propagator should own zero padding, or pass a custom `PropagationModel` for another implementation.

## Run examples

```bash
PYTHONPATH=src ../.venv/bin/python examples/square_aperture.py
PYTHONPATH=src ../.venv/bin/python examples/custom_propagator.py
```

The square-aperture example writes JSON reports and a status matrix to `example-output/`.

## Run tests

```bash
PYTHONPATH=src ../.venv/bin/python -m pytest
```

The tests cover input validation, deterministic reports, rectangular grids, custom black-box propagators, report serialization, field-comparison invariance, and the public waveprop-backed models.

## Migrating from the notebook

The original `optical-propagation-sanity-check.ipynb` is intentionally left untouched as source history. Its main names are available from the package root. Canonical model names are `ASM_MODEL`, `ASM_PADDED_MODEL`, and `ASM_UNBANDED_MODEL`; the older notebook names `BLAS_MODEL`, `ASM_BANDLIMITED_PADDED_MODEL`, and `UNBANDED_ASM_MODEL` remain as aliases.

The notebook's downsampled direct-integration reference is exposed as `DIRECT_INTEGRATION_MODEL`. In the package version, downsampling is performed on a uniform physical grid and the actual coarse spacing is passed to waveprop, avoiding the false-resolution assumption that can arise from selecting sparse array indices while retaining the original `dx`.

## API guide

Open [`docs/api.html`](docs/api.html) directly in a browser. It is a standalone static file describing the public objects, extension contracts, statuses, metrics, and common calls.

## Scientific basis

- Voelz & Roggemann (2009), “Digital simulation of scalar optical diffraction: revisiting chirp function sampling criteria and consequences,” *Applied Optics* 48(32), 6132–6142. DOI: `10.1364/AO.48.006132`.
- Matsushima & Shimobaba (2009), “Band-Limited Angular Spectrum Method for Numerical Simulation of Free-Space Propagation in Far and Near Fields,” *Optics Express* 17(22), 19662–19673. DOI: `10.1364/OE.17.019662`.
- Shen & Wang (2006), “Fast-Fourier-transform based numerical integration method for the Rayleigh–Sommerfeld diffraction formula,” *Applied Optics* 45(6), 1102–1110. DOI: `10.1364/AO.45.001102`.

The thresholds are configurable engineering defaults, not universal physical laws.
