"""Optional visual summaries for one or more sanity reports."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import numpy as np

from .checks import STATUS_ORDER, check_by_name
from .types import SanityReport

STATUS_COLORS = {
    "INFO": "#64748b",
    "PASS": "#15803d",
    "SKIP": "#64748b",
    "WARN": "#b45309",
    "FAIL": "#b91c1c",
}


def render_status_matrix(
    reports,
    *,
    output_path: str | Path | None = None,
    title: str | None = None,
    figsize: tuple[float, float] = (7.2, 5.5),
    show: bool = False,
):
    """Render report statuses as rows of checks and columns of configurations."""

    if isinstance(reports, SanityReport):
        items = [("report", reports)]
    elif isinstance(reports, dict):
        items = list(reports.items())
    else:
        items = list(reports)
    if not items:
        raise ValueError("reports must contain at least one SanityReport")

    check_names = [check.name for check in items[0][1].checks]
    status_matrix = np.array(
        [
            [STATUS_ORDER[check_by_name(report, name).status] for _, report in items]
            for name in check_names
        ]
    )
    fig, ax = plt.subplots(figsize=figsize, constrained_layout=True)
    ax.imshow(
        status_matrix,
        cmap=ListedColormap(
            [STATUS_COLORS[status] for status in ("INFO", "PASS", "SKIP", "WARN", "FAIL")]
        ),
        vmin=0,
        vmax=4,
        aspect="auto",
    )
    ax.set_xticks(range(len(items)), [str(label) for label, _ in items], rotation=45, ha="right")
    ax.set_yticks(range(len(check_names)), check_names)
    for row, name in enumerate(check_names):
        for column, (_, report) in enumerate(items):
            ax.text(
                column,
                row,
                check_by_name(report, name).status,
                ha="center",
                va="center",
                color="white",
                fontsize=9,
                fontweight="bold",
            )
    if title:
        ax.set_title(title)
    if output_path is not None:
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(destination, dpi=180, bbox_inches="tight")
    if show:
        plt.show()
    return fig, ax

