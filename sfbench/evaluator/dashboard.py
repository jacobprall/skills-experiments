"""HTML dashboard generator — single-page report from trial results."""

from __future__ import annotations

import json
from pathlib import Path

from rich.console import Console

from sfbench.models.trial import TrialResult

console = Console()

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS_DIR = PROJECT_ROOT / "results"


def generate_dashboard(output_path: Path | None = None) -> Path:
    """Generate an HTML dashboard from all results in the results directory."""
    results = _load_all_results()
    if not results:
        console.print("[yellow]No results found in results/[/yellow]")
        return Path()

    output = output_path or RESULTS_DIR / "dashboard.html"
    html = _build_html(results)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html)
    console.print(f"Dashboard written to {output}")
    return output


def _load_all_results() -> list[dict]:
    """Load all trial_result.json files from results directory."""
    results = []
    if not RESULTS_DIR.exists():
        return results

    for result_file in sorted(RESULTS_DIR.rglob("trial_result.json")):
        try:
            data = json.loads(result_file.read_text())
            data["_result_path"] = str(result_file.parent)
            results.append(data)
        except Exception:
            continue

    return results


def _build_html(results: list[dict]) -> str:
    """Build a single-page HTML dashboard."""

    # Group by agent + plugin_set
    groups: dict[str, list[dict]] = {}
    for r in results:
        key = f"{r.get('agent', '?')} / {r.get('plugin_set', '?')}"
        groups.setdefault(key, []).append(r)

    # Collect all unique task_ids
    all_tasks = sorted(set(r.get("task_id", "?") for r in results))

    # Build summary matrix rows
    matrix_rows = ""
    for task_id in all_tasks:
        cells = f"<td class='task-id'>{task_id}</td>"
        for group_name in sorted(groups.keys()):
            group_results = [r for r in groups[group_name] if r.get("task_id") == task_id]
            if group_results:
                r = group_results[-1]  # latest attempt
                passed = r.get("passed", False)
                pct = r.get("composite_pct", 0)
                cls = "pass" if passed else "fail"
                cells += f"<td class='{cls}'>{pct:.0f}%</td>"
            else:
                cells += "<td class='na'>—</td>"
        matrix_rows += f"<tr>{cells}</tr>\n"

    # Build per-trial detail sections
    detail_sections = ""
    for r in results:
        task_id = r.get("task_id", "?")
        agent = r.get("agent", "?")
        passed = r.get("passed", False)
        pct = r.get("composite_pct", 0)
        dur = r.get("duration_seconds", 0)
        run_id = r.get("run_id", "")

        req_rows = ""
        for req in r.get("requirement_results", []):
            status = "PASS" if req.get("passed") else "FAIL"
            cls = "pass" if req.get("passed") else "fail"
            req_rows += f"<tr><td>{req.get('id','')}</td><td class='{cls}'>{status}</td></tr>"

        assert_rows = ""
        for a in r.get("assertion_results", []):
            pts = f"{a.get('points_earned',0)}/{a.get('points_available',0)}"
            assert_rows += (
                f"<tr><td>{a.get('id','')}</td><td>{a.get('category','')}</td>"
                f"<td>{a.get('type','')}</td><td>{pts}</td></tr>"
            )

        trap_rows = ""
        for t in r.get("trap_results", []):
            detected = "Yes" if t.get("detected") else "No"
            pts = f"{t.get('points_earned',0)}/{t.get('points_available',0)}"
            trap_rows += f"<tr><td>{t.get('id','')}</td><td>{detected}</td><td>{pts}</td></tr>"

        status_cls = "pass" if passed else "fail"
        detail_sections += f"""
        <div class="trial-card" id="trial-{run_id}">
            <h3>{task_id} — <span class="{status_cls}">{pct:.0f}%</span></h3>
            <p>Agent: {agent} | Duration: {dur:.1f}s | Run: {run_id}</p>
            {"<h4>Requirements</h4><table class='detail'><tr><th>ID</th><th>Status</th></tr>" + req_rows + "</table>" if req_rows else ""}
            {"<h4>Assertions</h4><table class='detail'><tr><th>ID</th><th>Category</th><th>Type</th><th>Points</th></tr>" + assert_rows + "</table>" if assert_rows else ""}
            {"<h4>Traps</h4><table class='detail'><tr><th>ID</th><th>Detected</th><th>Points</th></tr>" + trap_rows + "</table>" if trap_rows else ""}
        </div>
        """

    group_headers = "".join(f"<th>{g}</th>" for g in sorted(groups.keys()))

    total = len(results)
    passed_count = sum(1 for r in results if r.get("passed"))
    avg_score = sum(r.get("composite_pct", 0) for r in results) / max(total, 1)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SFBench Dashboard</title>
<style>
  :root {{ --pass: #22c55e; --fail: #ef4444; --bg: #0f172a; --card: #1e293b;
           --text: #e2e8f0; --border: #334155; --accent: #3b82f6; }}
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family: system-ui, -apple-system, sans-serif; background:var(--bg);
          color:var(--text); padding:2rem; }}
  h1 {{ font-size:1.8rem; margin-bottom:.5rem; }}
  h2 {{ font-size:1.3rem; margin:1.5rem 0 .75rem; border-bottom:1px solid var(--border);
        padding-bottom:.5rem; }}
  h3 {{ font-size:1.1rem; margin-bottom:.5rem; }}
  h4 {{ font-size:.9rem; margin:.75rem 0 .25rem; color:#94a3b8; }}
  .summary {{ display:flex; gap:2rem; margin:1rem 0 2rem; }}
  .stat {{ background:var(--card); padding:1rem 1.5rem; border-radius:.5rem;
           border:1px solid var(--border); }}
  .stat .label {{ font-size:.75rem; color:#94a3b8; text-transform:uppercase; }}
  .stat .value {{ font-size:1.5rem; font-weight:700; margin-top:.25rem; }}
  table {{ width:100%; border-collapse:collapse; margin:.5rem 0; }}
  th, td {{ padding:.5rem .75rem; text-align:left; border:1px solid var(--border); }}
  th {{ background:#1e293b; font-size:.8rem; text-transform:uppercase; color:#94a3b8; }}
  td {{ font-size:.85rem; }}
  .task-id {{ font-weight:600; }}
  .pass {{ color:var(--pass); font-weight:600; }}
  .fail {{ color:var(--fail); font-weight:600; }}
  .na {{ color:#475569; }}
  .trial-card {{ background:var(--card); border:1px solid var(--border); border-radius:.5rem;
                 padding:1rem 1.25rem; margin:.75rem 0; }}
  .detail {{ font-size:.8rem; }}
  .detail th {{ font-size:.7rem; }}
</style>
</head>
<body>
<h1>SFBench Dashboard</h1>
<p style="color:#94a3b8">Snowflake Operations Benchmark Results</p>

<div class="summary">
  <div class="stat"><div class="label">Total Trials</div><div class="value">{total}</div></div>
  <div class="stat"><div class="label">Passed</div><div class="value pass">{passed_count}</div></div>
  <div class="stat"><div class="label">Failed</div><div class="value fail">{total - passed_count}</div></div>
  <div class="stat"><div class="label">Avg Score</div><div class="value">{avg_score:.0f}%</div></div>
</div>

<h2>Results Matrix</h2>
<table>
  <tr><th>Task</th>{group_headers}</tr>
  {matrix_rows}
</table>

<h2>Trial Details</h2>
{detail_sections}

</body>
</html>"""
