#!/usr/bin/env python3
"""Generate a self-contained HTML report from all AST comparison JSON files."""

import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List

DEFAULT_INPUT_DIR = "comparisons-ast"
DEFAULT_OUTPUT = "comparison_report.html"


def load_all_comparisons(input_dir: str) -> List[Dict[str, Any]]:
    """Recursively load every *.json file under input_dir."""
    root = Path(input_dir)
    comparisons: List[Dict[str, Any]] = []
    for path in sorted(root.rglob("*.json")):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["_source_file"] = str(path.relative_to(root))
            comparisons.append(data)
        except Exception as e:
            print(f"[!] Skipping {path}: {e}")
    return comparisons


_JS = r"""
// ── Helpers ──────────────────────────────────────────────────────────────────
function esc(s) {
  return String(s ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function val(v) {
  if (v === null || v === undefined) return '<span class="empty">—</span>';
  if (typeof v === 'object') return '<code style="font-size:11px;word-break:break-all">' + esc(JSON.stringify(v)) + '</code>';
  if (typeof v === 'boolean') return v
    ? '<span class="badge badge-ok">yes</span>'
    : '<span class="badge" style="background:rgba(248,113,113,.1);color:#f87171;border:1px solid rgba(248,113,113,.2)">no</span>';
  return '<span class="val">' + esc(v) + '</span>';
}
function badge(sig) {
  return '<span class="badge badge-' + sig + '">' + sig + '</span>';
}
function similarityColor(score) {
  if (score >= 80) return '#34d399';
  if (score >= 60) return '#fbbf24';
  return '#f87171';
}
function gaugeHTML(score) {
  const r = 24, cx = 30, cy = 30;
  const circ = 2 * Math.PI * r;
  const fill = (score / 100) * circ;
  const color = similarityColor(score);
  return '<div class="gauge-wrap">'
    + '<div class="gauge">'
    + '<svg width="60" height="60" viewBox="0 0 60 60">'
    + '<circle cx="' + cx + '" cy="' + cy + '" r="' + r + '" fill="none" stroke="#2e3350" stroke-width="5"/>'
    + '<circle cx="' + cx + '" cy="' + cy + '" r="' + r + '" fill="none" stroke="' + color + '" stroke-width="5"'
    + ' stroke-dasharray="' + fill.toFixed(1) + ' ' + circ.toFixed(1) + '" stroke-linecap="round"/>'
    + '</svg>'
    + '<div class="gauge-val" style="color:' + color + '">' + Math.round(score) + '%</div>'
    + '</div>'
    + '<div>'
    + '<div style="font-size:12px;font-weight:700;color:' + color + '">'
    + (score >= 80 ? 'Highly Similar' : score >= 60 ? 'Moderately Similar' : 'Quite Different')
    + '</div>'
    + '<div class="gauge-label">Semantic Similarity</div>'
    + '</div>'
    + '</div>';
}
function pills(arr, cls) {
  if (!arr || arr.length === 0) return '';
  return arr.map(function(x) { return '<span class="pill ' + cls + '">' + esc(x) + '</span>'; }).join('');
}
function diffSection(title, diff) {
  if (!diff) return '';
  const f1 = diff.only_in_first || [];
  const f2 = diff.only_in_second || [];
  const common = diff.common || [];
  if (f1.length === 0 && f2.length === 0 && common.length === 0) return '';
  let legend = '';
  if (f1.length || f2.length) {
    legend = '<div style="margin-top:6px;font-size:11px;color:var(--text-dim)">';
    if (f1.length) legend += '<span style="color:#f87171">&#9632; only in f1</span>&nbsp;&nbsp;';
    if (f2.length) legend += '<span style="color:#34d399">&#9632; only in f2</span>&nbsp;&nbsp;';
    if (common.length) legend += '<span style="color:#a5b4fc">&#9632; shared</span>';
    legend += '</div>';
  }
  return '<div class="diff-section">'
    + '<div class="diff-section-name">' + title + '</div>'
    + '<div class="pill-row">' + pills(f1,'pill-f1') + pills(f2,'pill-f2') + pills(common,'pill-common') + '</div>'
    + legend
    + '</div>';
}
function metricBar(label, v1, v2, unit, maxV) {
  const m = maxV || Math.max(v1, v2, 1);
  const pct1 = Math.min((v1 / m) * 100, 100).toFixed(1);
  const pct2 = Math.min((v2 / m) * 100, 100).toFixed(1);
  const n1 = (typeof v1 === 'number') ? v1.toFixed(1) : v1;
  const n2 = (typeof v2 === 'number') ? v2.toFixed(1) : v2;
  return '<div style="margin-bottom:14px;">'
    + '<div style="font-size:11px;color:var(--text-dim);margin-bottom:6px;text-transform:uppercase;letter-spacing:.5px">' + label + '</div>'
    + '<div class="metric-row"><div class="metric-label" style="font-size:12px">Function 1</div>'
    + '<div class="metric-bar-wrap"><div class="metric-bar" style="width:' + pct1 + '%;background:#7c6af7"></div></div>'
    + '<div class="metric-val">' + n1 + unit + '</div></div>'
    + '<div class="metric-row"><div class="metric-label" style="font-size:12px">Function 2</div>'
    + '<div class="metric-bar-wrap"><div class="metric-bar" style="width:' + pct2 + '%;background:#5b8dee"></div></div>'
    + '<div class="metric-val">' + n2 + unit + '</div></div>'
    + '</div>';
}

// ── Render card ───────────────────────────────────────────────────────────────
function renderCard(c, idx) {
  const f1 = c.function1 || '?';
  const f2 = c.function2 || '?';
  const ts = c.timestamp ? new Date(c.timestamp).toLocaleString() : '';
  const src = c._source_file || '';

  // Config diffs
  const diffs = (c.configuration && c.configuration.differences) || [];
  let cfgRows = '';
  if (diffs.length === 0) {
    cfgRows = '<tr><td colspan="4"><span class="badge badge-ok">Identical</span></td></tr>';
  } else {
    diffs.forEach(function(d) {
      cfgRows += '<tr>'
        + '<td class="field-name">' + esc(d.field) + '</td>'
        + '<td>' + val(d.function1_value) + '</td>'
        + '<td>' + val(d.function2_value) + '</td>'
        + '<td>' + badge(d.significance) + '</td>'
        + '</tr>';
    });
  }

  // Config overview
  const cfg1 = (c.configuration && c.configuration.function1) || {};
  const cfg2 = (c.configuration && c.configuration.function2) || {};
  let overviewRows = '';
  ['runtime','memory','timeout','architecture','handler'].forEach(function(f) {
    const v1 = cfg1[f], v2 = cfg2[f];
    const same = JSON.stringify(v1) === JSON.stringify(v2);
    overviewRows += '<tr>'
      + '<td class="field-name">' + esc(f) + '</td>'
      + '<td>' + val(v1) + '</td>'
      + '<td>' + val(v2) + '</td>'
      + '<td>' + (same ? '<span class="badge badge-ok">Same</span>' : badge('CRITICAL')) + '</td>'
      + '</tr>';
  });

  // Dependencies
  const dep = (c.dependencies && c.dependencies.comparison) || {};
  const depF1 = (c.dependencies && c.dependencies.function1) || {};
  const depF2 = (c.dependencies && c.dependencies.function2) || {};

  // Metrics
  const met1 = (c.metrics && c.metrics.function1) || {};
  const met2 = (c.metrics && c.metrics.function2) || {};
  const metComp = (c.metrics && c.metrics.comparison) || {};
  const maxCS = Math.max(met1.estimated_coldstart_time || 0, met2.estimated_coldstart_time || 0, 1);

  // Event sources
  const es1 = (c.event_sources && c.event_sources.function1) || ['Direct'];
  const es2 = (c.event_sources && c.event_sources.function2) || ['Direct'];
  function esBadge(s) {
    const cls = s === 'S3' ? 'badge-S3' : s === 'Api' ? 'badge-Api' : 'badge-default';
    return '<span class="badge ' + cls + '">' + esc(s) + '</span>';
  }

  // Dep packages
  const pkgs1 = (depF1.packages || []).map(function(p){ return '<code style="margin-right:6px;font-size:11px">' + esc(p) + '</code>'; }).join('');
  const pkgs2 = (depF2.packages || []).map(function(p){ return '<code style="margin-right:6px;font-size:11px">' + esc(p) + '</code>'; }).join('');

  let depUnique = '';
  if (dep.only_in_function1 && dep.only_in_function1.length) {
    depUnique += '<div style="margin-bottom:4px;font-size:12px"><span style="color:var(--text-dim)">Only in ' + esc(f1) + ':</span> '
      + dep.only_in_function1.map(function(p){ return '<span class="pill pill-f1" style="font-size:11px">' + esc(p) + '</span>'; }).join(' ')
      + '</div>';
  }
  if (dep.only_in_function2 && dep.only_in_function2.length) {
    depUnique += '<div style="font-size:12px"><span style="color:var(--text-dim)">Only in ' + esc(f2) + ':</span> '
      + dep.only_in_function2.map(function(p){ return '<span class="pill pill-f2" style="font-size:11px">' + esc(p) + '</span>'; }).join(' ')
      + '</div>';
  }

  // AST
  const ast = c.ast_analysis || {};
  const astComp = ast.comparison || {};
  const similarity = (astComp.semantic_similarity_score != null) ? astComp.semantic_similarity_score : 0;
  const astF1 = ast.function1 || null;
  const astF2 = ast.function2 || null;
  const complexityDiff = astComp.complexity_diff || {};
  const linesDiff = (astComp.lines_diff != null) ? astComp.lines_diff : 0;

  // Code structure section
  let codeStructureHTML = '<div class="section"><div class="section-title">Code Structure</div><p class="empty">AST data unavailable</p></div>';
  if (astF1 && astF2) {
    const c1 = complexityDiff.function1 || 0, c2 = complexityDiff.function2 || 0;
    const col1 = c1 > c2 ? 'var(--crit)' : 'var(--ok)';
    const col2 = c2 > c1 ? 'var(--crit)' : 'var(--ok)';
    let lineDiffHTML = '';
    if (linesDiff !== 0) {
      const lcolor = linesDiff > 0 ? 'var(--crit)' : 'var(--ok)';
      const lsign = linesDiff > 0 ? '+' : '';
      lineDiffHTML = '<div style="margin-top:10px;font-size:12px;color:var(--text-dim)">Code size difference: <strong style="color:' + lcolor + '">' + lsign + linesDiff + ' lines</strong></div>';
    }
    codeStructureHTML = '<div class="section">'
      + '<div class="section-title">Code Structure</div>'
      + '<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">'
      + '<div>'
      + '<div style="font-size:11px;color:var(--text-dim);font-weight:700;margin-bottom:8px;text-transform:uppercase">' + esc(f1) + '</div>'
      + '<div class="stats-grid">'
      + '<div class="stat-item"><div class="s-val">' + astF1.total_lines + '</div><div class="s-lbl">Lines</div></div>'
      + '<div class="stat-item"><div class="s-val">' + ((astF1.functions && astF1.functions.length) || 0) + '</div><div class="s-lbl">Functions</div></div>'
      + '<div class="stat-item"><div class="s-val">' + ((astF1.imports && astF1.imports.length) || 0) + '</div><div class="s-lbl">Imports</div></div>'
      + '<div class="stat-item"><div class="s-val">' + astF1.total_statements + '</div><div class="s-lbl">Statements</div></div>'
      + '</div></div>'
      + '<div>'
      + '<div style="font-size:11px;color:var(--text-dim);font-weight:700;margin-bottom:8px;text-transform:uppercase">' + esc(f2) + '</div>'
      + '<div class="stats-grid">'
      + '<div class="stat-item"><div class="s-val">' + astF2.total_lines + '</div><div class="s-lbl">Lines</div></div>'
      + '<div class="stat-item"><div class="s-val">' + ((astF2.functions && astF2.functions.length) || 0) + '</div><div class="s-lbl">Functions</div></div>'
      + '<div class="stat-item"><div class="s-val">' + ((astF2.imports && astF2.imports.length) || 0) + '</div><div class="s-lbl">Imports</div></div>'
      + '<div class="stat-item"><div class="s-val">' + astF2.total_statements + '</div><div class="s-lbl">Statements</div></div>'
      + '</div></div>'
      + '</div>'
      + '<div style="margin-top:16px"><div class="complexity-row">'
      + '<div class="complexity-box"><div class="num" style="color:' + col1 + '">' + c1 + '</div><div class="name">' + esc(f1) + ' complexity</div></div>'
      + '<div class="complexity-box"><div class="num" style="color:' + col2 + '">' + c2 + '</div><div class="name">' + esc(f2) + ' complexity</div></div>'
      + '</div>' + lineDiffHTML + '</div>'
      + '</div>';
  }

  // Config diffs section
  let cfgDiffSection = '<p class="empty">No differences found \u2014 configurations are identical.</p>';
  if (diffs.length > 0) {
    cfgDiffSection = '<table class="config-table"><thead><tr><th>Field</th><th>' + esc(f1) + '</th><th>' + esc(f2) + '</th><th>Significance</th></tr></thead><tbody>' + cfgRows + '</tbody></table>';
  }

  // Coldstart note
  let coldNote = '<div class="empty">Cold-start times are equal</div>';
  if (metComp.coldstart_diff_ms > 0) {
    const faster = metComp.coldstart_faster === 'function1' ? f1 : f2;
    coldNote = '<div style="font-size:12px;margin-top:4px;color:var(--text-dim)">&#9193; <strong style="color:var(--ok)">' + esc(faster) + '</strong> is faster by <strong>' + metComp.coldstart_diff_ms.toFixed(0) + ' ms</strong></div>';
  }

  return '<div class="comp-card" id="comp-' + idx + '">'
    + '<div class="comp-header">'
    + '<div style="flex:1">'
    + '<div class="comp-title"><span>' + esc(f1) + '</span> &nbsp;vs&nbsp; <span>' + esc(f2) + '</span></div>'
    + '<div class="source-file">' + esc(src) + '</div>'
    + '<div class="comp-meta">' + esc(ts) + '</div>'
    + '</div>'
    + gaugeHTML(similarity)
    + '</div>'
    + '<div class="sections">'

    // Config overview
    + '<div class="section"><div class="section-title">Configuration Overview</div>'
    + '<table class="config-table"><thead><tr><th>Field</th><th>' + esc(f1) + '</th><th>' + esc(f2) + '</th><th>Status</th></tr></thead>'
    + '<tbody>' + overviewRows + '</tbody></table></div>'

    // Config diffs
    + '<div class="section"><div class="section-title">Configuration Differences</div>' + cfgDiffSection + '</div>'

    // Event sources + deps
    + '<div class="section"><div class="section-title">Event Sources &amp; Dependencies</div>'
    + '<div style="display:flex;gap:24px;flex-wrap:wrap">'
    + '<div><div style="font-size:11px;color:var(--text-dim);margin-bottom:6px;text-transform:uppercase">' + esc(f1) + '</div>'
    + '<div style="display:flex;gap:6px;flex-wrap:wrap">' + es1.map(esBadge).join('') + '</div>'
    + '<div style="margin-top:8px;font-size:12px">' + pkgs1 + '</div></div>'
    + '<div><div style="font-size:11px;color:var(--text-dim);margin-bottom:6px;text-transform:uppercase">' + esc(f2) + '</div>'
    + '<div style="display:flex;gap:6px;flex-wrap:wrap">' + es2.map(esBadge).join('') + '</div>'
    + '<div style="margin-top:8px;font-size:12px">' + pkgs2 + '</div></div>'
    + '</div>'
    + (depUnique ? '<div style="margin-top:12px">' + depUnique + '</div>' : '')
    + '</div>'

    // Metrics
    + '<div class="section"><div class="section-title">Performance Metrics</div>'
    + metricBar('Estimated Cold-Start', met1.estimated_coldstart_time||0, met2.estimated_coldstart_time||0, ' ms', maxCS)
    + metricBar('Memory Efficiency', met1.memory_efficiency||0, met2.memory_efficiency||0, '%', 100)
    + coldNote
    + '</div>'

    // Code structure
    + codeStructureHTML

    // AST diffs
    + '<div class="section"><div class="section-title">AST Diffs '
    + '<span style="font-size:10px;margin-left:6px">'
    + '<span style="color:#f87171">&#9632;</span> only in ' + esc(f1) + '&nbsp;'
    + '<span style="color:#34d399">&#9632;</span> only in ' + esc(f2) + '&nbsp;'
    + '<span style="color:#a5b4fc">&#9632;</span> shared'
    + '</span></div>'
    + diffSection('Functions', astComp.functions_diff)
    + diffSection('Imports', astComp.imports_diff)
    + diffSection('External Calls', astComp.external_calls_diff)
    + diffSection('Variables', astComp.variables_diff)
    + ((!astComp.functions_diff && !astComp.imports_diff) ? '<p class="empty">No AST data available</p>' : '')
    + '</div>'

    + '</div></div>';
}

// ── Build page ────────────────────────────────────────────────────────────────
function build() {
  const DATA = JSON.parse(document.getElementById('report-data').textContent);
  const sidebarList = document.getElementById('sidebar-list');
  const summaryBar = document.getElementById('summary-bar');
  const container = document.getElementById('cards-container');

  if (!DATA || DATA.length === 0) {
    container.innerHTML = '<div class="no-data">'
      + '<svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">'
      + '<path d="M9 17H7A5 5 0 0 1 7 7h2"/><path d="M15 7h2a5 5 0 1 1 0 10h-2"/><line x1="8" y1="12" x2="16" y2="12"/>'
      + '</svg>'
      + '<div style="font-size:16px;font-weight:600">No comparison data found</div>'
      + '<div style="margin-top:8px">Run <code>python compare_lambda_functions_ast.py &lt;f1&gt; &lt;f2&gt;</code> first</div>'
      + '</div>';
    return;
  }

  const totalComps = DATA.length;
  const criticalDiffs = DATA.reduce(function(n, c) {
    return n + ((c.configuration && c.configuration.differences && c.configuration.differences.filter(function(d){ return d.significance === 'CRITICAL'; }).length) || 0);
  }, 0);
  const avgSimilarity = DATA.reduce(function(s, c) {
    return s + ((c.ast_analysis && c.ast_analysis.comparison && c.ast_analysis.comparison.semantic_similarity_score) || 0);
  }, 0) / totalComps;
  const totalFunctions = new Set(DATA.reduce(function(a, c){ return a.concat([c.function1, c.function2]); }, [])).size;

  const avgColor = avgSimilarity >= 80 ? 'var(--ok)' : avgSimilarity >= 60 ? 'var(--imp)' : 'var(--crit)';
  const critColor = criticalDiffs > 0 ? 'var(--crit)' : 'var(--ok)';
  summaryBar.innerHTML =
    '<div class="stat-card"><div class="val">' + totalComps + '</div><div class="lbl">Comparisons</div></div>'
    + '<div class="stat-card"><div class="val">' + totalFunctions + '</div><div class="lbl">Functions Involved</div></div>'
    + '<div class="stat-card"><div class="val" style="color:' + avgColor + '">' + avgSimilarity.toFixed(0) + '%</div><div class="lbl">Avg Similarity</div></div>'
    + '<div class="stat-card"><div class="val" style="color:' + critColor + '">' + criticalDiffs + '</div><div class="lbl">Critical Differences</div></div>';

  DATA.forEach(function(c, idx) {
    const f1 = c.function1 || '?', f2 = c.function2 || '?';
    const sim = (c.ast_analysis && c.ast_analysis.comparison && c.ast_analysis.comparison.semantic_similarity_score) || 0;
    const color = similarityColor(sim);
    const li = document.createElement('li');
    li.innerHTML = '<a href="#comp-' + idx + '">'
      + '<span class="pair">' + esc(f1) + ' vs ' + esc(f2) + '</span>'
      + '<span class="meta" style="color:' + color + '">' + Math.round(sim) + '% similarity</span>'
      + '</a>';
    sidebarList.appendChild(li);
    container.insertAdjacentHTML('beforeend', renderCard(c, idx));
  });

  const cards = document.querySelectorAll('.comp-card');
  const links = document.querySelectorAll('.sidebar-list a');
  const obs = new IntersectionObserver(function(entries) {
    entries.forEach(function(e) {
      if (e.isIntersecting) {
        const id = e.target.id;
        links.forEach(function(l) { l.classList.toggle('active', l.getAttribute('href') === '#' + id); });
      }
    });
  }, { threshold: 0.3 });
  cards.forEach(function(c) { obs.observe(c); });
}

document.addEventListener('DOMContentLoaded', build);
"""

