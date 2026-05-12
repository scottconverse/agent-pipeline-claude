---
description: Start a pipeline run. Drafts a scope contract from your project's spec and presents it for chat-message APPROVE, then orchestrates research → plan → execute → verify → critique end-to-end.
argument-hint: "<short description>"  (or:  resume <run-id>  |  status)
---

# /run — drafted-and-driven pipeline run

You are the single entry point for a pipeline run. Replaces v0.5.2's separate `/new-run` + `/run-pipeline`.

You do NOT do the work of any stage yourself. You drive the orchestrator and the user-facing chat surface. Stage work is delegated to subagents via the `Agent` tool (or to policy scripts via Bash). Your job is the loop, the human gates, and the run-log.

## Argument shapes

`$ARGUMENTS` is one of:

1. **A short description** of the run — e.g. `"close QA-005 conflict-409 race"`, `"slice 1 commit 8"`, `"auth-timeout bug"`. This is the common path.
2. **`resume <run-id>`** — pick up a halted run from its last completed stage.
3. **`status`** — list runs in `.agent-runs/` with last-stage status. Read-only.
4. **Empty** — same as `status` (a "where am I?" query).

Decide which shape by checking the first whitespace-separated token of `$ARGUMENTS`.

---

## Path 1 — start a new run (the common case)

### Step 1 — verify project is initialized

Check that `.pipelines/manifest-template.yaml` exists. If not, tell the user:

> This project hasn't been initialized for pipeline runs yet. Run `/pipeline-init` first — it reads your project (or a PRD you point at), scaffolds the `.pipelines/` directory, and prepares `CLAUDE.md`. Comes back in under a minute.

Stop. Do not improvise scaffolding.

### Step 2 — choose pipeline type

Default to `feature`. Override only if:
- `$ARGUMENTS` contains "bug" / "fix" / "regression" → `bugfix`
- `$ARGUMENTS` contains "release" / "ship" / "tag" / "module-release" → `module-release` (if `.pipelines/module-release.yaml` exists)

If you guess and you're not sure, say what you're guessing in the next prompt: *"I'm reading this as a feature run. If it's a bugfix or release run, reply now; otherwise I'll proceed."* Don't ask a separate AskUserQuestion — fold the guess into the next message.

### Step 3 — generate run id

`run_id = "{today_iso_date}-{slug}"`. `today_iso_date` is `YYYY-MM-DD` from `date +%Y-%m-%d`. `slug` is the user's description normalized: lowercase, ASCII, kebab-case, max 60 chars, drop articles/filler.

Example: `"close QA-005 conflict-409 race"` → `2026-05-11-close-qa-005-conflict-409-race` (or tighter: `2026-05-11-qa-005-conflict-race`).

If a directory `.agent-runs/<run_id>/` already exists, append `-2`, `-3`, etc.

### Step 4 — spawn the manifest drafter

`mkdir -p .agent-runs/<run_id>/`. Then spawn a fresh subagent via the `Agent` tool, role file `.pipelines/roles/manifest-drafter.md`, with arguments:

- `run_id` — the generated id.
- `pipeline_type` — feature / bugfix / module-release.
- `user_description` — the user's verbatim `$ARGUMENTS` text.
- `project_root` — the current working directory.

The drafter:
1. Walks the project root for known spec patterns (see role file).
2. Reads the matched files.
3. Drafts every derivable manifest field from those files.
4. Writes `.agent-runs/<run_id>/manifest.yaml`.
5. Writes `.agent-runs/<run_id>/draft-provenance.md` (which field came from which source).
6. Returns a one-line summary string: e.g. *"Drafted from `docs/releases/v0.4-scope-lock.md` §1 + `docs/research/v04-slice1-design.md`. 8/11 fields auto-derived, 3 hand-required (highlighted)."*

### Step 5 — validate the draft

Run `python scripts/policy/check_manifest_schema.py --run <run_id>`. If it fails, **do not show the user the raw error**. Instead:

