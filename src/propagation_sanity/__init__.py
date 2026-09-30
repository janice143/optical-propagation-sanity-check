"""Numerical Scalar Wave Propagation Sanity Check.

A validation toolkit for numerical reliability in scalar free-space
wave propagation. The toolkit checks sampling, finite-domain,
propagator discretization and propagation-model approximation risks,
and evaluates numerical convergence through controlled experiments.
"""

from propagation_sanity.core.report import ReportItem, ValidationReport
from propagation_sanity.validate import validate
from propagation_sanity.viewer import render_html, render_terminal, view

__version__ = "0.1.0"

__all__ = [
    "validate",
    "ValidationReport",
    "ReportItem",
    "view",
    "render_html",
    "render_terminal",
]
