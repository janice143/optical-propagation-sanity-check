"""Compare two grid/padding choices for a square aperture."""

from pathlib import Path

from propagation_sanity import (
    ASM_MODEL,
    ASM_PADDED_MODEL,
    ASM_UNBANDED_MODEL,
    GridSpec,
    PropagationSpec,
    SanityThresholds,
    render_status_matrix,
    sanity_check,
    square_aperture,
)

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "example-output"
WAVELENGTH = 532e-9
DISTANCES = (1e-3, 10e-3, 100e-3, 150e-3)

# This is an experiment-specific acceptance profile, derived from the article's
# square-aperture evidence. It is intentionally local to this example rather
# than silently weakening the package defaults:
# - ~0.42% Nyquist-edge energy was judged adequately sampled;
# - <=5% output-edge energy is acceptable for the displayed field of view;
# - BLAS is designed around an approximately pi transfer-phase step boundary.
ARTICLE_DEMO_THRESHOLDS = SanityThresholds(
    spectral_edge_warn=5e-3,
    spectral_edge_fail=1e-2,
    edge_energy_warn=5e-2,
    edge_energy_fail=1e-1,
    propagator_phase_warn_pi=1.0,
    propagator_phase_fail_pi=1.25,
)


def run_case(label, shape, model):
    grid = GridSpec(dx=2e-6, dy=2e-6, min_feature_size=100e-6)
    field = square_aperture(shape, grid, width=100e-6)
    reports = {}
    for z in DISTANCES:
        report = sanity_check(
            field,
            grid=grid,
            propagation=PropagationSpec(wavelength=WAVELENGTH, z=z),
            model=model,
            thresholds=ARTICLE_DEMO_THRESHOLDS,
        )
        distance_label = f"{z * 1e3:.0f} mm"
        reports[distance_label] = report
        report.save_json(OUTPUT_DIR / f"{label}-{z * 1e3:03.0f}mm.json")
        report.save_markdown(OUTPUT_DIR / f"{label}-{z * 1e3:03.0f}mm.md")
        print(f"\n{label}: {distance_label}\n{report.to_text()}")
    render_status_matrix(
        reports,
        output_path=OUTPUT_DIR / f"{label}-status-matrix.png",
        title=f"{label}: {shape[0]} x {shape[1]}, {model.name}",
    )
    return reports


def save_comparison_summary(run1_reports, run2_reports):
    lines = [
        "# Square aperture: Run 1 vs Run 2",
        "",
        "This is the human-facing decision summary. JSON files remain available for regression and audit use.",
        "",
        "## Decision table",
        "",
        "| Distance | Run 1: N=512, unbanded/unpadded ASM | Run 2: N=1024, BLAS + padding | Decision |",
        "|---:|---:|---:|---|",
    ]
    for distance_label in run1_reports:
        run1 = run1_reports[distance_label]
        run2 = run2_reports[distance_label]
        decision = (
            "Run 2 resolves the configured blockers."
            if run1.overall == "FAIL" and run2.overall == "PASS"
            else "Run 2 mitigates the blocker, but a sampling warning remains."
            if run1.overall == "FAIL" and run2.overall == "WARN"
            else "Both configurations are acceptable."
            if run1.overall == run2.overall == "PASS"
            else "Review the remaining warning."
            if run2.overall == "WARN"
            else "Run 2 still has a blocker."
        )
        lines.append(
            f"| {distance_label} | **{run1.overall}** | **{run2.overall}** | {decision} |"
        )

    lines.extend(
        [
            "",
            "## Run 2 propagator-sampling evidence",
            "",
            "| Distance | Raw active-spectrum phase step | BLAS-supported phase step | Retained spectral energy |",
            "|---:|---:|---:|---:|",
        ]
    )
    for distance_label, report in run2_reports.items():
        check = next(
            item for item in report.checks if item.name == "Propagator sampling"
        )
        raw = check.metrics["max_active_phase_step_over_pi"]
        supported = check.metrics["max_supported_phase_step_over_pi"]
        retained = check.metrics["retained_input_spectral_energy"]
        lines.append(
            f"| {distance_label} | {raw:.3f}π | {supported:.3f}π | {retained:.1%} |"
        )

    lines.extend(
        [
            "",
            "## Acceptance profile used by this example",
            "",
            "- Input spectral-edge energy: WARN at 0.5%, FAIL at 1%.",
            "- Output edge energy: WARN at 5%, FAIL at 10%.",
            "- Transfer-phase step: WARN at 1.0π, FAIL at 1.25π.",
            "- For BLAS models, raw and retained-support phase steps are evaluated separately. BLAS mitigation can reduce a raw FAIL to WARN, but cannot turn it into PASS.",
            "- Retained spectral energy is reported as evidence; no universal acceptance threshold is imposed on it.",
            "",
            "These are experiment-specific engineering thresholds, not universal constants.",
            "",
        ]
    )
    (OUTPUT_DIR / "decision-summary.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    OUTPUT_DIR.mkdir(exist_ok=True)
    run1_reports = run_case("run1", (512, 512), ASM_UNBANDED_MODEL)
    run2_reports = run_case("run2", (1024, 1024), ASM_PADDED_MODEL)
    save_comparison_summary(run1_reports, run2_reports)
    print(f"\nArtifacts written to {OUTPUT_DIR}")
    print(f"Start with the decision summary: {OUTPUT_DIR / 'decision-summary.md'}")