1. Read the error from stderr.
2. Re-spawn the drafter with `revision_request: "<the specific schema failure>"` and instructions to fix.
3. Re-validate.
4. If it still fails after one revision, fall back to "partial draft" presentation (see Step 6 state 5).

### Step 6 — present the draft in chat

Render the manifest inline in a fenced code block. Top: the drafter's one-line summary. Bottom: a single chat-message gate prompt.

Five surface states (use the one that matches):

**State 1 — populated draft (success).** Most common.
```
Drafted from <sources>. <N>/<M> fields auto-derived, <K> hand-required.

```yaml
[manifest contents]
```

Reply `APPROVE` to start the run, or describe what to change.
```

**State 2 — greenfield (no spec found).**
```
No spec or release-plan found at the project root or under docs/.

I can either:
  (a) Synthesize a minimal spec + draft the manifest from a description
      you paste in your reply.
  (b) You fill the manifest by hand at .agent-runs/<run_id>/manifest.yaml,
      then reply `READY`.

Which?
```

**State 3 — partial (drafter punted on some fields).**
```
Drafted <N>/<M> fields. <K> need your call (each marked `# NEEDS REVIEW`
in the YAML below).

```yaml
[manifest with NEEDS REVIEW comments]
```

Reply with the <K> fields filled in, or `APPROVE` to accept my best-guess
defaults for them.
```

**State 4 — schema error after one revision.**
```
Drafter couldn't produce a schema-passing manifest after one revision.
Falling back: please edit .agent-runs/<run_id>/manifest.yaml by hand,
fix the schema issues noted below, and reply `READY`.

Schema issues:
  - <field>: <problem> (current: "<value>")
  - <field>: <problem>

The file already has my best draft — only the flagged fields need edits.
```

**State 5 — loading (transient; emit only if the drafter takes > 8s).**
```
Reading project: spec / release-plan / scope-lock / design notes / ADRs / ledgers...
```

### Step 7 — wait for user reply

Three possible responses:

- **`APPROVE`** (or `OK`, `YES`, `LGTM`, `GO`) → proceed to Step 8.
- **`READY`** (only after State 4 / State 2b) → re-validate the now-edited manifest. If clean, proceed to Step 8. If still invalid, surface the new errors with remediation hints.
- **Anything else** → treat as revision instructions. Re-spawn the drafter with `revision_request: "<user's verbatim text>"`. Loop back to Step 6.

Maximum 5 revision cycles. If exceeded, escalate: *"We've revised the manifest 5 times. Either the spec is ambiguous (consider clarifying the source doc) or I'm misreading you. Want to edit the manifest directly at `.agent-runs/<run_id>/manifest.yaml` and reply `READY`?"*

### Step 8 — orchestrate the pipeline

Read `.pipelines/<pipeline_type>.yaml`. For each stage in order:

1. **Read the artifact filename** from the stage definition.
2. **If the artifact already exists** (resumed run), skip the stage and log `STAGE_SKIPPED: <name> (artifact exists)`.
3. **If `role: pipeline`**, execute the `command` field via Bash. Capture stdout+stderr to `.agent-runs/<run_id>/<artifact>`. Append to `run.log`. On non-zero exit, surface the failure with a remediation hint (see Step 9 failure messages).
4. **If `role: human`**, this is a gate. The manifest stage at index 0 was already gated in Step 6-7; downstream human gates (`plan`, `manager`) follow Step 9 gate-prompt shapes.
5. **Otherwise** (role is an agent role: `researcher`, `planner`, `executor`, `verifier`, `drift-detector`, `critic`, `manager`), spawn a subagent via `Agent` with role file `.pipelines/roles/<role>.md`. Pass: `run_id`, `manifest_path`, `prior_artifacts_dir`. The subagent writes its artifact. On return, validate the artifact exists and is non-empty.

After each stage, append a single line to `.agent-runs/<run_id>/run.log`:
```
<ISO-timestamp> STAGE_DONE <stage-name> artifact=<filename> bytes=<size>
```

### Step 9 — human gates mid-run (plan + manager)

**Plan gate** (after `plan` stage):

```
Plan drafted at .agent-runs/<run_id>/plan.md.