_CSS = """
  :root {
    --bg: #0f1117; --surface: #1a1d27; --surface2: #22263a; --border: #2e3350;
    --accent: #7c6af7; --accent2: #5b8dee; --text: #e2e8f0; --text-dim: #8892a4;
    --crit: #f87171; --imp: #fbbf24; --minor: #60a5fa; --ok: #34d399;
    --tag-bg-crit: rgba(248,113,113,.15); --tag-bg-imp: rgba(251,191,36,.15);
    --tag-bg-minor: rgba(96,165,250,.15); --tag-bg-ok: rgba(52,211,153,.15);
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--bg); color: var(--text); font-family: 'Segoe UI', system-ui, sans-serif; font-size: 14px; line-height: 1.6; }
  a { color: var(--accent); text-decoration: none; }
  .layout { display: flex; min-height: 100vh; }
  .sidebar { width: 280px; min-width: 280px; background: var(--surface); border-right: 1px solid var(--border); display: flex; flex-direction: column; position: sticky; top: 0; height: 100vh; overflow-y: auto; }
  .main { flex: 1; padding: 32px; overflow-x: hidden; }
  .sidebar-header { padding: 20px 16px 12px; border-bottom: 1px solid var(--border); }
  .sidebar-header h1 { font-size: 15px; font-weight: 700; color: var(--accent); letter-spacing: .5px; }
  .sidebar-header small { color: var(--text-dim); font-size: 11px; }
  .sidebar-list { list-style: none; padding: 8px 0; }
  .sidebar-list li a { display: block; padding: 10px 16px; color: var(--text-dim); border-left: 3px solid transparent; transition: all .15s; font-size: 13px; line-height: 1.4; }
  .sidebar-list li a:hover, .sidebar-list li a.active { color: var(--text); background: var(--surface2); border-left-color: var(--accent); }
  .sidebar-list li a .pair { font-weight: 600; color: var(--text); display: block; }
  .sidebar-list li a .meta { font-size: 11px; color: var(--text-dim); }
  .summary-bar { display: flex; gap: 16px; margin-bottom: 32px; flex-wrap: wrap; }
  .stat-card { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 16px 20px; flex: 1; min-width: 140px; }
  .stat-card .val { font-size: 28px; font-weight: 700; color: var(--accent); }
  .stat-card .lbl { font-size: 12px; color: var(--text-dim); margin-top: 2px; }
  .comp-card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; margin-bottom: 40px; overflow: hidden; }
  .comp-header { background: var(--surface2); padding: 18px 24px; border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }
  .comp-title { font-size: 17px; font-weight: 700; flex: 1; }
  .comp-title span { color: var(--accent2); }
  .comp-meta { font-size: 12px; color: var(--text-dim); }
  .gauge-wrap { display: flex; align-items: center; gap: 12px; }
  .gauge { position: relative; width: 60px; height: 60px; }
  .gauge svg { transform: rotate(-90deg); }
  .gauge-val { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 700; }
  .gauge-label { font-size: 11px; color: var(--text-dim); }
  .sections { display: grid; grid-template-columns: 1fr 1fr; gap: 0; }
  .section { padding: 20px 24px; border-bottom: 1px solid var(--border); }
  .section:nth-child(odd) { border-right: 1px solid var(--border); }
  .section.full { grid-column: 1 / -1; border-right: none; }
  .section-title { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: var(--text-dim); margin-bottom: 14px; display: flex; align-items: center; gap: 6px; }
  .section-title::after { content: ''; flex: 1; height: 1px; background: var(--border); }
  .config-table { width: 100%; border-collapse: collapse; font-size: 13px; }
  .config-table th { text-align: left; color: var(--text-dim); font-weight: 500; padding: 6px 8px; border-bottom: 1px solid var(--border); font-size: 11px; text-transform: uppercase; }
  .config-table td { padding: 7px 8px; border-bottom: 1px solid rgba(46,51,80,.5); vertical-align: top; }
  .config-table tr:last-child td { border-bottom: none; }
  .config-table .field-name { font-weight: 600; color: var(--text-dim); font-size: 12px; }
  .config-table .val { font-family: 'Consolas', monospace; word-break: break-all; }
  .badge { display: inline-block; padding: 2px 7px; border-radius: 4px; font-size: 10px; font-weight: 700; letter-spacing: .5px; text-transform: uppercase; white-space: nowrap; }
  .badge-CRITICAL { background: var(--tag-bg-crit); color: var(--crit); border: 1px solid rgba(248,113,113,.3); }
  .badge-IMPORTANT { background: var(--tag-bg-imp); color: var(--imp); border: 1px solid rgba(251,191,36,.3); }
  .badge-MINOR { background: var(--tag-bg-minor); color: var(--minor); border: 1px solid rgba(96,165,250,.3); }
  .badge-ok { background: var(--tag-bg-ok); color: var(--ok); border: 1px solid rgba(52,211,153,.3); }
  .badge-S3 { background: rgba(251,191,36,.12); color: var(--imp); border: 1px solid rgba(251,191,36,.3); }
  .badge-Api { background: rgba(96,165,250,.12); color: var(--minor); border: 1px solid rgba(96,165,250,.3); }
  .badge-default { background: rgba(124,106,247,.12); color: var(--accent); border: 1px solid rgba(124,106,247,.3); }
  .diff-section { margin-bottom: 12px; }
  .diff-section-name { font-size: 11px; font-weight: 700; color: var(--text-dim); text-transform: uppercase; margin-bottom: 6px; }
  .pill-row { display: flex; flex-wrap: wrap; gap: 6px; }
  .pill { display: inline-flex; align-items: center; gap: 4px; padding: 3px 9px; border-radius: 20px; font-size: 12px; font-family: 'Consolas', monospace; }
  .pill-f1 { background: rgba(248,113,113,.12); color: #f87171; border: 1px solid rgba(248,113,113,.25); }
  .pill-f2 { background: rgba(52,211,153,.12); color: #34d399; border: 1px solid rgba(52,211,153,.25); }
  .pill-common { background: rgba(124,106,247,.1); color: #a5b4fc; border: 1px solid rgba(124,106,247,.2); }
  .empty { color: var(--text-dim); font-size: 12px; font-style: italic; }
  .metric-row { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
  .metric-label { width: 180px; font-size: 12px; color: var(--text-dim); flex-shrink: 0; }
  .metric-bar-wrap { flex: 1; background: var(--bg); border-radius: 4px; height: 8px; overflow: hidden; }
  .metric-bar { height: 100%; border-radius: 4px; transition: width .4s ease; }
  .metric-val { width: 70px; text-align: right; font-size: 12px; font-family: 'Consolas', monospace; }
  .complexity-row { display: flex; gap: 16px; }
  .complexity-box { flex: 1; background: var(--surface2); border: 1px solid var(--border); border-radius: 8px; padding: 14px; text-align: center; }
  .complexity-box .num { font-size: 36px; font-weight: 800; }
  .complexity-box .name { font-size: 11px; color: var(--text-dim); margin-top: 2px; }
  .stats-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
  .stat-item { background: var(--surface2); border-radius: 6px; padding: 10px 12px; }
  .stat-item .s-val { font-size: 18px; font-weight: 700; color: var(--text); }
  .stat-item .s-lbl { font-size: 11px; color: var(--text-dim); }
  .no-data { text-align: center; padding: 60px 20px; color: var(--text-dim); }
  .no-data svg { margin-bottom: 16px; opacity: .4; }
  .source-file { font-size: 11px; color: var(--text-dim); font-family: 'Consolas', monospace; margin-top: 2px; }
  @media (max-width: 900px) {
    .sections { grid-template-columns: 1fr; }
    .section:nth-child(odd) { border-right: none; }
    .sidebar { display: none; }
    .main { padding: 20px; }
  }
"""


