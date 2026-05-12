---
name: run-pipeline
description: "[DEPRECATED v1.0 → removed v1.1] Orchestrate a pipeline run. Use /run instead."
argument-hint: <pipeline-type> <run-id>
---

# /run-pipeline — DEPRECATED

This command is deprecated as of v1.0. Use `/run` instead.

## What to do

Print this deprecation notice verbatim to the user:

```
/run-pipeline is deprecated as of v1.0 and will be removed in v1.1.

Use /run instead — single command, drafted manifest, chat-message
human gates. No more two-step copy-paste.

  Old: /run-pipeline feature 2026-05-11-my-task-slug
  New: /run "short description"     # for new runs
       /run resume 2026-05-11-my-task-slug   # for resumption
       /run status                  # for run listing
```

Then check whether the user wants to switch or continue legacy:

- If `$ARGUMENTS` looks like `<pipeline-type> <run-id>` (two tokens, second matches `^\d{4}-\d{2}-\d{2}-`), the run already exists at `.agent-runs/<run-id>/`. Offer: *"This looks like a resumption of an existing run. Want me to delegate to `/run resume <run-id>`? Reply YES to switch, or LEGACY to use the old `/run-pipeline` orchestrator."*
- If `YES`, hand off to `/run resume <run-id>`.
- If `LEGACY`, fall through to the v0.5.2 orchestrator behavior below.

## Legacy fallback (v0.5.2 behavior, unmaintained)

Only runs when the user explicitly says `LEGACY`.

The full v0.5.2 orchestrator logic for `/run-pipeline` is preserved in the v0.5.2 tag at `git show v0.5.2:commands/run-pipeline.md`. The legacy fallback in v1.0 delegates by:

1. Setting `LEGACY_MODE=1` as a marker variable.
2. Reading `.pipelines/<pipeline-type>.yaml` for the stages list.
3. Reading `.agent-runs/<run-id>/manifest.yaml` and validating via `scripts/policy/check_manifest_schema.py`.
4. For each stage in order, spawning the appropriate agent (researcher / planner / executor / etc.) per the v0.5.2 orchestration rules.
5. Using `AskUserQuestion` for the three human gates (manifest / plan / manager) — the v0.5.2 modal pattern, NOT the v1.0 chat-message pattern.

This path exists only for v0.5.2 muscle-memory. New work should use `/run`. Bugs in the legacy fallback will not be fixed.

## Hard rules

- Always print the deprecation notice first. Never silently delegate.
- The new `/run` command is the maintained orchestrator. This file is a shim.
- Never modify the new `commands/run.md` from this file.