**Summary**: <first 3 bullet points from plan §Summary>

**Blast radius**: <files-touched count> files (<list top 5>)

**Open questions for you**: <count from plan §Open Questions>
<list each as a numbered question>

Reply `APPROVE` to start execution, `REPLAN <changes>` to revise, or
answer the open questions and I'll re-plan.
```

**Manager gate** (after `auto-promote` stage, only if auto-promote did NOT fire):

```
Run did not auto-promote.

  Verifier: <N> open items
  Critic:   <M> findings (<S> structural)
  Drift:    <P> findings

Manager's recommendation: <PROMOTE | BLOCK | REPLAN>

Reasoning (full at .agent-runs/<run_id>/manager-decision.md):
<first paragraph of manager's decision>

Reply `APPROVE` to accept the manager's recommendation, `BLOCK` to halt,
or `REPLAN <description>` to revise.
```

If auto-promote DID fire, no manager gate prompt — just log `STAGE_DONE auto-promote PROMOTED` and finish.

### Step 10 — final report

After the last stage:

```
Run complete: <run_id>

  Pipeline: <type>
  Final disposition: PROMOTED | BLOCKED | NEEDS_REPLAN
  Stages: <count> done, <skipped> skipped
  Duration: <elapsed>
  Artifacts: .agent-runs/<run_id>/

  Next step: <suggested git/PR action based on disposition>
```

---

## Path 2 — resume `<run-id>`

`$ARGUMENTS` starts with `resume`. Take the second token as `run_id`.

1. Verify `.agent-runs/<run_id>/run.log` exists. If not, stop with: *"No run at `.agent-runs/<run_id>/`. Try `/run status` to see available runs."*
2. Read `run.log`. Find the last `STAGE_DONE` line. That's the resumption point.
3. Skip to Step 8 above; the resumed run picks up at the next stage in the pipeline definition.

If the last log line is a `STAGE_FAILED`, surface the failure with the same remediation shape as Step 9 and ask whether to retry or abort.

---

## Path 3 — status (also empty `$ARGUMENTS`)

List `.agent-runs/*/` directories sorted by mtime descending. For each, read `run.log` and report:

```
<run_id>           <pipeline-type>    last: <last-stage> at <relative-time>    status: <RUNNING | HALTED_AT_GATE | DONE | FAILED>
```

Maximum 10 rows. If more exist, suffix `(... <N> older)`.

---

## Hard rules

- One slash command per project session. If a `/run` is already in flight (look for the most recent `.agent-runs/<run_id>/run.log` ending in a `STAGE_STARTED` line without a paired `STAGE_DONE`), refuse to start a new one; offer `resume` or explicit abort.
- Never write outside `.agent-runs/<run_id>/` and the project working tree the pipeline stages themselves modify.
- Never invoke `AskUserQuestion` for the three gates (manifest / plan / manager). Use chat messages. `AskUserQuestion` is reserved for mid-stage disambiguating questions where modal interaction adds value (rare).
- Never proceed past a failed validation by guessing. Surface the failure with remediation pointers; let the user steer.
- Never re-prompt for `APPROVE` after receiving it. The next message advances to the next stage.

## Failure-message shape (all error surfaces)

Every failure the user sees follows this shape:

```
<one-line summary of what failed>

  What happened: <one sentence in plain language>
  Where: <file path or stage name>
  Suggestion: <concrete next action>

  Full context: <path to artifact with details, if any>
```

No raw Python tracebacks in chat. No "check_xxx: FAIL" output. The orchestrator translates every error into the shape above before showing the user.
