---
name: audit-init
description: Scaffold dual-AI audit-handoff infrastructure for a project — out-of-repo audit gate + protocol and in-repo 5-lens self-audit. For projects where one AI implements and a different AI audits. Invoked as /agent-pipeline-claude:audit-init.
---

# Audit-init

Follow the canonical workflow in `references/audit-init.md`. That document is the single source of truth for the input collection, the three artifacts produced, per-agent wiring, single-agent fallback, and project-level CLAUDE.md updates.

Tool mapping for Claude Code:

- Use **AskUserQuestion** to collect the structured inputs in Step 1 (project name, implementer agent, auditor agent, repo path, desktop path).
- Use **Bash** for `git -C <path> rev-parse` sanity check and for the PR push in Step 4.
- Use **Read** + **Write** for template substitution and artifact placement.

`$ARGUMENTS` is unused — the procedure is fully interactive via `AskUserQuestion`.

Hard rules:

- Never overwrite existing audit infrastructure without `AskUserQuestion` confirmation.
- Always confirm the project repo path is a real git repo before scaffolding the in-repo doc.
- The in-repo `docs/process/5-lens-self-audit.md` always lands via PR on a branch — never directly to main.
- For non-Claude AI roles, print the file paths + integration pattern; do not attempt to wire the other runtime.
