"""Benchmark scenarios and regression suites."""

from propagation_sanity.benchmarks.square_aperture import (
    build_square_aperture_contract,
    run_square_aperture_suite,
)
from propagation_sanity.benchmarks.accelerating_beam import (
    build_airy_beam_contract,
    run_airy_beam_suite,
)
from propagation_sanity.benchmarks.diff_optics import (
    run_differentiable_optics_comparison,
)

__all__ = [
    "build_square_aperture_contract",
    "run_square_aperture_suite",
    "build_airy_beam_contract",
    "run_airy_beam_suite",
    "run_differentiable_optics_comparison",
]
