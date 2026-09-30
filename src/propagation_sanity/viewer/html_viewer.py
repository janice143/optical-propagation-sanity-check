"""HTML visualizer and interactive report generator for numerical propagation sanity checks.

Generates self-contained, Notion-style minimalist black-and-white interactive reports
with clean typography, property lists, database-style filters, and drag-and-drop JSON loading.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional, Union


def render_html(
    report_or_data: Union[Dict[str, Any], str, Path, Any],
    output_path: Optional[Union[str, Path]] = None,
    title: str = "Optical Propagation Validation Report",
) -> str:
    """Generate an interactive standalone HTML report from validation data.

    Parameters
    ----------
    report_or_data : dict, str, Path, or ValidationReport
        The report data or file to render.
    output_path : str or Path, optional
        If provided, writes the rendered HTML to this path.
    title : str, optional
        Document title for the HTML viewer.

    Returns
    -------
    str
        The complete HTML string.
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

    json_str = json.dumps(data, indent=2, default=str)
    safe_json_str = json_str.replace("</script>", "<\\/script>")

    html_content = _build_html_template(data=data, json_str=safe_json_str, title=title)

    if output_path is not None:
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        with open(out_p, "w", encoding="utf-8") as f:
            f.write(html_content)

    return html_content


def _build_html_template(data: Dict[str, Any], json_str: str, title: str) -> str:
    """Construct the Notion-style minimalist black-and-white HTML template."""
    return f"""<!DOCTYPE html>
<html lang="en" class="light">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"></script>
  <style>
    :root {{
      --notion-bg: #ffffff;
      --notion-text: #37352f;
      --notion-text-muted: #787774;
      --notion-text-light: #9b9a97;
      --notion-border: #edece9;
      --notion-border-subtle: rgba(55, 53, 47, 0.08);
      --notion-card: #fcfcfb;
      --notion-hover: #f1f1ef;
      --notion-callout: #f7f6f5;
      --notion-code-bg: #f7f6f3;
      --tag-gray-bg: #e3e2e0;
      --tag-gray-text: #32302c;
      --tag-pass-bg: #e9f5ec;
      --tag-pass-text: #1e4620;
      --tag-fail-bg: #fbeae8;
      --tag-fail-text: #6e1c18;
      --tag-warn-bg: #fbf3db;
      --tag-warn-text: #594308;
    }}
    html.dark {{
      --notion-bg: #191919;
      --notion-text: #ebebeb;
      --notion-text-muted: #9b9b9b;
      --notion-text-light: #666666;
      --notion-border: #2a2a2a;
      --notion-border-subtle: rgba(255, 255, 255, 0.08);
      --notion-card: #202020;
      --notion-hover: #262626;
      --notion-callout: #222222;
      --notion-code-bg: #222222;
      --tag-gray-bg: #303030;
      --tag-gray-text: #d4d4d4;
      --tag-pass-bg: #1e2e22;
      --tag-pass-text: #8ce19e;
      --tag-fail-bg: #381e1d;
      --tag-fail-text: #f89490;
      --tag-warn-bg: #362915;
      --tag-warn-text: #f0c36d;
    }}
    body {{
      background-color: var(--notion-bg);
      color: var(--notion-text);
      font-family: ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, "Apple Color Emoji", Arial, sans-serif;
      line-height: 1.6;
      margin: 0;
      padding: 0;
      -webkit-font-smoothing: antialiased;
    }}
    .notion-tag {{
      display: inline-flex;
      align-items: center;
      padding: 2px 7px;
      font-size: 11px;
      font-weight: 500;
      border-radius: 3px;
      line-height: 16px;
      letter-spacing: -0.01em;
    }}
    .notion-property-row {{
      display: grid;
      grid-template-columns: 140px 1fr;
      align-items: baseline;
      padding: 4px 0;
      font-size: 13px;
    }}
    .notion-callout {{
      background-color: var(--notion-callout);
      border-radius: 4px;
      padding: 14px 16px;
      display: flex;
      align-items: flex-start;
      gap: 12px;
      border: 1px solid var(--notion-border-subtle);
    }}
    .notion-divider {{
      border-top: 1px solid var(--notion-border);
      margin: 24px 0;
    }}
    .notion-btn {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 4px 10px;
      font-size: 12px;
      font-weight: 500;
      color: var(--notion-text);
      background: transparent;
      border: 1px solid var(--notion-border);
      border-radius: 4px;
      cursor: pointer;
      transition: background 0.1s ease;
    }}
    .notion-btn:hover {{
      background-color: var(--notion-hover);
    }}
    .notion-toggle summary {{
      cursor: pointer;
      user-select: none;
      list-style: none;
      display: flex;
      align-items: center;
      gap: 6px;
    }}
    .notion-toggle summary::-webkit-details-marker {{
      display: none;
    }}
    .notion-toggle summary::before {{
      content: "▶";
      font-size: 9px;
      color: var(--notion-text-muted);
      transition: transform 0.15s ease;
      display: inline-block;
      width: 12px;
    }}
    .notion-toggle[open] summary::before {{
      transform: rotate(90deg);
    }}
    .notion-row {{
      border-bottom: 1px solid var(--notion-border);
      transition: background 0.1s ease;
    }}
    .notion-row:hover {{
      background-color: var(--notion-hover);
    }}
  </style>
</head>
<body class="p-6 sm:p-12 md:p-16">

  <!-- Embedded JSON Data Store -->
  <script id="report-data" type="application/json">
{json_str}
  </script>

  <div class="max-w-4xl mx-auto space-y-6">

    <!-- Notion Minimal Top Bar -->
    <div class="flex items-center justify-between pb-4 border-b border-[var(--notion-border)] text-xs text-[var(--notion-text-muted)]">
      <div class="flex items-center gap-2">
        <span class="font-medium text-[var(--notion-text)]">Workspace</span>
        <span>/</span>
        <span>Propagation Sanity Check</span>
        <span>/</span>
        <span id="breadcrumb-scenario" class="text-[var(--notion-text)]">Report</span>
      </div>
      <div class="flex items-center gap-2">
        <label class="notion-btn cursor-pointer">
          <span>Upload JSON</span>
          <input type="file" id="file-loader" accept=".json" class="hidden">
        </label>
        <button id="btn-export-json" class="notion-btn">
          <span>Export JSON</span>
        </button>
        <button id="btn-copy-json" class="notion-btn">
          <span id="copy-btn-text">Copy</span>
        </button>
        <button id="btn-theme-toggle" class="notion-btn" title="Toggle theme">
          <span id="theme-icon">🌙</span>
        </button>
      </div>
    </div>

    <!-- Drag & Drop Notification Banner (hidden by default) -->
    <div id="drop-indicator" class="hidden notion-callout border border-dashed border-[var(--notion-text-muted)]">
      <span class="text-base">📂</span>
      <p class="text-xs text-[var(--notion-text)]">Drop any JSON report file anywhere on this page to update view.</p>
    </div>

    <!-- Notion Page Header -->
    <div class="space-y-4 pt-2">
      <div class="text-4xl select-none" id="page-icon">🔬</div>
      <h1 class="text-3xl sm:text-4xl font-bold tracking-tight text-[var(--notion-text)]" id="page-title">
        Optical Propagation Validation Report
      </h1>
      <p class="text-sm text-[var(--notion-text-muted)]" id="page-subtitle">
        Evidence-oriented sampling check & numerical stability verification
      </p>
    </div>

    <!-- Notion Page Properties (Database Card Style) -->
    <div class="py-3 border-y border-[var(--notion-border)] space-y-1 font-sans">
      <div class="notion-property-row">
        <span class="text-[var(--notion-text-muted)] flex items-center gap-1.5 text-xs">
          <span>🏷️</span> Status
        </span>
        <div id="prop-status"></div>
      </div>
      <div class="notion-property-row">
        <span class="text-[var(--notion-text-muted)] flex items-center gap-1.5 text-xs">
          <span>⚙️</span> Propagator
        </span>
        <div class="text-xs font-mono text-[var(--notion-text)]" id="prop-method">-</div>
      </div>
      <div class="notion-property-row">
        <span class="text-[var(--notion-text-muted)] flex items-center gap-1.5 text-xs">
          <span>📏</span> Distance (z)
        </span>
        <div class="text-xs font-mono text-[var(--notion-text)]" id="prop-z">-</div>
      </div>
      <div class="notion-property-row">
        <span class="text-[var(--notion-text-muted)] flex items-center gap-1.5 text-xs">
          <span>💡</span> Wavelength (λ)
        </span>
        <div class="text-xs font-mono text-[var(--notion-text)]" id="prop-wavelength">-</div>
      </div>
      <div class="notion-property-row">
        <span class="text-[var(--notion-text-muted)] flex items-center gap-1.5 text-xs">
          <span>🔲</span> Grid Size
        </span>
        <div class="text-xs font-mono text-[var(--notion-text)]" id="prop-grid">-</div>
      </div>
      <div class="notion-property-row">
        <span class="text-[var(--notion-text-muted)] flex items-center gap-1.5 text-xs">
          <span>📐</span> Extent & Nyquist
        </span>
        <div class="text-xs font-mono text-[var(--notion-text)]" id="prop-extent">-</div>
      </div>
      <div class="notion-property-row">
        <span class="text-[var(--notion-text-muted)] flex items-center gap-1.5 text-xs">
          <span>🎯</span> Fresnel Number
        </span>
        <div class="text-xs font-mono text-[var(--notion-text)]" id="prop-nf">-</div>
      </div>
    </div>

    <!-- Executive Summary Callout Box -->
    <div id="summary-callout" class="notion-callout">
      <span class="text-lg select-none" id="callout-icon">ℹ️</span>
      <div class="space-y-1 text-xs">
        <div class="font-semibold text-[var(--notion-text)]" id="callout-title">Summary Statement</div>
        <p class="text-[var(--notion-text-muted)] leading-relaxed" id="callout-body">-</p>
      </div>
    </div>

    <!-- Notion Section: Convergence Progression -->
    <div class="space-y-3 pt-2">
      <div class="flex items-center justify-between">
        <h2 class="text-base font-semibold text-[var(--notion-text)] flex items-center gap-2">
          <span>📈</span> Convergence Progression
        </h2>
        <span class="text-xs text-[var(--notion-text-muted)] font-mono">Tolerance: 1.0%</span>
      </div>
      <div id="convergence-list" class="border border-[var(--notion-border)] rounded divide-y divide-[var(--notion-border)]">
        <!-- Rendered dynamically -->
      </div>
    </div>

    <!-- Notion Section: Spectral Support & Bandwidth -->
    <div class="space-y-3 pt-2">
      <div class="flex items-center justify-between">
        <h2 class="text-base font-semibold text-[var(--notion-text)] flex items-center gap-2">
          <span>📊</span> Spectral Support & Matsushima Bandlimit
        </h2>
        <span id="spectral-status-pill"></span>
      </div>
      <div id="spectral-block" class="border border-[var(--notion-border)] rounded p-4 space-y-3 bg-[var(--notion-card)]">
        <!-- Rendered dynamically -->
      </div>
    </div>

    <!-- Notion Section: Verification Database / Checklist -->
    <div class="space-y-3 pt-2">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <h2 class="text-base font-semibold text-[var(--notion-text)] flex items-center gap-2">
          <span>📋</span> All Verification Checks & Diagnostics
        </h2>

        <!-- Database Toolbar -->
        <div class="flex items-center gap-2 text-xs">
          <input type="text" id="search-input" placeholder="Filter checks..." 
            class="px-2.5 py-1 rounded border border-[var(--notion-border)] bg-transparent text-[var(--notion-text)] placeholder-[var(--notion-text-light)] focus:outline-none focus:border-[var(--notion-text)]">
          <select id="filter-type" class="px-2 py-1 rounded border border-[var(--notion-border)] bg-transparent text-[var(--notion-text)] focus:outline-none">
            <option value="all">All Types</option>
            <option value="formal_criterion">Formal Criteria</option>
            <option value="convergence">Convergence</option>
            <option value="diagnostic">Diagnostics</option>
            <option value="derived">Derived Grid</option>
          </select>
          <select id="filter-status" class="px-2 py-1 rounded border border-[var(--notion-border)] bg-transparent text-[var(--notion-text)] focus:outline-none">
            <option value="all">All Status</option>
            <option value="pass">Passed</option>
            <option value="fail">Failed</option>
            <option value="info">Info</option>
          </select>
        </div>
      </div>

      <!-- Checklist Items -->
      <div id="items-table" class="border border-[var(--notion-border)] rounded divide-y divide-[var(--notion-border)]">
        <!-- Rendered dynamically -->
      </div>
    </div>

    <!-- Notion Toggle: Raw JSON Source -->
    <details class="notion-toggle pt-4 text-xs">
      <summary class="font-medium text-[var(--notion-text-muted)] hover:text-[var(--notion-text)]">
        Raw JSON Source
      </summary>
      <div class="mt-3">
        <pre id="raw-json-pre" class="p-3 rounded text-[11px] font-mono bg-[var(--notion-code-bg)] border border-[var(--notion-border)] overflow-x-auto max-h-80 text-[var(--notion-text)]"></pre>
      </div>
    </details>

    <!-- Page Footer -->
    <div class="pt-8 pb-4 text-center text-xs text-[var(--notion-text-light)] border-t border-[var(--notion-border)]">
      Evidence-oriented scalar optical propagation sanity check • Minimalist report
    </div>

  </div>

  <!-- Interactive JavaScript Engine -->
  <script>
    let currentReport = null;

    function init() {{
      try {{
        const raw = document.getElementById('report-data').textContent;
        currentReport = JSON.parse(raw);
        renderReport(currentReport);
      }} catch (err) {{
        console.error('Failed to parse report data:', err);
      }}

      // Listeners
      document.getElementById('search-input').addEventListener('input', () => filterAndRenderItems());
      document.getElementById('filter-type').addEventListener('change', () => filterAndRenderItems());
      document.getElementById('filter-status').addEventListener('change', () => filterAndRenderItems());

      document.getElementById('file-loader').addEventListener('change', handleFileSelect);
      document.getElementById('btn-export-json').addEventListener('click', exportJSON);
      document.getElementById('btn-copy-json').addEventListener('click', copyJSON);
      document.getElementById('btn-theme-toggle').addEventListener('click', toggleTheme);

      // Drag & Drop
      window.addEventListener('dragover', (e) => {{
        e.preventDefault();
        document.getElementById('drop-indicator').classList.remove('hidden');
      }});
      window.addEventListener('dragleave', (e) => {{
        if (e.clientX === 0 && e.clientY === 0) {{
          document.getElementById('drop-indicator').classList.add('hidden');
        }}
      }});
      window.addEventListener('drop', (e) => {{
        e.preventDefault();
        document.getElementById('drop-indicator').classList.add('hidden');
        if (e.dataTransfer.files.length > 0) {{
          loadFile(e.dataTransfer.files[0]);
        }}
      }});
    }}

    function handleFileSelect(e) {{
      const file = e.target.files[0];
      if (file) loadFile(file);
    }}

    function loadFile(file) {{
      const reader = new FileReader();
      reader.onload = (e) => {{
        try {{
          const parsed = JSON.parse(e.target.result);
          currentReport = parsed;
          document.getElementById('report-data').textContent = JSON.stringify(parsed, null, 2);
          renderReport(parsed);
        }} catch (err) {{
          alert('Error parsing JSON: ' + err.message);
        }}
      }};
      reader.readAsText(file);
    }}

    function exportJSON() {{
      if (!currentReport) return;
      const blob = new Blob([JSON.stringify(currentReport, null, 2)], {{ type: 'application/json' }});
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'propagation_report.json';
      a.click();
      URL.revokeObjectURL(url);
    }}

    function copyJSON() {{
      if (!currentReport) return;
      navigator.clipboard.writeText(JSON.stringify(currentReport, null, 2)).then(() => {{
        const btnText = document.getElementById('copy-btn-text');
        btnText.textContent = 'Copied ✓';
        setTimeout(() => {{ btnText.textContent = 'Copy'; }}, 2000);
      }});
    }}

    function toggleTheme() {{
      const html = document.documentElement;
      const isDark = html.classList.contains('dark');
      if (isDark) {{
        html.classList.remove('dark');
        html.classList.add('light');
        document.getElementById('theme-icon').textContent = '🌙';
      }} else {{
        html.classList.remove('light');
        html.classList.add('dark');
        document.getElementById('theme-icon').textContent = '☀️';
      }}
    }}

    function renderReport(report) {{
      const meta = report.metadata || {{}};
      const results = report.results || [];
      const summary = report.summary || {{}};

      document.getElementById('raw-json-pre').textContent = JSON.stringify(report, null, 2);

      const method = (meta.method || 'unknown').toUpperCase();
      const z_mm = (meta.z && meta.z.length) ? (meta.z[0] * 1e3).toFixed(1) + ' mm' : 'N/A';
      document.getElementById('breadcrumb-scenario').textContent = `${{method}} (z = ${{z_mm}})`;
      document.getElementById('page-subtitle').textContent = `Method: ${{method}} • z = ${{z_mm}} • Backend: ${{meta.backend || 'default'}} • Padding: ${{meta.padding || 1.0}}x`;

      // Status check
      const criteria = results.filter(r => r.assessment_type === 'formal_criterion');
      const conv = results.filter(r => r.assessment_type === 'convergence');
      const hasFail = criteria.some(c => c.status === 'fail') || conv.some(c => c.status === 'not_converged');
      const allConvPassed = conv.length > 0 && conv.every(c => c.status === 'converged_at_tolerance');

      let statusPill = '';
      let calloutIcon = 'ℹ️';
      let calloutTitle = 'Diagnostic Status';
      let calloutText = '';

      if (hasFail) {{
        statusPill = '<span class="notion-tag" style="background: var(--tag-fail-bg); color: var(--tag-fail-text);">Issues Detected</span>';
        calloutIcon = '⚠️';
        calloutTitle = 'Numerical Risks Present';
        calloutText = 'At least one formal criterion or convergence test failed. Chirp aliasing or window truncation is active at this distance.';
      }} else if (allConvPassed) {{
        statusPill = '<span class="notion-tag" style="background: var(--tag-pass-bg); color: var(--tag-pass-text);">Validated</span>';
        calloutIcon = '✅';
        calloutTitle = 'Numerical Stability Supported';
        calloutText = 'All tested convergence experiments and formal criteria passed at the requested tolerance level.';
      }} else {{
        statusPill = '<span class="notion-tag" style="background: var(--tag-gray-bg); color: var(--tag-gray-text);">Unverified / Info</span>';
        calloutIcon = 'ℹ️';
        calloutTitle = 'Diagnostic Scan Complete';
        calloutText = 'Static criteria evaluated. Run with --convergence to verify resolution and domain stability bounds.';
      }}

      document.getElementById('prop-status').innerHTML = statusPill;
      document.getElementById('callout-icon').textContent = calloutIcon;
      document.getElementById('callout-title').textContent = calloutTitle;
      document.getElementById('callout-body').textContent = calloutText;

      document.getElementById('prop-method').textContent = `${{method}} (${{meta.bandlimit ? 'BLAS Bandlimited' : 'Standard Unbandlimited'}})`;
      document.getElementById('prop-z').textContent = z_mm;
      document.getElementById('prop-wavelength').textContent = meta.wavelength ? `${{(meta.wavelength * 1e9).toFixed(1)}} nm` : '-';
      document.getElementById('prop-grid').textContent = `${{meta.nx || '-'}} × ${{meta.ny || '-'}} (Δx = ${{meta.dx ? (meta.dx*1e6).toFixed(2) + ' μm' : '-'}})`;
      document.getElementById('prop-extent').textContent = `L = ${{meta.Lx ? (meta.Lx*1e3).toFixed(2) + ' mm' : '-'}} • Nyquist = ${{meta.nyquist_x ? (meta.nyquist_x*1e-3).toFixed(1) + ' c/mm' : '-'}}`;

      const fnItem = results.find(r => r.id === 'model.fresnel_number');
      document.getElementById('prop-nf').textContent = fnItem && typeof fnItem.value === 'number' ? fnItem.value.toFixed(4) : '-';

      // Convergence list
      renderConvergenceSection(conv);

      // Spectral ruler
      renderSpectralSection(results, meta);

      // Database items
      filterAndRenderItems();
    }}

    function renderConvergenceSection(convItems) {{
      const container = document.getElementById('convergence-list');
      container.innerHTML = '';

      if (!convItems || convItems.length === 0) {{
        container.innerHTML = '<div class="p-4 text-xs text-[var(--notion-text-muted)] italic text-center">No convergence experiments recorded in this run.</div>';
        return;
      }}

      convItems.forEach(item => {{
        const row = document.createElement('div');
        row.className = 'p-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs';

        const val = item.value || {{}};
        const errors = val.errors || [];
        const tol = val.tolerance || 0.01;
        const isPassed = item.status === 'converged_at_tolerance';

        const tag = isPassed ? 
          '<span class="notion-tag" style="background: var(--tag-pass-bg); color: var(--tag-pass-text);">Converged</span>' :
          '<span class="notion-tag" style="background: var(--tag-fail-bg); color: var(--tag-fail-text);">Not Converged</span>';

        let errSummary = '';
        if (errors.length > 0) {{
          const lastErr = errors[errors.length - 1].intensity_relative_error || 0;
          errSummary = `<span class="font-mono ${{isPassed ? 'text-[var(--notion-text)]' : 'font-semibold'}}" style="${{isPassed ? '' : 'color: var(--tag-fail-text);'}}">Final Error: ${{(lastErr * 100).toFixed(2)}}%</span>`;
        }} else {{
          errSummary = '<span class="text-[var(--notion-text-light)]">Not evaluated</span>';
        }}

        row.innerHTML = `
          <div class="flex items-center gap-3">
            ${{tag}}
            <span class="font-medium text-[var(--notion-text)]">${{item.title}}</span>
          </div>
          <div class="flex items-center gap-4 text-xs">
            ${{errSummary}}
            <span class="text-[var(--notion-text-muted)] font-mono">Tol: ${{(tol * 100).toFixed(1)}}%</span>
          </div>
        `;
        container.appendChild(row);
      }});
    }}

    function renderSpectralSection(results, meta) {{
      const container = document.getElementById('spectral-block');
      const pill = document.getElementById('spectral-status-pill');
      container.innerHTML = '';

      const matsuItem = results.find(r => r.id === 'asm.admissible_band');
      const bwItem = results.find(r => r.id === 'spectrum.effective_bandwidth');
      const nyquist = meta.nyquist_x || 250000;

      if (!matsuItem && !bwItem) {{
        container.innerHTML = '<div class="text-xs text-[var(--notion-text-muted)] italic">Spectral boundary diagnostics not available.</div>';
        return;
      }}

      let fx_limit = 0;
      let f_99 = 0;
      if (matsuItem && matsuItem.value) {{
        fx_limit = matsuItem.value.fx_limit || 0;
        if (matsuItem.value.field_effective_support) {{
          f_99 = matsuItem.value.field_effective_support.x_99_percent_freq || 0;
        }}
      }}
      if (!f_99 && bwItem && bwItem.value && bwItem.value.radial) {{
        f_99 = bwItem.value.radial['99.0%'] || 0;
      }}

      const withinLimit = f_99 <= fx_limit;
      if (pill) {{
        pill.innerHTML = withinLimit ? 
          '<span class="notion-tag" style="background: var(--tag-pass-bg); color: var(--tag-pass-text);">Within Bandlimit</span>' :
          '<span class="notion-tag" style="background: var(--tag-fail-bg); color: var(--tag-fail-text);">Chirp Aliasing Risk</span>';
      }}

      const pctMatsu = Math.min(100, (fx_limit / nyquist) * 100).toFixed(1);
      const pctField = Math.min(100, (f_99 / nyquist) * 100).toFixed(1);

      container.innerHTML = `
        <div class="space-y-2">
          <div class="h-2 w-full bg-[var(--notion-border)] rounded-full relative overflow-hidden">
            <div class="absolute top-0 bottom-0 bg-[var(--notion-text-muted)] opacity-30 rounded-full" style="width: ${{pctMatsu}}%"></div>
            <div class="absolute top-0 bottom-0 bg-[var(--notion-text)] opacity-80 rounded-full" style="width: ${{pctField}}%"></div>
          </div>
          <div class="flex justify-between text-[11px] font-mono text-[var(--notion-text-muted)] pt-0.5">
            <span>0 c/mm</span>
            <span>Matsushima Limit: ${{(fx_limit * 1e-3).toFixed(1)}} c/mm (${{pctMatsu}}%)</span>
            <span>99% Field Energy: ${{(f_99 * 1e-3).toFixed(1)}} c/mm (${{pctField}}%)</span>
            <span>f_Nyq: ${{(nyquist * 1e-3).toFixed(1)}} c/mm</span>
          </div>
        </div>
        <p class="text-xs text-[var(--notion-text-muted)] leading-relaxed pt-1">
          ${{withinLimit ? 
            '✓ Field spectral energy is contained within the Matsushima admissible band. Sampling rate is sufficient.' : 
            '✕ Field spectral energy exceeds the Matsushima limit. Transfer function oscillations exceed the Nyquist rate (chirp aliasing). Enable BLAS or increase padding.'}}
        </p>
      `;
    }}

    function filterAndRenderItems() {{
      if (!currentReport) return;
      const query = (document.getElementById('search-input').value || '').toLowerCase();
      const typeFilter = document.getElementById('filter-type').value;
      const statusFilter = document.getElementById('filter-status').value;

      const items = currentReport.results || [];
      const filtered = items.filter(it => {{
        if (typeFilter !== 'all' && it.assessment_type !== typeFilter) return false;
        if (statusFilter === 'pass' && !['pass', 'converged_at_tolerance'].includes(it.status)) return false;
        if (statusFilter === 'fail' && !['fail', 'not_converged'].includes(it.status)) return false;
        if (statusFilter === 'info' && it.status !== 'info') return false;

        if (query) {{
          const text = `${{it.title || ''}} ${{it.id || ''}} ${{it.category || ''}} ${{it.interpretation || ''}}`.toLowerCase();
          if (!text.includes(query)) return false;
        }}
        return true;
      }});

      const container = document.getElementById('items-table');
      container.innerHTML = '';

      if (filtered.length === 0) {{
        container.innerHTML = '<div class="p-6 text-xs text-[var(--notion-text-muted)] italic text-center">No checks matching current filters.</div>';
        return;
      }}

      filtered.forEach(it => {{
        const row = document.createElement('details');
        row.className = 'notion-toggle p-3 notion-row text-xs';

        let tag = '';
        if (['pass', 'converged_at_tolerance'].includes(it.status)) {{
          tag = '<span class="notion-tag" style="background: var(--tag-pass-bg); color: var(--tag-pass-text);">PASS</span>';
        }} else if (['fail', 'not_converged'].includes(it.status)) {{
          tag = '<span class="notion-tag" style="background: var(--tag-fail-bg); color: var(--tag-fail-text);">FAIL</span>';
        }} else {{
          tag = `<span class="notion-tag" style="background: var(--tag-gray-bg); color: var(--tag-gray-text);">${{it.status.toUpperCase()}}</span>`;
        }}

        let valStr = '';
        if (typeof it.value === 'object' && it.value !== null) {{
          valStr = `<span class="text-[var(--notion-text-muted)] font-mono">{...}</span>`;
        }} else {{
          const unit = it.unit ? ` ${{it.unit}}` : '';
          valStr = `<span class="font-mono font-medium text-[var(--notion-text)]">${{it.value}}${{unit}}</span>`;
        }}

        row.innerHTML = `
          <summary class="flex items-center justify-between cursor-pointer">
            <div class="flex items-center gap-2.5">
              ${{tag}}
              <span class="font-medium text-[var(--notion-text)]">${{it.title || it.id}}</span>
              <span class="text-[var(--notion-text-light)] font-mono text-[11px]">(${{it.id}})</span>
            </div>
            <div>${{valStr}}</div>
          </summary>
          <div class="mt-3 pl-4 space-y-2 border-l border-[var(--notion-border)] ml-1.5">
            ${{typeof it.value === 'object' && it.value !== null ? 
              `<pre class="p-2.5 rounded bg-[var(--notion-code-bg)] text-[11px] font-mono overflow-x-auto text-[var(--notion-text)] border border-[var(--notion-border)]">${{JSON.stringify(it.value, null, 2)}}</pre>` : ''}}
            ${{it.formula ? `<div class="text-[11px] font-mono text-[var(--notion-text-muted)]">Formula: ${{it.formula}}</div>` : ''}}
            ${{it.interpretation ? `<div class="text-xs text-[var(--notion-text)] leading-relaxed">${{it.interpretation}}</div>` : ''}}
            ${{it.recommended_action && it.status !== 'pass' && it.status !== 'converged_at_tolerance' ? `
              <div class="text-xs p-2 rounded bg-[var(--notion-callout)] border border-[var(--notion-border)] text-[var(--notion-text)]">
                <strong>Action:</strong> ${{it.recommended_action}}
              </div>` : ''}}
            ${{it.source ? `<div class="text-[11px] text-[var(--notion-text-light)]">Source: ${{it.source}}</div>` : ''}}
          </div>
        `;
        container.appendChild(row);
      }});
    }}

    window.addEventListener('DOMContentLoaded', init);
  </script>
</body>
</html>"""
