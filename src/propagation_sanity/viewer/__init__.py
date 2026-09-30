"""Viewer and visualization layer for numerical optical propagation validation reports.

Provides both interactive HTML dashboard rendering and ANSI/rich terminal viewing.
"""

from __future__ import annotations

import tempfile
import webbrowser
from pathlib import Path
from typing import Any, Dict, Optional, Union

from propagation_sanity.viewer.html_viewer import render_html
from propagation_sanity.viewer.terminal_viewer import render_terminal


def view(
    report_or_data: Union[Dict[str, Any], str, Path, Any],
    format: str = "html",
    output_path: Optional[Union[str, Path]] = None,
    open_browser: bool = False,
    color: Optional[bool] = None,
) -> str:
    """View and visualize a validation report in the requested format.

    Parameters
    ----------
    report_or_data : dict, str, Path, or ValidationReport
        The validation report to visualize.
    format : {"html", "terminal"}
        Output visualizer format.
    output_path : str or Path, optional
        Where to save rendered output (for HTML).
    open_browser : bool
        If True and format is "html", opens the dashboard in the default web browser.
    color : bool, optional
        Whether ANSI color codes are enabled for terminal output.

    Returns
    -------
    str
        Rendered output string (HTML or terminal text).
    """
    if format == "terminal":
        rendered = render_terminal(report_or_data, color=color)
        print(rendered)
        return rendered

    elif format == "html":
        if output_path is None and open_browser:
            # Create a temporary file to view in browser
            tmp = tempfile.NamedTemporaryFile(suffix=".html", delete=False)
            output_path = tmp.name
            tmp.close()

        rendered = render_html(report_or_data, output_path=output_path)

        if open_browser and output_path is not None:
            url = Path(output_path).resolve().as_uri()
            webbrowser.open(url)

        return rendered

    else:
        raise ValueError(f"Unknown format: {format!r}. Choose 'html' or 'terminal'.")


__all__ = [
    "render_html",
    "render_terminal",
    "view",
]
