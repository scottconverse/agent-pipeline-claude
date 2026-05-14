---
name: run-autonomous
description: (Deprecated in v1.3.0 — use /agent-pipeline-claude:run instead.) The v1.2.x grant-based autonomous mode is gone. The standard /run now uses fast modal AskUserQuestion gates (one click each) and auto-promotes evidence-driven when all checks pass.
---

# Deprecated in v1.3.0

This skill is a no-op. The grant + autonomous-mode mechanism it implemented (v1.2.1) created more friction than it removed: gates required signed grant files, the LLM still found ways to halt on edge cases, and the ceremony around chat-APPROVE was the actual failure mode — not the lack of authorization.

The v1.3.0 redesign:

- **All three human gates** (manifest, plan, manager) fire as `AskUserQuestion` modals — ONE click each.
- **Auto-promote is the path to hands-off.** When `auto_promote.py` reports ELIGIBLE (verifier clean, critic clean, drift clean, policy passed, tests passed), the manager gate is skipped entirely. No grant required.
- **There is no separate autonomous mode.** Just `/agent-pipeline-claude:run`.

## What to do instead

Run `/agent-pipeline-claude:run "<task description>"`. The flow:

1. Manifest drafter produces `manifest.yaml`. Modal gate: APPROVE / Revise / View.
2. Pipeline stages run in order (research → plan → execute → policy → verify → drift → critic).
3. Plan stage produces `plan.md`. Modal gate: APPROVE / REPLAN / View / Block.
4. After critique, `auto_promote.py` runs.
5. **If ELIGIBLE**: `manager-decision.md` is auto-written with verdict PROMOTE; manager subagent validates-and-appends a confirmation; no human gate fires.
6. **If NOT_ELIGIBLE**: manager subagent decides; modal gate: APPROVE manager verdict / BLOCK / REPLAN / View.

If you have existing autonomous-grant files on disk under `.agent-workflows/autonomous-grants/`, they are ignored. Safe to archive.

If you typed `/agent-pipeline-claude:run-autonomous` expecting the old behavior, please use `/agent-pipeline-claude:run` instead.
