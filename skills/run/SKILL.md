---
name: run
description: Start, resume, or list pipeline runs. Drafts a per-run scope contract from the project's spec, presents it for chat-message APPROVE, then orchestrates research → plan → execute → verify → critique end-to-end with three human gates. Invoked as /agent-pipeline-claude:run.
---

# Run

Follow the canonical workflow in `references/run.md`. That document is the single source of truth for argument shapes, the manifest gate, the plan gate, the manager gate, stage orchestration, resume logic, and status listing.

Tool mapping for Claude Code:

- When the procedure says **`Agent`**, use the Agent tool to spawn a subagent with the appropriate role file from `.pipelines/roles/`.
- When the procedure says **`Bash`**, use the Bash tool from the project root.
- When the procedure says **chat message gate**, render the message verbatim — never substitute `AskUserQuestion` for any of the three gates (manifest / plan / manager).

`$ARGUMENTS` is the user's text after the slash command. The procedure parses its first whitespace-separated token to decide between new run / `resume` / `status`.

Hard rules:

- **(v1.2.0+) Read the project's control plane BEFORE drafting the manifest.** Look at `.agent-workflows/PROJECT_CONTROL_PLANE.md`, `.agent-workflows/ACTIVE_WORK_QUEUE.md`, `docs/RELEASE_PLAN.md`, or `docs/PROJECT_CONTROL_PLANE.md` (first one that exists wins). The control plane names the active target. If the user's task description does not align with that target, STOP and either propose alignment OR ask the user to set `override_active_target` with a 2+ sentence reason. Do not draft an off-priority manifest. `check_active_target.py` enforces this at preflight stage 0.5; surfacing the conflict at draft time is faster + cheaper.
- **(v1.2.0+) Manifest requires `advances_target` and `authorizing_source`.** The drafter populates them from the control plane. Without a control plane, set `advances_target` from the user description and `authorizing_source` empty (preflight runs informational mode).
- Never silently skip a stage.
- Never advance past a `BLOCKED` or `FAILED` stage.
- Never rewrite `run.log` (append-only).
- Never modify the manifest mid-run. `check_manifest_immutable.py --check` will catch mutations and fail the policy stage.
- Never write outside `.agent-runs/<run_id>/` and the project working tree.
- At any halt, give the exact resume instruction: `/agent-pipeline-claude:run resume <run-id>`.
