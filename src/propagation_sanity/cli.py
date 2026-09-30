"""Command-line interface for Numerical Optical Propagation Sanity Check.

Provides commands to run validation checks and benchmark suites,
outputting formatted terminal reports or JSON.
"""

from __future__ import annotations

import argparse
import sys
import json

from propagation_sanity.core.propagation_config import PropagationMethod
from propagation_sanity.benchmarks.square_aperture import (
    build_square_aperture_contract,
    run_square_aperture_suite,
)
from propagation_sanity.benchmarks.accelerating_beam import (
    build_airy_beam_contract,
    run_airy_beam_suite,
)
from propagation_sanity.validate import validate


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="propagation-sanity",
        description="Numerical Scalar Wave Propagation Sanity Check Toolkit",
    )
    subparsers = parser.add_subparsers(dest="command", help="Sub-commands")

    # Command: check / validate
    check_p = subparsers.add_parser("check", help="Run validation on a scenario")
    check_p.add_argument(
        "--scenario",
        choices=["square", "airy"],
        default="square",
        help="Predefined scenario (default: square)",
    )
    check_p.add_argument(
        "--z-mm",
        type=float,
        default=100.0,
        help="Propagation distance in mm (default: 100)",
    )
    check_p.add_argument(
        "--method",
        choices=["asm", "fresnel", "fraunhofer"],
        default="asm",
        help="Propagation method (default: asm)",
    )
    check_p.add_argument(
        "--bandlimit",
        action="store_true",
        help="Enable Matsushima BLAS (bandlimit=True)",
    )
    check_p.add_argument(
        "--convergence",
        action="store_true",
        help="Execute numerical convergence experiments",
    )
    check_p.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON report instead of text summary",
    )

    # Command: benchmark
    bench_p = subparsers.add_parser("benchmark", help="Run benchmark suite")
    bench_p.add_argument(
        "--scenario",
        choices=["square", "airy"],
        default="square",
        help="Benchmark scenario to run",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "check":
        z_m = args.z_mm * 1e-3
        method_map = {
            "asm": PropagationMethod.ASM,
            "fresnel": PropagationMethod.FRESNEL,
            "fraunhofer": PropagationMethod.FRAUNHOFER,
        }
        method = method_map[args.method]

        if args.scenario == "square":
            contract = build_square_aperture_contract(
                z=z_m,
                method=method,
                bandlimit=args.bandlimit,
            )
        else:
            contract = build_airy_beam_contract(
                z=z_m,
                method=method,
                bandlimit=args.bandlimit,
            )

        report = validate(contract, run_convergence=args.convergence)

        if args.json:
            print(report.to_json())
        else:
            print(report.summary())
        return 0

    elif args.command == "benchmark":
        if args.scenario == "square":
            print("Running Square Aperture Benchmark Suite across z = [1, 10, 100, 150] mm...\n")
            suite = run_square_aperture_suite()
            for key, data in suite.items():
                print(f"=== Scenario {key} (z = {data['z']*1e3:.0f} mm) ===")
                print(f"Analytic Fraunhofer first null : {data['fraunhofer_first_null']*1e6:.1f} μm")
                print(f"Standard ASM vs BLAS diff     : {data['blas_intensity_relative_diff']*100:.2f}%")
                print(f"Fresnel number N_F             : {data['fresnel_number']:.3f}\n")
        elif args.scenario == "airy":
            print("Running Airy Beam Acceleration Suite across z = [0, 5, 10, 20] mm...\n")
            suite = run_airy_beam_suite()
            for key, data in suite.items():
                print(f"=== Scenario {key} (z = {data['z']*1e3:.0f} mm) ===")
                print(f"Peak trajectory (x, y) : ({data['peak_x']*1e6:.1f} μm, {data['peak_y']*1e6:.1f} μm)\n")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
