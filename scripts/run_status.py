"""Status helper for the `/agent-pipeline-claude:run status` path.

Lists pipeline runs under ``.agent-runs/`` with last log entry + computed
status. Used by the run skill (Path 3 in skills/run/references/run.md) and
runnable standalone:

    python scripts/policy/run_status.py [--runs-dir .agent-runs] [--limit 10]

Output: one line per run, sorted by mtime descending.

    <run-id>    mode=<task|sprint>    last: <event> @ <relative-time>    status: <RUNNING | HALTED | SHIPPED>

Statuses derived from run.log content:
  - SHIPPED   : last line contains `RUN_DONE` or `PR_OPENED`
  - HALTED    : last line contains `TASK_RETRY_EXHAUSTED`, `RUN_BLOCKED`, or `HARD_HALT`
  - RUNNING   : last line contains `TASK_STARTED` (no paired TASK_PASSED), or
                 the most recent `TASK_*` is `STARTED` without a `_PASSED` after it
  - UNKNOWN   : empty log or unparseable
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path


SHIPPED_MARKERS = ("RUN_DONE", "PR_OPENED")
HALTED_MARKERS = ("TASK_RETRY_EXHAUSTED", "RUN_BLOCKED", "HARD_HALT")


def _classify_run(log_path: Path) -> tuple[str, str]:
    """Return (status, last_line) for a run.log file."""
    if not log_path.is_file():
        return "UNKNOWN", ""
    text = log_path.read_text(encoding="utf-8", errors="replace").strip()
    if not text:
        return "UNKNOWN", ""
    lines = text.splitlines()
    last = lines[-1]
    if any(marker in last for marker in SHIPPED_MARKERS):
        return "SHIPPED", last
    if any(marker in last for marker in HALTED_MARKERS):
        return "HALTED", last
    # Walk backward looking for TASK_STARTED without a TASK_PASSED after it
    return "RUNNING", last


def _detect_mode(scope_path: Path) -> str:
    """Read `**Mode**: <value>` from scope.md; return 'task' / 'sprint' / 'unknown'."""
    if not scope_path.is_file():
        return "unknown"
    text = scope_path.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"\*\*Mode\*\*:\s*(task|sprint)\b", text, flags=re.IGNORECASE)
    if m:
        return m.group(1).lower()
    return "unknown"


def _relative_time(ts: float) -> str:
    delta = time.time() - ts
    if delta < 60:
        return f"{int(delta)}s ago"
    if delta < 3600:
        return f"{int(delta // 60)}m ago"
    if delta < 86400:
        return f"{int(delta // 3600)}h ago"
    return f"{int(delta // 86400)}d ago"


def list_runs(runs_dir: Path, limit: int = 10) -> list[dict]:
    """Return a sorted list of run summaries (newest first)."""
    if not runs_dir.is_dir():
        return []
    runs = []
    for run_dir in runs_dir.iterdir():
        if not run_dir.is_dir():
            continue
        log = run_dir / "run.log"
        if not log.is_file():
            # Skip dirs without a log (not a real run).
            continue
        status, last_line = _classify_run(log)
        mode = _detect_mode(run_dir / "scope.md")
        runs.append({
            "run_id": run_dir.name,
            "mode": mode,
            "status": status,
            "last_line": last_line,
            "mtime": log.stat().st_mtime,
        })
    runs.sort(key=lambda r: r["mtime"], reverse=True)
    return runs[:limit]


def format_runs(runs: list[dict]) -> str:
    if not runs:
        return "(no runs in .agent-runs/)"
    out_lines = []
    for r in runs:
        rel = _relative_time(r["mtime"])
        # Truncate last_line to keep output compact
        last_event = r["last_line"][:80] + ("..." if len(r["last_line"]) > 80 else "")
        out_lines.append(
            f"{r['run_id']}  mode={r['mode']}  last: {last_event}  @ {rel}  status: {r['status']}"
        )
    return "\n".join(out_lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="run_status", description=__doc__)
    p.add_argument("--runs-dir", type=Path, default=Path(".agent-runs"),
                   help="Runs directory (default: .agent-runs/).")
    p.add_argument("--limit", type=int, default=10, help="Max runs to list.")
    args = p.parse_args(argv)
    runs = list_runs(args.runs_dir.resolve(), limit=args.limit)
    print(format_runs(runs))
    return 0


if __name__ == "__main__":
    sys.exit(main())
