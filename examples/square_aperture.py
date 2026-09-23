"""Compare two grid/padding choices for a square aperture."""

from pathlib import Path

from propagation_sanity import (
    ASM_MODEL,
    ASM_PADDED_MODEL,
    GridSpec,
    PropagationSpec,
    render_status_matrix,
    sanity_check,
    square_aperture,
)

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "example-output"
WAVELENGTH = 532e-9
DISTANCES = (1e-3, 10e-3, 100e-3, 150e-3)


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
        )
        distance_label = f"{z * 1e3:.0f} mm"
        reports[distance_label] = report
        report.save_json(OUTPUT_DIR / f"{label}-{z * 1e3:03.0f}mm.json")
        print(f"\n{label}: {distance_label}\n{report.to_text()}")
    render_status_matrix(
        reports,
        output_path=OUTPUT_DIR / f"{label}-status-matrix.png",
        title=f"{label}: {shape[0]} x {shape[1]}, {model.name}",
    )


if __name__ == "__main__":
    OUTPUT_DIR.mkdir(exist_ok=True)
    run_case("run1", (512, 512), ASM_MODEL)
    run_case("run2", (1024, 1024), ASM_PADDED_MODEL)
    print(f"\nArtifacts written to {OUTPUT_DIR}")

