"""Command-line interface for Numerical Optical Propagation Sanity Check.

Provides commands to run validation checks, benchmark suites, and view/render
validation JSON reports interactively or in the terminal.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from propagation_sanity.core.propagation_config import PropagationMethod
from propagation_sanity.core.report import ValidationReport
from propagation_sanity.benchmarks.square_aperture import (
    build_square_aperture_contract,
    run_square_aperture_suite,
)
from propagation_sanity.benchmarks.accelerating_beam import (
    build_airy_beam_contract,
    run_airy_beam_suite,
)
from propagation_sanity.validate import validate
from propagation_sanity.viewer import render_html, render_terminal, view


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
        help="Output raw JSON report to stdout",
    )
    check_p.add_argument(
        "-o",
        "--output",
        type=str,
        default=None,
        help="Save report to file (.json or .html)",
    )
    check_p.add_argument(
        "--html",
        type=str,
        default=None,
        help="Export interactive HTML report dashboard to specified path",
    )
    check_p.add_argument(
        "--browser",
        action="store_true",
        help="Open HTML dashboard report in web browser",
    )

    # Command: view
    view_p = subparsers.add_parser("view", help="Render/view an existing JSON validation report")
    view_p.add_argument(
        "report_file",
        type=str,
        help="Path to the JSON report file to view",
    )
    view_p.add_argument(
        "--format",
        choices=["html", "terminal"],
        default="terminal",
        help="Viewer mode: 'terminal' (default) or 'html'",
    )
    view_p.add_argument(
        "-o",
        "--output",
        type=str,
        default=None,
        help="Output path for rendered HTML report",
    )
    view_p.add_argument(
        "--browser",
        action="store_true",
        help="Automatically open HTML report in the default web browser",
    )

    # Command: benchmark
    bench_p = subparsers.add_parser("benchmark", help="Run benchmark suite")
    bench_p.add_argument(
        "--scenario",
        choices=["square", "airy"],
        default="square",
        help="Benchmark scenario to run",
    )
    bench_p.add_argument(
        "--json",
        action="store_true",
        help="Output benchmark results as JSON",
    )
    bench_p.add_argument(
        "-o",
        "--output",
        type=str,
        default=None,
        help="Save benchmark results to JSON file",
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

        # Handle file saving
        if args.output:
            out_p = Path(args.output)
            if out_p.suffix.lower() == ".html":
                report.save_html(out_p)
                print(f"Report HTML dashboard saved to {out_p}")
            else:
                report.save_json(out_p)
                print(f"Report JSON saved to {out_p}")

        if args.html:
            report.save_html(args.html)
            print(f"Interactive HTML dashboard saved to {args.html}")

        if args.browser:
            report.view(format="html", open_browser=True, output_path=args.html or args.output)

        # Output to stdout if not browser/file-only or if specifically asked
        if args.json:
            print(report.to_json())
        elif not args.output and not args.html and not args.browser:
            print(report.summary())
        return 0

    elif args.command == "view":
        report_path = Path(args.report_file)
        if not report_path.exists():
            print(f"Error: Report file not found: {report_path}", file=sys.stderr)
            return 1

        fmt = "html" if args.browser else args.format
        view(
            report_or_data=report_path,
            format=fmt,
            output_path=args.output,
            open_browser=args.browser,
        )
        if args.output and fmt == "html":
            print(f"Rendered HTML saved to {args.output}")
        return 0

    elif args.command == "benchmark":
        suite = None
        if args.scenario == "square":
            suite = run_square_aperture_suite()
            if not args.json:
                print("Running Square Aperture Benchmark Suite across z = [1, 10, 100, 150] mm...\n")
                for key, data in suite.items():
                    print(f"=== Scenario {key} (z = {data['z']*1e3:.0f} mm) ===")
                    print(f"Analytic Fraunhofer first null : {data['fraunhofer_first_null']*1e6:.1f} μm")
                    print(f"Standard ASM vs BLAS diff     : {data['blas_intensity_relative_diff']*100:.2f}%")
                    print(f"Fresnel number N_F             : {data['fresnel_number']:.3f}\n")
        elif args.scenario == "airy":
            suite = run_airy_beam_suite()
            if not args.json:
                print("Running Airy Beam Acceleration Suite across z = [0, 5, 10, 20] mm...\n")
                for key, data in suite.items():
                    print(f"=== Scenario {key} (z = {data['z']*1e3:.0f} mm) ===")
                    print(f"Peak trajectory (x, y) : ({data['peak_x']*1e6:.1f} μm, {data['peak_y']*1e6:.1f} μm)\n")

        if args.json or args.output:
            # Prepare serializable suite dict
            serializable_suite = {}
            for k, v in suite.items():
                entry = dict(v)
                if "report" in entry and hasattr(entry["report"], "to_dict"):
                    entry["report"] = entry["report"].to_dict()
                serializable_suite[k] = entry

            json_str = json.dumps(serializable_suite, indent=2, default=str)
            if args.output:
                Path(args.output).write_text(json_str, encoding="utf-8")
                print(f"Benchmark suite JSON saved to {args.output}")
            if args.json:
                print(json_str)
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
