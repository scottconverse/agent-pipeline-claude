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

- Never silently skip a stage.
- Never advance past a `BLOCKED` or `FAILED` stage.
- Never rewrite `run.log` (append-only).
- Never modify the manifest mid-run.
- Never write outside `.agent-runs/<run_id>/` and the project working tree.
- At any halt, give the exact resume instruction: `/agent-pipeline-claude:run resume <run-id>`.
