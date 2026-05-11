# Ideas — what should v0.5 (and beyond) look like?

This thread collects proposals for future versions. Anything from a single new policy check to a whole new layer is fair game. The bar for "this should ship" is: a specific failure mode the existing layers don't catch, plus a sketch of what catches it.

## What makes a good idea post

Three things:

1. **The failure mode.** Concretely — what went wrong, in what project, on what kind of task. Receipts beat hypotheticals.
2. **Why the existing layers don't catch it.** Manifest? Policy? Verifier? Manager? Judge (v0.4)? If your failure mode is "the verifier missed X," the proposal might be a verifier improvement, not a new layer.
3. **The sketch.** What would catch it — new role file, new policy check, new pipeline type, new manifest field, new layer entirely?

You don't need a full design. "A `data-migration` pipeline type with a dry-run rehearsal stage that operates against a copy of production data" is enough to start the conversation.

## Current candidate set (informal)

These are ideas under active consideration. None are committed. Some have been discussed in passing across projects; some are extensions that fell out of v0.4 design discussions. Order is not priority.

### Project memory layer

A persistent project-level memory the manifest can reference, separate from CLAUDE.md and ADRs. Use case: the executor and verifier repeatedly need to know which paths are "stable surface" (carefully reviewed) vs. "rough edge" (work-in-progress). Currently this lives in ad-hoc CLAUDE.md sections; a structured memory file would let the policy stage and the v0.4 judge reference it.

### Streaming verifier output

The verifier produces a single artifact at the end of the stage. For long-running verifications (running the full test suite, axe-core scan, browser walkthrough), real-time progress would help. Sketch: verifier writes line-by-line to `verifier-report.md` as it goes; orchestrator streams updates to the operator.

### Cross-run artifact diff

When the same run-id is re-invoked after a halt, the only history is `run.log` lines. Knowing what changed between attempt 1 and attempt 2 (which files, which test results, which manifest fields) would help diagnose stuck runs. Sketch: a `runs/<run-id>/attempts/N/` subdirectory per re-invocation, with a diff summary at top level.

### Per-stage timeouts and cost caps

Some agent stages can spin indefinitely (researcher rabbit-holing, executor retry-looping). A configurable per-stage timeout — wall-clock or token-spend — would halt with a clear "stage exceeded budget" log entry. Sketch: `timeout_minutes` or `max_tokens` field on the stage in the pipeline YAML; orchestrator enforces via subagent kill.

### Judge layer for sub-agents

The v0.4 judge intercepts the executor's tool calls. What about the researcher's or planner's? Probably overkill for most stages, but research stages that hit external APIs (web search, GitHub API, documentation lookup) could benefit. Sketch: extend Handler 3 with a generic action-classification step for any agent stage that opts in via a `judge: enabled` flag in its YAML stage entry.

### Auto-tuning classification rules

After N runs, the `judge-metrics.yaml` aggregate has enough data to suggest rule changes. Sketch: a `/judge-tune` slash command that reads the metrics across runs, identifies patterns (e.g. "every `gh issue create` was auto-allowed → reasonable; every `curl example.com/v1/customers` was human-blocked → promote to high_risk"), and proposes specific edits to `action-classification.yaml`.

### Multi-repo orchestration

The pipeline today operates on one repo. Multi-module projects (CivicSuite has ~30 repos with cross-module dependencies) need cross-repo coordination — a tag-bump in one repo cascades to consumer repos in a specific order. Sketch: a `meta-release` pipeline type that takes a list of repos and a dependency graph, runs the per-module pipelines in order, and aggregates artifacts.

### Better PRD-to-manifest auto-fill

`/pipeline-init` today asks for a PRD and scaffolds CLAUDE.md. The next step is the manifest — currently the operator fills it by hand. Sketch: a `/manifest-from-prd` command that reads the PRD, the recently-touched code, and proposes a draft manifest for the operator to edit. Reduces the manifest authoring time from 10 minutes to 2.

## How to propose a new idea

Reply to this thread or start a new Ideas discussion. Use the three-point shape above:

1. Failure mode (with a project / task name if possible).
2. Why existing layers don't catch it.
3. Sketch of what catches it.

Ideas that get traction either become explicit candidates here or move to GitHub Issues with a feature label. Ideas that don't get traction stay in the thread as searchable record — sometimes the third person to think of the same thing is when the idea gets built.

## What I'm explicitly NOT looking for

- "Use a different LLM." Out of scope; the plugin is Claude Code-shaped.
- "Add autonomous mode." Explicitly forbidden by the plugin's hard rules — every gate is explicit by design.
- "Make the gates optional." Same reason.
- "Replace the policy stage with hooks." Hooks intercept per-tool-call; policy intercepts per-stage. v0.4 added the per-tool-call intercept (judge); the per-stage check is still the right grain for path-scope and TODO checks.
- "Generate the manifest automatically." Some auto-fill is fine (see "Better PRD-to-manifest" above); full auto-generate defeats the gate.