def generate_html(comparisons: list) -> str:
    comps_json = json.dumps(comparisons, indent=2)
    generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="UTF-8"/>\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0"/>\n'
        "<title>Lambda AST Comparison Report</title>\n"
        "<style>" + _CSS + "</style>\n"
        "</head>\n"
        "<body>\n"
        '<div class="layout">\n'
        '  <nav class="sidebar">\n'
        '    <div class="sidebar-header">\n'
        "      <h1>&#955; AST Comparisons</h1>\n"
        "      <small>Generated " + generated + "</small>\n"
        "    </div>\n"
        '    <ul class="sidebar-list" id="sidebar-list"></ul>\n'
        "  </nav>\n"
        '  <main class="main" id="main">\n'
        '    <div class="summary-bar" id="summary-bar"></div>\n'
        '    <div id="cards-container"></div>\n'
        "  </main>\n"
        "</div>\n"
        '<script type="application/json" id="report-data">\n'
        + comps_json + "\n"
        "</script>\n"
        "<script>" + _JS + "</script>\n"
        "</body>\n"
        "</html>\n"
    )


def _placeholder_for_old_impl():
    comps_json = json.dumps(comparisons, indent=2)
    generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Lambda AST Comparison Report</title>
<style>
  :root {{
    --bg: #0f1117;
    --surface: #1a1d27;
    --surface2: #22263a;
    --border: #2e3350;
    --accent: #7c6af7;
    --accent2: #5b8dee;
    --text: #e2e8f0;
    --text-dim: #8892a4;
    --crit: #f87171;
    --imp: #fbbf24;
    --minor: #60a5fa;
    --ok: #34d399;
    --tag-bg-crit: rgba(248,113,113,.15);
    --tag-bg-imp: rgba(251,191,36,.15);
    --tag-bg-minor: rgba(96,165,250,.15);
    --tag-bg-ok: rgba(52,211,153,.15);
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: var(--bg); color: var(--text); font-family: 'Segoe UI', system-ui, sans-serif; font-size: 14px; line-height: 1.6; }}
  a {{ color: var(--accent); text-decoration: none; }}

  /* ── Layout ── */
  .layout {{ display: flex; min-height: 100vh; }}
  .sidebar {{ width: 280px; min-width: 280px; background: var(--surface); border-right: 1px solid var(--border); display: flex; flex-direction: column; position: sticky; top: 0; height: 100vh; overflow-y: auto; }}
  .main {{ flex: 1; padding: 32px; overflow-x: hidden; }}

  /* ── Sidebar ── */
  .sidebar-header {{ padding: 20px 16px 12px; border-bottom: 1px solid var(--border); }}
  .sidebar-header h1 {{ font-size: 15px; font-weight: 700; color: var(--accent); letter-spacing: .5px; }}
  .sidebar-header small {{ color: var(--text-dim); font-size: 11px; }}
  .sidebar-list {{ list-style: none; padding: 8px 0; }}
  .sidebar-list li a {{
    display: block; padding: 10px 16px; color: var(--text-dim); border-left: 3px solid transparent;
    transition: all .15s; font-size: 13px; line-height: 1.4;
  }}
  .sidebar-list li a:hover, .sidebar-list li a.active {{
    color: var(--text); background: var(--surface2); border-left-color: var(--accent);
  }}
  .sidebar-list li a .pair {{ font-weight: 600; color: var(--text); display: block; }}
  .sidebar-list li a .meta {{ font-size: 11px; color: var(--text-dim); }}

  /* ── Summary bar ── */
  .summary-bar {{ display: flex; gap: 16px; margin-bottom: 32px; flex-wrap: wrap; }}
  .stat-card {{
    background: var(--surface); border: 1px solid var(--border); border-radius: 10px;
    padding: 16px 20px; flex: 1; min-width: 140px;
  }}
  .stat-card .val {{ font-size: 28px; font-weight: 700; color: var(--accent); }}
  .stat-card .lbl {{ font-size: 12px; color: var(--text-dim); margin-top: 2px; }}

  /* ── Comparison card ── */
  .comp-card {{
    background: var(--surface); border: 1px solid var(--border); border-radius: 12px;
    margin-bottom: 40px; overflow: hidden;
  }}
  .comp-header {{
    background: var(--surface2); padding: 18px 24px; border-bottom: 1px solid var(--border);
    display: flex; align-items: center; gap: 16px; flex-wrap: wrap;
  }}
  .comp-title {{ font-size: 17px; font-weight: 700; flex: 1; }}
  .comp-title span {{ color: var(--accent2); }}
  .comp-meta {{ font-size: 12px; color: var(--text-dim); }}

  /* ── Similarity gauge ── */
  .gauge-wrap {{ display: flex; align-items: center; gap: 12px; }}
  .gauge {{ position: relative; width: 60px; height: 60px; }}
  .gauge svg {{ transform: rotate(-90deg); }}
  .gauge-val {{
    position: absolute; inset: 0; display: flex; align-items: center; justify-content: center;
    font-size: 13px; font-weight: 700;
  }}
  .gauge-label {{ font-size: 11px; color: var(--text-dim); }}

  /* ── Sections ── */
  .sections {{ display: grid; grid-template-columns: 1fr 1fr; gap: 0; }}
  .section {{ padding: 20px 24px; border-bottom: 1px solid var(--border); }}
  .section:nth-child(odd) {{ border-right: 1px solid var(--border); }}
  .section.full {{ grid-column: 1 / -1; border-right: none; }}
  .section-title {{
    font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px;
    color: var(--text-dim); margin-bottom: 14px; display: flex; align-items: center; gap: 6px;
  }}
  .section-title::after {{ content: ''; flex: 1; height: 1px; background: var(--border); }}

  /* ── Config table ── */
  .config-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  .config-table th {{ text-align: left; color: var(--text-dim); font-weight: 500; padding: 6px 8px; border-bottom: 1px solid var(--border); font-size: 11px; text-transform: uppercase; }}
  .config-table td {{ padding: 7px 8px; border-bottom: 1px solid rgba(46,51,80,.5); vertical-align: top; }}
  .config-table tr:last-child td {{ border-bottom: none; }}
  .config-table .field-name {{ font-weight: 600; color: var(--text-dim); font-size: 12px; }}
  .config-table .val {{ font-family: 'Consolas', monospace; word-break: break-all; }}

  /* ── Badges ── */
  .badge {{
    display: inline-block; padding: 2px 7px; border-radius: 4px; font-size: 10px;
    font-weight: 700; letter-spacing: .5px; text-transform: uppercase; white-space: nowrap;
  }}
  .badge-CRITICAL {{ background: var(--tag-bg-crit); color: var(--crit); border: 1px solid rgba(248,113,113,.3); }}
  .badge-IMPORTANT {{ background: var(--tag-bg-imp); color: var(--imp); border: 1px solid rgba(251,191,36,.3); }}
  .badge-MINOR {{ background: var(--tag-bg-minor); color: var(--minor); border: 1px solid rgba(96,165,250,.3); }}
  .badge-ok {{ background: var(--tag-bg-ok); color: var(--ok); border: 1px solid rgba(52,211,153,.3); }}
  .badge-S3 {{ background: rgba(251,191,36,.12); color: var(--imp); border: 1px solid rgba(251,191,36,.3); }}
  .badge-Api {{ background: rgba(96,165,250,.12); color: var(--minor); border: 1px solid rgba(96,165,250,.3); }}
  .badge-default {{ background: rgba(124,106,247,.12); color: var(--accent); border: 1px solid rgba(124,106,247,.3); }}

  /* ── Diff pills ── */
  .diff-section {{ margin-bottom: 12px; }}
  .diff-section-name {{ font-size: 11px; font-weight: 700; color: var(--text-dim); text-transform: uppercase; margin-bottom: 6px; }}
  .pill-row {{ display: flex; flex-wrap: wrap; gap: 6px; }}
  .pill {{
    display: inline-flex; align-items: center; gap: 4px; padding: 3px 9px;
    border-radius: 20px; font-size: 12px; font-family: 'Consolas', monospace;
  }}
  .pill-f1 {{ background: rgba(248,113,113,.12); color: #f87171; border: 1px solid rgba(248,113,113,.25); }}
  .pill-f2 {{ background: rgba(52,211,153,.12); color: #34d399; border: 1px solid rgba(52,211,153,.25); }}
  .pill-common {{ background: rgba(124,106,247,.1); color: #a5b4fc; border: 1px solid rgba(124,106,247,.2); }}
  .empty {{ color: var(--text-dim); font-size: 12px; font-style: italic; }}

  /* ── Metrics bar ── */
  .metric-row {{ display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }}
  .metric-label {{ width: 180px; font-size: 12px; color: var(--text-dim); flex-shrink: 0; }}
  .metric-bar-wrap {{ flex: 1; background: var(--bg); border-radius: 4px; height: 8px; overflow: hidden; }}
  .metric-bar {{ height: 100%; border-radius: 4px; transition: width .4s ease; }}
  .metric-val {{ width: 70px; text-align: right; font-size: 12px; font-family: 'Consolas', monospace; }}

  /* ── Complexity compare ── */
  .complexity-row {{ display: flex; gap: 16px; }}
  .complexity-box {{
    flex: 1; background: var(--surface2); border: 1px solid var(--border); border-radius: 8px;
    padding: 14px; text-align: center;
  }}
  .complexity-box .num {{ font-size: 36px; font-weight: 800; }}
  .complexity-box .name {{ font-size: 11px; color: var(--text-dim); margin-top: 2px; }}

  /* ── Stats grid ── */
  .stats-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }}
  .stat-item {{ background: var(--surface2); border-radius: 6px; padding: 10px 12px; }}
  .stat-item .s-val {{ font-size: 18px; font-weight: 700; color: var(--text); }}
  .stat-item .s-lbl {{ font-size: 11px; color: var(--text-dim); }}

  /* ── No data ── */
  .no-data {{
    text-align: center; padding: 60px 20px; color: var(--text-dim);
  }}
  .no-data svg {{ margin-bottom: 16px; opacity: .4; }}

  /* ── Source file ── */
  .source-file {{ font-size: 11px; color: var(--text-dim); font-family: 'Consolas', monospace; margin-top: 2px; }}

  /* ── Responsive ── */
  @media (max-width: 900px) {{
    .sections {{ grid-template-columns: 1fr; }}
    .section:nth-child(odd) {{ border-right: none; }}
    .sidebar {{ display: none; }}
    .main {{ padding: 20px; }}
  }}
</style>
</head>
<body>
<div class="layout">
  <nav class="sidebar">
    <div class="sidebar-header">
      <h1>&#955; AST Comparisons</h1>
      <small>Generated {generated}</small>
    </div>
    <ul class="sidebar-list" id="sidebar-list"></ul>
  </nav>

  <main class="main" id="main">
    <div class="summary-bar" id="summary-bar"></div>
    <div id="cards-container"></div>
  </main>
</div>

<script>
const DATA = {comps_json};

// ── Helpers ─────────────────────────────────────────────────────────────────

function esc(s) {{
  return String(s ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}}

function val(v) {{
  if (v === null || v === undefined) return '<span class="empty">—</span>';
  if (typeof v === 'object') return '<code style="font-size:11px;word-break:break-all">' + esc(JSON.stringify(v)) + '</code>';
  if (typeof v === 'boolean') return v
    ? '<span class="badge badge-ok">yes</span>'
    : '<span class="badge" style="background:rgba(248,113,113,.1);color:#f87171;border:1px solid rgba(248,113,113,.2)">no</span>';
  return '<span class="val">' + esc(v) + '</span>';
}}

function badge(sig) {{
  return `<span class="badge badge-${{sig}}">${{sig}}</span>`;
}}

function similarityColor(score) {{
  if (score >= 80) return '#34d399';
  if (score >= 60) return '#fbbf24';
  return '#f87171';
}}

function gaugeHTML(score) {{
  const r = 24, cx = 30, cy = 30;
  const circ = 2 * Math.PI * r;
  const fill = (score / 100) * circ;
  const color = similarityColor(score);
  return `
    <div class="gauge-wrap">
      <div class="gauge">
        <svg width="60" height="60" viewBox="0 0 60 60">
          <circle cx="${{cx}}" cy="${{cy}}" r="${{r}}" fill="none" stroke="#2e3350" stroke-width="5"/>
          <circle cx="${{cx}}" cy="${{cy}}" r="${{r}}" fill="none" stroke="${{color}}" stroke-width="5"
            stroke-dasharray="${{fill.toFixed(1)}} ${{circ.toFixed(1)}}" stroke-linecap="round"/>
        </svg>
        <div class="gauge-val" style="color:${{color}}">${{Math.round(score)}}%</div>
      </div>
      <div>
        <div style="font-size:12px;font-weight:700;color:${{color}}">
          ${{score >= 80 ? 'Highly Similar' : score >= 60 ? 'Moderately Similar' : 'Quite Different'}}
        </div>
        <div class="gauge-label">Semantic Similarity</div>
      </div>
    </div>`;
}}

function pills(arr, cls) {{
  if (!arr || arr.length === 0) return '';
  return arr.map(x => `<span class="pill ${{cls}}">${{esc(x)}}</span>`).join('');
}}

function diffSection(title, diff) {{
  if (!diff) return '';
  const f1 = diff.only_in_first || [];
  const f2 = diff.only_in_second || [];
  const common = diff.common || [];
  if (f1.length === 0 && f2.length === 0 && common.length === 0) return '';
  return `
    <div class="diff-section">
      <div class="diff-section-name">${{title}}</div>
      <div class="pill-row">
        ${{pills(f1, 'pill-f1')}}
        ${{pills(f2, 'pill-f2')}}
        ${{pills(common, 'pill-common')}}
      </div>
      ${{(f1.length || f2.length) ? `<div style="margin-top:6px;font-size:11px;color:var(--text-dim)">
        ${{f1.length ? `<span style="color:#f87171">&#9632; only in f1</span>&nbsp;&nbsp;` : ''}}
        ${{f2.length ? `<span style="color:#34d399">&#9632; only in f2</span>&nbsp;&nbsp;` : ''}}
        ${{common.length ? `<span style="color:#a5b4fc">&#9632; shared</span>` : ''}}
      </div>` : ''}}
    </div>`;
}}

function metricBar(label, v1, v2, unit, maxV) {{
  const m = maxV || Math.max(v1, v2, 1);
  const pct1 = Math.min((v1 / m) * 100, 100).toFixed(1);
  const pct2 = Math.min((v2 / m) * 100, 100).toFixed(1);
  const color1 = '#7c6af7', color2 = '#5b8dee';
  return `
    <div style="margin-bottom:14px;">
      <div style="font-size:11px;color:var(--text-dim);margin-bottom:6px;text-transform:uppercase;letter-spacing:.5px">${{label}}</div>
      <div class="metric-row">
        <div class="metric-label" style="font-size:12px">Function 1</div>
        <div class="metric-bar-wrap"><div class="metric-bar" style="width:${{pct1}}%;background:${{color1}}"></div></div>
        <div class="metric-val">${{typeof v1 === 'number' ? v1.toFixed(1) : v1}}${{unit}}</div>
      </div>
      <div class="metric-row">
        <div class="metric-label" style="font-size:12px">Function 2</div>
        <div class="metric-bar-wrap"><div class="metric-bar" style="width:${{pct2}}%;background:${{color2}}"></div></div>
        <div class="metric-val">${{typeof v2 === 'number' ? v2.toFixed(1) : v2}}${{unit}}</div>
      </div>
    </div>`;
}}

// ── Render a single comparison card ─────────────────────────────────────────

function renderCard(c, idx) {{
  const f1 = c.function1 || '?';
  const f2 = c.function2 || '?';
  const ts = c.timestamp ? new Date(c.timestamp).toLocaleString() : '';
  const src = c._source_file || '';

  // Configuration diffs
  const diffs = c.configuration?.differences || [];
  const cfgRows = diffs.length === 0
    ? '<tr><td colspan="4"><span class="badge badge-ok">Identical</span></td></tr>'
    : diffs.map(d => `
        <tr>
          <td class="field-name">${{esc(d.field)}}</td>
          <td>${{val(d.function1_value)}}</td>
          <td>${{val(d.function2_value)}}</td>
          <td>${{badge(d.significance)}}</td>
        </tr>`).join('');

  // Config overview (identical fields)
  const cfg1 = c.configuration?.function1 || {{}};
  const cfg2 = c.configuration?.function2 || {{}};
  const overviewFields = ['runtime','memory','timeout','architecture','handler'];
  const overviewRows = overviewFields.map(f => {{
    const v1 = cfg1[f], v2 = cfg2[f];
    const same = JSON.stringify(v1) === JSON.stringify(v2);
    return `<tr>
      <td class="field-name">${{esc(f)}}</td>
      <td>${{val(v1)}}</td>
      <td>${{val(v2)}}</td>
      <td>${{same ? '<span class="badge badge-ok">Same</span>' : badge('CRITICAL')}}</td>
    </tr>`;
  }}).join('');

  // Dependencies
  const dep = c.dependencies?.comparison || {{}};
  const depF1 = c.dependencies?.function1 || {{}};
  const depF2 = c.dependencies?.function2 || {{}};

  // Metrics
  const met1 = c.metrics?.function1 || {{}};
  const met2 = c.metrics?.function2 || {{}};
  const metComp = c.metrics?.comparison || {{}};
  const maxCS = Math.max(met1.estimated_coldstart_time || 0, met2.estimated_coldstart_time || 0, 1);

  // Event sources
  const es1 = c.event_sources?.function1 || ['Direct'];
  const es2 = c.event_sources?.function2 || ['Direct'];
  function esBadge(s) {{
    const cls = s === 'S3' ? 'badge-S3' : s === 'Api' ? 'badge-Api' : 'badge-default';
    return `<span class="badge ${{cls}}">${{esc(s)}}</span>`;
  }}

  // AST analysis
  const ast = c.ast_analysis || {{}};
  const astComp = ast.comparison || {{}};
  const similarity = astComp.semantic_similarity_score ?? 0;
  const astF1 = ast.function1 || null;
  const astF2 = ast.function2 || null;

  const complexityDiff = astComp.complexity_diff || {{}};
  const linesDiff = astComp.lines_diff ?? 0;

  return `
  <div class="comp-card" id="comp-${{idx}}">
    <div class="comp-header">
      <div style="flex:1">
        <div class="comp-title"><span>${{esc(f1)}}</span> &nbsp;vs&nbsp; <span>${{esc(f2)}}</span></div>
        <div class="source-file">${{esc(src)}}</div>
        <div class="comp-meta">${{esc(ts)}}</div>
      </div>
      ${{gaugeHTML(similarity)}}
    </div>

    <div class="sections">

      <!-- Config overview -->
      <div class="section">
        <div class="section-title">Configuration Overview</div>
        <table class="config-table">
          <thead><tr><th>Field</th><th>${{esc(f1)}}</th><th>${{esc(f2)}}</th><th>Status</th></tr></thead>
          <tbody>${{overviewRows}}</tbody>
        </table>
      </div>

      <!-- Config diffs -->
      <div class="section">
        <div class="section-title">Configuration Differences</div>
        ${{diffs.length === 0
          ? '<p class="empty">No differences found — configurations are identical.</p>'
          : `<table class="config-table">
              <thead><tr><th>Field</th><th>${{esc(f1)}}</th><th>${{esc(f2)}}</th><th>Significance</th></tr></thead>
              <tbody>${{cfgRows}}</tbody>
            </table>`
        }}
      </div>

      <!-- Event Sources + Dependencies -->
      <div class="section">
        <div class="section-title">Event Sources &amp; Dependencies</div>
        <div style="display:flex;gap:24px;flex-wrap:wrap">
          <div>
            <div style="font-size:11px;color:var(--text-dim);margin-bottom:6px;text-transform:uppercase">${{esc(f1)}}</div>
            <div style="display:flex;gap:6px;flex-wrap:wrap">${{es1.map(esBadge).join('')}}</div>
            <div style="margin-top:8px;font-size:12px">${{(depF1.packages || []).map(p => `<code style="margin-right:6px;font-size:11px">${{esc(p)}}</code>`).join('')}}</div>
          </div>
          <div>
            <div style="font-size:11px;color:var(--text-dim);margin-bottom:6px;text-transform:uppercase">${{esc(f2)}}</div>
            <div style="display:flex;gap:6px;flex-wrap:wrap">${{es2.map(esBadge).join('')}}</div>
            <div style="margin-top:8px;font-size:12px">${{(depF2.packages || []).map(p => `<code style="margin-right:6px;font-size:11px">${{esc(p)}}</code>`).join('')}}</div>
          </div>
        </div>
        ${{(dep.only_in_function1?.length || dep.only_in_function2?.length) ? `
          <div style="margin-top:12px">
            ${{dep.only_in_function1?.length ? `<div style="margin-bottom:4px;font-size:12px"><span style="color:var(--text-dim)">Only in ${{esc(f1)}}:</span> ${{dep.only_in_function1.map(p=>`<span class="pill pill-f1" style="font-size:11px">${{esc(p)}}</span>`).join(' ')}}</div>` : ''}}
            ${{dep.only_in_function2?.length ? `<div style="font-size:12px"><span style="color:var(--text-dim)">Only in ${{esc(f2)}}:</span> ${{dep.only_in_function2.map(p=>`<span class="pill pill-f2" style="font-size:11px">${{esc(p)}}</span>`).join(' ')}}</div>` : ''}}
          </div>` : ''
        }}
      </div>

      <!-- Metrics -->
      <div class="section">
        <div class="section-title">Performance Metrics</div>
        ${{metricBar('Estimated Cold-Start', met1.estimated_coldstart_time||0, met2.estimated_coldstart_time||0, ' ms', maxCS)}}
        ${{metricBar('Memory Efficiency', met1.memory_efficiency||0, met2.memory_efficiency||0, '%', 100)}}
        ${{metComp.coldstart_diff_ms > 0 ? `
          <div style="font-size:12px;margin-top:4px;color:var(--text-dim)">
            &#9193; <strong style="color:var(--ok)">${{esc(metComp.coldstart_faster === 'function1' ? f1 : f2)}}</strong>
            is faster by <strong>${{metComp.coldstart_diff_ms.toFixed(0)}} ms</strong>
          </div>` : '<div class="empty">Cold-start times are equal</div>'
        }}
      </div>

      <!-- Code Structure: stats -->
      ${{astF1 && astF2 ? `
      <div class="section">
        <div class="section-title">Code Structure</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
          <div>
            <div style="font-size:11px;color:var(--text-dim);font-weight:700;margin-bottom:8px;text-transform:uppercase">${{esc(f1)}}</div>
            <div class="stats-grid">
              <div class="stat-item"><div class="s-val">${{astF1.total_lines}}</div><div class="s-lbl">Lines</div></div>
              <div class="stat-item"><div class="s-val">${{astF1.functions?.length||0}}</div><div class="s-lbl">Functions</div></div>
              <div class="stat-item"><div class="s-val">${{astF1.imports?.length||0}}</div><div class="s-lbl">Imports</div></div>
              <div class="stat-item"><div class="s-val">${{astF1.total_statements}}</div><div class="s-lbl">Statements</div></div>
            </div>
          </div>
          <div>
            <div style="font-size:11px;color:var(--text-dim);font-weight:700;margin-bottom:8px;text-transform:uppercase">${{esc(f2)}}</div>
            <div class="stats-grid">
              <div class="stat-item"><div class="s-val">${{astF2.total_lines}}</div><div class="s-lbl">Lines</div></div>
              <div class="stat-item"><div class="s-val">${{astF2.functions?.length||0}}</div><div class="s-lbl">Functions</div></div>
              <div class="stat-item"><div class="s-val">${{astF2.imports?.length||0}}</div><div class="s-lbl">Imports</div></div>
              <div class="stat-item"><div class="s-val">${{astF2.total_statements}}</div><div class="s-lbl">Statements</div></div>
            </div>
          </div>
        </div>
        <div style="margin-top:16px">
          <div class="complexity-row">
            <div class="complexity-box">
              <div class="num" style="color:${{(complexityDiff.function1||0) > (complexityDiff.function2||0) ? 'var(--crit)' : 'var(--ok)'}}">${{complexityDiff.function1||0}}</div>
              <div class="name">${{esc(f1)}} complexity</div>
            </div>
            <div class="complexity-box">
              <div class="num" style="color:${{(complexityDiff.function2||0) > (complexityDiff.function1||0) ? 'var(--crit)' : 'var(--ok)'}}">${{complexityDiff.function2||0}}</div>
              <div class="name">${{esc(f2)}} complexity</div>
            </div>
          </div>
          ${{linesDiff !== 0 ? `<div style="margin-top:10px;font-size:12px;color:var(--text-dim)">
            Code size difference: <strong style="color:${{linesDiff > 0 ? 'var(--crit)' : 'var(--ok)}}">${{linesDiff > 0 ? '+' : ''}}${{linesDiff}} lines</strong>
          </div>` : ''}}
        </div>
      </div>
      ` : `<div class="section"><div class="section-title">Code Structure</div><p class="empty">AST data unavailable</p></div>`}}

      <!-- AST Diffs -->
      <div class="section">
        <div class="section-title">AST Diffs
          <span style="font-size:10px;margin-left:6px">
            <span style="color:#f87171">&#9632;</span> only in ${{esc(f1)}}&nbsp;
            <span style="color:#34d399">&#9632;</span> only in ${{esc(f2)}}&nbsp;
            <span style="color:#a5b4fc">&#9632;</span> shared
          </span>
        </div>
        ${{diffSection('Functions', astComp.functions_diff)}}
        ${{diffSection('Imports', astComp.imports_diff)}}
        ${{diffSection('External Calls', astComp.external_calls_diff)}}
        ${{diffSection('Variables', astComp.variables_diff)}}
        ${{!astComp.functions_diff && !astComp.imports_diff ? '<p class="empty">No AST data available</p>' : ''}}
      </div>

    </div>
  </div>`;
}}

// ── Build page ───────────────────────────────────────────────────────────────

function build() {{
  const sidebarList = document.getElementById('sidebar-list');
  const summaryBar = document.getElementById('summary-bar');
  const container = document.getElementById('cards-container');

  if (!DATA || DATA.length === 0) {{
    container.innerHTML = `
      <div class="no-data">
        <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M9 17H7A5 5 0 0 1 7 7h2"/><path d="M15 7h2a5 5 0 1 1 0 10h-2"/><line x1="8" y1="12" x2="16" y2="12"/>
        </svg>
        <div style="font-size:16px;font-weight:600">No comparison data found</div>
        <div style="margin-top:8px">Run <code>python compare_lambda_functions_ast.py &lt;f1&gt; &lt;f2&gt;</code> first</div>
      </div>`;
    return;
  }}

  // Summary stats
  const totalComps = DATA.length;
  const criticalDiffs = DATA.reduce((n, c) =>
    n + (c.configuration?.differences?.filter(d => d.significance === 'CRITICAL').length || 0), 0);
  const avgSimilarity = DATA.reduce((s, c) =>
    s + (c.ast_analysis?.comparison?.semantic_similarity_score || 0), 0) / totalComps;
  const totalFunctions = new Set(DATA.flatMap(c => [c.function1, c.function2])).size;

  summaryBar.innerHTML = `
    <div class="stat-card"><div class="val">${{totalComps}}</div><div class="lbl">Comparisons</div></div>
    <div class="stat-card"><div class="val">${{totalFunctions}}</div><div class="lbl">Functions Involved</div></div>
    <div class="stat-card"><div class="val" style="color:${{avgSimilarity >= 80 ? 'var(--ok)' : avgSimilarity >= 60 ? 'var(--imp)' : 'var(--crit)}}">${{avgSimilarity.toFixed(0)}}%</div><div class="lbl">Avg Similarity</div></div>
    <div class="stat-card"><div class="val" style="color:${{criticalDiffs > 0 ? 'var(--crit)' : 'var(--ok)}}">${{criticalDiffs}}</div><div class="lbl">Critical Differences</div></div>
  `;

  // Sidebar + cards
  DATA.forEach((c, idx) => {{
    const f1 = c.function1 || '?', f2 = c.function2 || '?';
    const sim = c.ast_analysis?.comparison?.semantic_similarity_score ?? 0;
    const color = similarityColor(sim);

    const li = document.createElement('li');
    li.innerHTML = `<a href="#comp-${{idx}}">
      <span class="pair">${{esc(f1)}} vs ${{esc(f2)}}</span>
      <span class="meta" style="color:${{color}}">${{Math.round(sim)}}% similarity</span>
    </a>`;
    sidebarList.appendChild(li);

    container.insertAdjacentHTML('beforeend', renderCard(c, idx));
  }});

  // Sidebar active link on scroll
  const cards = document.querySelectorAll('.comp-card');
  const links = document.querySelectorAll('.sidebar-list a');
  const obs = new IntersectionObserver(entries => {{
    entries.forEach(e => {{
      if (e.isIntersecting) {{
        const id = e.target.id;
        links.forEach(l => l.classList.toggle('active', l.getAttribute('href') === '#' + id));
      }}
    }});
  }}, {{ threshold: 0.3 }});
  cards.forEach(c => obs.observe(c));
}}

document.addEventListener('DOMContentLoaded', build);
</script>
</body>
</html>
"""
    pass  # unused


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate HTML comparison report")
    parser.add_argument("--input-dir", default=DEFAULT_INPUT_DIR,
                        help=f"Directory containing JSON comparison files (default: {DEFAULT_INPUT_DIR})")
    parser.add_argument("--output", default=DEFAULT_OUTPUT,
                        help=f"Output HTML file (default: {DEFAULT_OUTPUT})")
    args = parser.parse_args()

    comparisons = load_all_comparisons(args.input_dir)
    if not comparisons:
        print(f"[!] No JSON files found in '{args.input_dir}'")

    html = generate_html(comparisons)
    output_path = Path(args.output)
    
    # Delete previous report if it exists
    if output_path.exists():
        output_path.unlink()
        print(f"[~] Deleted previous report: {output_path.resolve()}")
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[OK] Report generated: {output_path.resolve()}")
    print(f"     Loaded {len(comparisons)} comparison(s)")


if __name__ == "__main__":
    main()
