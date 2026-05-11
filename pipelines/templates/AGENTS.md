# AGENTS.md — Codex project context

This file is read automatically by Codex when working in this repo. It tells Codex
how to find and use the agentic pipeline scaffolded under `.pipelines/` and the
policy checks under `scripts/policy/`.

If you are Claude Code in this repo, read `CLAUDE.md` instead. The two files
coexist; they describe the same pipeline from each runtime's perspective.

---

## What this project uses

This project uses the **agentic-pipeline** discipline
(https://github.com/scottconverse/agentic-pipeline). The pipeline is a
manifest-driven, stage-by-stage workflow for non-trivial changes:

```
manifest → research → plan → test-writer → execute → policy →
verify → drift-detect → critique → auto-promote → manager
```

Every stage produces a durable artifact under `.agent-runs/<run-id>/`. Every
stage has a role brief under `.pipelines/roles/<role>.md`. The role brief is
the contract — read it before doing that stage's work.

## Codex runtime conventions

Codex does not spawn subagents, so the pipeline runs **sequentially in fresh
sessions**, not in parallel with context isolation. To preserve the firewall
between stages:

1. **One stage per session.** Start a fresh Codex session for each stage.
2. **Read only that stage's inputs.** The orchestration prompts in
   `codex/run-pipeline.md` tell you exactly which files to read for each stage.
   Do NOT read prior conversation history; do NOT load the entire `.agent-runs/`
   directory wholesale.
3. **Write only that stage's artifact.** Each stage's output is one file under
   `.agent-runs/<run-id>/`. Do not modify any other artifact.
4. **Append to `run.log` after the stage's artifact is written.** One line per
   stage outcome, format `TIMESTAMP | STAGE | STATUS | NOTE`.

## How to start

Three entry points, in order:

1. **First time on this project:** read `codex/pipeline-init.md` and follow it.
   (Already done if `.pipelines/` exists at the repo root.)
2. **Starting a new task:** read `codex/new-run.md` and follow it. This creates
   `.agent-runs/YYYY-MM-DD-<slug>/manifest.yaml` and asks the human to fill it
   in.
3. **Running the pipeline:** read `codex/run-pipeline.md` and follow it. This
   walks every stage, stage-by-stage, in fresh sessions.

## Hard rules (apply throughout)

- Never modify a role file in `.pipelines/roles/`. Those are the contract.
- Never modify the manifest mid-run. If it needs to change, the manager returns
  REPLAN and the human re-issues `new-run`.
- Never edit `run.log` retroactively. Append only.
- Never bypass the policy stage. If `python scripts/policy/run_all.py --run
  <run-id>` exits non-zero, the run halts. Fix the violations, do not paper
  them over.
- Never skip the human gates. Manifest approval and final manager decision
  require a human typing APPROVE.
- Never invoke `git push --force`, `git reset --hard`, `rm -rf`, `sudo`, or
  any other high-risk action without explicit human approval in this session.

## Single-AI hardening (v0.5+)

When this AI is the only AI running the pipeline (no separate auditor), four
structural substitutes for cross-AI verification are in effect:

1. **Strict manifest schema** — `scripts/policy/check_manifest_schema.py` blocks
   fuzzy manifests at the start of the run.
2. **Pre-edit fact-forcing gate** — before the executor's first edit to any
   file, it must write a fact block (importers, schema, manifest goal verbatim)
   into `.agent-runs/<run-id>/notes/pre-edit-<filename>.md`.
3. **Adversarial critic** — after verify, a cold-read critic re-reads the diff
   without the implementer's reasoning and emits a findings count.
4. **Drift detector** — compares the manifest contract to the final assembled
   state and emits a drift count.
5. **Machine-checkable auto-promote** — `scripts/policy/auto_promote.py` reads
   the parseable count lines from verifier/critic/drift/policy/judge artifacts
   and writes a PROMOTE preset only if all six conditions pass.

These four (plus the policy stage) substitute for a second AI. Do not skip them.

## Where the run state lives

- `.agent-runs/<run-id>/manifest.yaml` — the contract for this run.
- `.agent-runs/<run-id>/run.log` — append-only event log; the orchestration
  prompts use this to determine resume point.
- `.agent-runs/<run-id>/*.md` — one artifact per completed stage.
- `.pipelines/<pipeline-type>.yaml` — the stage list for this run's pipeline.
- `.pipelines/roles/<role>.md` — the role brief read at the start of each stage.

## CLAUDE.md (if present)

If `CLAUDE.md` exists at the repo root, read it too. It contains
project-specific conventions (stack, tests, lint, ADR posture, non-negotiables)
that Claude reads as global context. The same conventions apply to Codex.
