"""Terminal-based viewer for numerical propagation validation reports.

Renders formatted, colorful (ANSI) or plain-text dashboards for terminals
with box-drawing characters and clear visual hierarchy.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


# ANSI color codes
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    BG_GREEN = "\033[42m\033[30m"
    BG_RED = "\033[41m\033[37m"
    BG_YELLOW = "\033[43m\033[30m"
    BG_BLUE = "\033[44m\033[37m"


def _format_val(val: Any) -> str:
    """Format arbitrary value for terminal display."""
    if isinstance(val, float):
        if abs(val) < 1e-3 or abs(val) > 1e4:
            return f"{val:.4e}"
        return f"{val:.4f}"
    if isinstance(val, dict):
        # Compact representation
        items = []
        for k, v in val.items():
            if isinstance(v, (int, float)):
                v_str = f"{v:.3e}" if isinstance(v, float) and (abs(v) < 1e-2 or abs(v) > 1e3) else str(v)
                items.append(f"{k}: {v_str}")
            elif isinstance(v, dict):
                items.append(f"{k}: {{...}}")
            elif isinstance(v, list):
                items.append(f"{k}: [{len(v)} items]")
            else:
                items.append(f"{k}: {v}")
        return ", ".join(items[:3]) + (", ..." if len(items) > 3 else "")
    if isinstance(val, list):
        if len(val) <= 4:
            return ", ".join(str(v) for v in val)
        return f"[{val[0]}, {val[1]}, ... ({len(val)} items)]"
    return str(val)


def render_terminal(
    report_or_data: Union[Dict[str, Any], str, Path, Any],
    color: Optional[bool] = None,
) -> str:
    """Render a validation report to a formatted terminal string.

    Parameters
    ----------
    report_or_data : dict, str, Path, or ValidationReport
        The report data to render.
    color : bool, optional
        Whether to enable ANSI color codes. If None, auto-detected from sys.stdout.

    Returns
    -------
    str
        Formatted terminal output string.
    """
    if hasattr(report_or_data, "to_dict"):
        data = report_or_data.to_dict()
    elif isinstance(report_or_data, (str, Path)):
        p = Path(report_or_data)
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = json.loads(str(report_or_data))
    elif isinstance(report_or_data, dict):
        data = report_or_data
    else:
        raise TypeError(f"Unsupported report data type: {type(report_or_data)}")

    if color is None:
        color = sys.stdout.isatty()

    def c(code: str, text: str) -> str:
        return f"{code}{text}{Colors.RESET}" if color else text

    metadata = data.get("metadata", {})
    results = data.get("results", [])
    summary = data.get("summary", {})

    lines: List[str] = []

    # 1. Top Banner
    w = 78
    lines.append(c(Colors.BOLD + Colors.CYAN, "╔" + "═" * (w - 2) + "╗"))
    title_text = "  NUMERICAL SCALAR WAVE PROPAGATION — VALIDATION REPORT  "
    pad_l = (w - 2 - len(title_text)) // 2
    pad_r = w - 2 - len(title_text) - pad_l
    lines.append(c(Colors.BOLD + Colors.CYAN, "║") + " " * pad_l + c(Colors.BOLD + Colors.WHITE, title_text) + " " * pad_r + c(Colors.BOLD + Colors.CYAN, "║"))
    lines.append(c(Colors.BOLD + Colors.CYAN, "╚" + "═" * (w - 2) + "╝"))

    # 2. Executive Status Summary
    # Check overall convergence status
    conv_items = [r for r in results if r.get("assessment_type") == "convergence"]
    criteria_items = [r for r in results if r.get("assessment_type") == "formal_criterion"]

    all_passed = True
    any_failed = False
    for it in conv_items:
        st = it.get("status", "")
        if st == "not_converged":
            any_failed = True
            all_passed = False
        elif st != "converged_at_tolerance":
            all_passed = False
    for it in criteria_items:
        st = it.get("status", "")
        if st == "fail":
            any_failed = True
            all_passed = False
        elif st != "pass":
            all_passed = False

    if conv_items or criteria_items:
        if all_passed:
            status_badge = c(Colors.BG_GREEN, "  PASS — NUMERICAL STABILITY SUPPORTED  ")
        elif any_failed:
            status_badge = c(Colors.BG_RED, "  FAIL — NUMERICAL ISSUES DETECTED  ")
        else:
            status_badge = c(Colors.BG_YELLOW, "  INCOMPLETE / UNVERIFIED  ")
    else:
        status_badge = c(Colors.BG_BLUE, "  INFO ONLY — NO CONVERGENCE TESTS  ")

    lines.append("")
    lines.append(f"  Overall Status: {status_badge}")
    lines.append("")

    # 3. Simulation & Grid Parameters
    lines.append(c(Colors.BOLD, "  ▶ SIMULATION CONTRACT"))
    lines.append("  " + "─" * (w - 4))
    
    meta_keys = [
        ("Method", metadata.get("method", "N/A")),
        ("Backend", metadata.get("backend", "N/A")),
        ("Bandlimit", metadata.get("bandlimit", "N/A")),
        ("Padding", metadata.get("padding", "N/A")),
        ("Wavelength", f"{metadata.get('wavelength', 0)*1e9:.1f} nm" if "wavelength" in metadata else "N/A"),
        ("Distance z", f"{metadata.get('z', [0])[0]*1e3:.1f} mm" if "z" in metadata and isinstance(metadata["z"], list) and metadata["z"] else "N/A"),
        ("Grid (Nx, Ny)", f"{metadata.get('nx', 'N/A')} × {metadata.get('ny', 'N/A')}"),
        ("Sampling (dx, dy)", f"{metadata.get('dx', 0)*1e6:.2f} × {metadata.get('dy', 0)*1e6:.2f} μm" if "dx" in metadata else "N/A"),
        ("Extent (Lx, Ly)", f"{metadata.get('Lx', 0)*1e3:.2f} × {metadata.get('Ly', 0)*1e3:.2f} mm" if "Lx" in metadata else "N/A"),
        ("Nyquist", f"{metadata.get('nyquist_x', 0)*1e-3:.1f} cycles/mm" if "nyquist_x" in metadata else "N/A"),
    ]

    # Two column layout
    for i in range(0, len(meta_keys), 2):
        k1, v1 = meta_keys[i]
        col1 = f"  • {c(Colors.DIM, k1 + ':'):<28} {v1:<18}"
        if i + 1 < len(meta_keys):
            k2, v2 = meta_keys[i + 1]
            col2 = f"• {c(Colors.DIM, k2 + ':'):<28} {v2}"
        else:
            col2 = ""
        lines.append(f"{col1} {col2}")
    lines.append("")

    # 4. Formal Criteria
    if criteria_items:
        lines.append(c(Colors.BOLD, "  ▶ FORMAL CRITERIA"))
        lines.append("  " + "─" * (w - 4))
        for it in criteria_items:
            st = it.get("status", "info")
            if st == "pass":
                badge = c(Colors.GREEN + Colors.BOLD, "[ PASS ]")
            elif st == "fail":
                badge = c(Colors.RED + Colors.BOLD, "[ FAIL ]")
            else:
                badge = c(Colors.YELLOW, f"[ {st.upper()} ]")
            
            title = it.get("title", it.get("id"))
            lines.append(f"  {badge} {c(Colors.BOLD, title)}")
            if it.get("interpretation"):
                lines.append(f"         {c(Colors.DIM, 'Notice:')} {it['interpretation']}")
            if it.get("recommended_action") and st == "fail":
                lines.append(f"         {c(Colors.YELLOW, 'Action:')} {it['recommended_action']}")
        lines.append("")

    # 5. Convergence Experiments
    if conv_items:
        lines.append(c(Colors.BOLD, "  ▶ CONVERGENCE EXPERIMENTS"))
        lines.append("  " + "─" * (w - 4))
        for it in conv_items:
            st = it.get("status", "")
            if st == "converged_at_tolerance":
                badge = c(Colors.GREEN + Colors.BOLD, "[ CONVERGED ]")
            elif st == "not_converged":
                badge = c(Colors.RED + Colors.BOLD, "[ NOT CONV  ]")
            else:
                badge = c(Colors.YELLOW, f"[ {st.upper()[:8]} ]")

            title = it.get("title", it.get("id"))
            raw_val = it.get("value")
            val = raw_val if isinstance(raw_val, dict) else {}
            tol = val.get("tolerance") or it.get("threshold") or 0.01
            errors = val.get("errors", []) if isinstance(val.get("errors"), list) else []
            last_err = errors[-1].get("intensity_relative_error") if errors else None

            err_str = f"Final Err: {last_err:.2e}" if last_err is not None else ""
            tol_str = f"Tol: {tol:.2e}" if isinstance(tol, (int, float)) else ""
            lines.append(f"  {badge} {c(Colors.BOLD, title):<26} {err_str:<20} {tol_str}")

            if it.get("interpretation"):
                lines.append(f"         {c(Colors.DIM, it['interpretation'])}")
        lines.append("")

    # 6. Key Diagnostics
    diag_items = [r for r in results if r.get("assessment_type") in ("diagnostic", "scope_check")]
    if diag_items:
        lines.append(c(Colors.BOLD, "  ▶ KEY DIAGNOSTICS & SAMPLING METRICS"))
        lines.append("  " + "─" * (w - 4))
        for it in diag_items:
            title = it.get("title", it.get("id"))
            val = it.get("value")
            unit = f" {it['unit']}" if it.get("unit") else ""

            # Specially format complex diagnostics
            if it.get("id") == "asm.phase_step" and isinstance(val, dict):
                val_disp = f"Max step: {val.get('max_phase_step_pi', 0):.2f} π ({val.get('max_phase_step', 0):.2f} rad)"
            elif it.get("id") == "spatial.paraxial_fov" and isinstance(val, dict):
                ratio = val.get("ratio_x", 0) * 100
                val_disp = f"f_safe/f_Nyq = {ratio:.2f}%"
            elif it.get("id") == "spectrum.effective_bandwidth" and isinstance(val, dict):
                r = val.get("radial", {})
                val_disp = f"99% width: {r.get('99.0%', 0)*1e-3:.1f} c/mm"
            elif it.get("id") == "model.fresnel_remainder" and isinstance(val, dict):
                val_disp = f"Max: {val.get('max_phase_error_pi', 0):.2f} π ({val.get('max_phase_error_rad', 0):.2f} rad)"
            else:
                val_disp = f"{_format_val(val)}{unit}"

            st = it.get("status", "info")
            st_flag = f" {c(Colors.YELLOW, '[WARN]')}" if st not in ("info", "pass") else ""
            lines.append(f"  • {c(Colors.CYAN, title):<28} : {val_disp}{st_flag}")
            if it.get("interpretation") and st != "info":
                lines.append(f"    {c(Colors.DIM, it['interpretation'])}")
        lines.append("")

    lines.append(c(Colors.DIM, "  " + "─" * (w - 4)))
    return "\n".join(lines)
