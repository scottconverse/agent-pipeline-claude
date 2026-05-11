# codex/run-pipeline — orchestrate a pipeline run (Codex)

**How to use this file:** the Codex equivalent of the Claude Code
`/run-pipeline` slash command. Two ways to use it:

1. **One-stage-at-a-time mode (recommended).** Paste this document into a fresh
   Codex session, name the run id and pipeline type, and Codex will execute the
   NEXT incomplete stage and stop. Repeat in a fresh session per stage. This
   preserves context isolation between stages — the structural firewall that
   makes the pipeline trustworthy.
2. **Sequential single-session mode.** Same paste, but tell Codex "run every
   stage to completion in this session." Faster, but context bleeds between
   stages. Use this only for small / low-stakes runs.

The Claude Code equivalent (`commands/run-pipeline.md`) spawns subagents per
stage for true context isolation. Codex has no subagent primitive, so we
substitute "fresh session per stage" as the human-driven equivalent.

---

You are orchestrating an agentic pipeline run. The pipeline definition lives in
`.pipelines/<pipeline-type>.yaml`. The run state lives in
`.agent-runs/<run-id>/`. You execute every stage in order, write progress to
`run.log`, and stop at human-approval gates or on failure.

## Arguments

Expect two whitespace-separated tokens from the user:

- `<pipeline-type>` — must match a YAML in `.pipelines/`
- `<run-id>` — the directory name under `.agent-runs/` (typically
  `YYYY-MM-DD-<slug>`)

Plus a mode preference (default: one-stage-at-a-time):

- "one stage" — execute the next incomplete stage and stop
- "all stages" — execute every remaining stage in this session

If the user didn't provide all of these, ask in plain English.

---

## Phase A — Setup

### A1. Read the pipeline definition

Read `.pipelines/<pipeline-type>.yaml`. Parse the stages list in document
order. Each stage has these fields:

- `name` — string (e.g. `manifest`, `research`, `policy`)
- `role` — one of `human`, `pipeline`, `researcher`, `planner`, `test-writer`,
  `executor`, `verifier`, `drift-detector`, `critic`, `manager`
- `artifact` — filename written under `.agent-runs/<run-id>/`
- `gate` (optional) — `human_approval` if a human must approve after this stage
- `command` (optional) — only on `role: pipeline` stages; the shell command
- `optional_artifact` (optional, v0.5) — if `true`, missing artifact is OK
- `auto_promote_aware` (optional, v0.5) — if `true`, check for auto-promote
  preset before this stage

If the YAML is missing or unparseable, stop and report.

### A2. Read and validate the manifest

Read `.agent-runs/<run-id>/manifest.yaml`. If it doesn't exist, stop and tell
the user to paste `codex/new-run.md` into a fresh session first.

Run the strict schema validator:

```
python scripts/policy/check_manifest_schema.py --run <run-id>
```

If it exits non-zero, append `<TS> | manifest-schema | FAILED | see stdout` to
`.agent-runs/<run-id>/run.log`, display the violation output, and STOP.

### A3. Read the run log (resume state)

Read `.agent-runs/<run-id>/run.log` if it exists. Format: one event per line:

```
TIMESTAMP | STAGE_NAME | STATUS | NOTE
```

Where STATUS is `COMPLETE`, `FAILED`, or `BLOCKED`. Parse into a set of
completed stages (`COMPLETE` only).

If `run.log` doesn't exist, treat the completed set as empty.

### A4. Determine the resume point

Walk the stage list in order. The first stage whose `name` is NOT in the
completed set is where you resume.

If every stage is complete, jump to Phase C — Wrap-up.

### A5. Report the plan

Print to the user:

- Pipeline name and run id
- Total stages and their names in order
- Which stages are already complete
- Which stage is starting now
- Reminder of the chosen mode (one-stage vs. all-stages)

---

## Phase B — Stage execution

For each stage starting at the resume point, in order, execute the appropriate
handler below. After the handler completes:

1. Append one line to `.agent-runs/<run-id>/run.log` using the shell:

   ```sh
   TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
   echo "$TS | <stage_name> | COMPLETE | <note>" >> .agent-runs/<run-id>/run.log
   ```

2. If mode is "one stage", STOP. Tell the user the stage completed and what
   the next stage will be when they re-paste this file in a fresh session.
3. If mode is "all stages", continue to the next stage.

If any handler returns FAILED or BLOCKED, stop immediately regardless of mode.

### Handler 1 — `role: human` with `gate: human_approval`

This is the initial manifest-approval gate.

Steps:

1. If a prior artifact exists, tell the user: "Review
   `.agent-runs/<run-id>/<artifact_filename>` before continuing."
2. Ask the user in plain English: "Gate: `<stage_name>` — type APPROVE to
   proceed, or describe what needs to change to stop the pipeline."
3. If APPROVE: append `<TS> | <stage_name> | COMPLETE | human approved` and
   continue.
4. Otherwise: append `<TS> | <stage_name> | BLOCKED | <reason>` and STOP.

### Handler 2 — `role: pipeline` with a `command`

Runs the shell command in the `command` field. Standard stages of this type
are `policy` and (v0.5) `auto-promote`.

Steps:

1. Substitute `{run_id}` in the `command` with the actual run id.
2. Run the command from the repo root. Capture stdout + stderr combined.
3. **Artifact handling:**
   - Regular stages (no `optional_artifact`): write captured output to
     `.agent-runs/<run-id>/<artifact_filename>`.
   - `optional_artifact: true` (auto-promote): leave whatever the command
     produced. Display captured stdout to the user.
4. **Exit code handling:**
   - Regular stages: exit 0 → COMPLETE; non-zero → FAILED, STOP.
   - `auto-promote` specifically: BOTH exit 0 and exit 1 advance.
     - Exit 0 → `COMPLETE | auto-promote ELIGIBLE`
     - Exit 1 → `COMPLETE | auto-promote NOT_ELIGIBLE`
     - Exit 2 → FAILED, STOP (run dir not found).

### Handler 3 — agent role

These stages do real work. In Claude Code, each is an isolated subagent. In
Codex, you have two options:

**Option A — Fresh-session-per-stage (preferred).** Tell the user:

> "Stage `<stage_name>` is up. Start a fresh Codex session and paste this
> prompt as the first message:
>
> ---
>
> [paste the role file contents from `.pipelines/roles/<role>.md` here]
>
> ---
>
> RUN CONTEXT:
>
> [paste the manifest content and every prior-stage artifact here, each with a
> `--- <filename> ---` header]
>
> ---
>
> RUN ID: `<run-id>`
> WORKING DIR: `.agent-runs/<run-id>/`
> Write your output to `.agent-runs/<run-id>/<expected_artifact_filename>`
> and stop.
>
> ---
>
> When that session writes the artifact, come back to THIS session and tell me
> it's done; I'll verify and proceed."

This is the high-isolation path. The new session has no context except the
role file + manifest + prior artifacts — same as a Claude subagent.

**Option B — Same-session execution.** If the user picked "all stages" mode
AND explicitly waived context isolation, execute the role yourself in this
session:

1. Read `.pipelines/roles/<role>.md` in full.
2. Read the manifest and every prior-stage artifact under `.agent-runs/<run-id>/`.
3. Perform the role's work per its instructions.
4. Write the output to `.agent-runs/<run-id>/<expected_artifact_filename>`.

After the stage produces its artifact (either path):

5. Verify the artifact exists and is non-empty: `test -s
   .agent-runs/<run-id>/<artifact>` (exit 0 means non-empty).
6. If missing or empty: append `<TS> | <stage_name> | FAILED | artifact not
   produced (or empty)` and STOP.
7. If present: append `<TS> | <stage_name> | COMPLETE | <artifact> written`.

### Handler 4 — `role: manager` with `auto_promote_aware: true`

This replaces Handler 1 + Handler 3 for the manager stage when the YAML sets
`auto_promote_aware: true`.

Steps:

1. **Check for preset.** Read `.agent-runs/<run-id>/manager-decision.md`. If
   the read succeeds AND the first non-empty line is exactly
   `**Decision: PROMOTE**`, proceed to step 2. Otherwise jump to step 4.
2. **Validate-and-append mode.** Run Handler 3, but tell the agent: "An
   auto-promote preset already wrote `**Decision: PROMOTE**`. Validate the six
   citations in the existing file. Append a `## Manager confirmation` section
   listing what you validated. DO NOT REWRITE the first line. DO NOT change
   the verdict."
3. **Skip the human gate.** Append `<TS> | manager | COMPLETE |
   auto-promoted, manager confirmed`. Report to user. Continue.
4. **Fall through.** Run Handler 3 followed by Handler 1's human-approval gate
   logic. If the auto-promote stage wrote `auto-promote-report.md`, include
   its contents in the manager context so the manager sees which conditions
   failed.

### Note on Handler 3a (judge layer)

The Claude Code orchestrator has a Handler 3a that intercepts every tool call
the executor proposes and routes high-risk actions through a separate judge
subagent. Codex does not have the primitive to intercept its own tool calls
mid-stream, so Handler 3a is **not implemented in Codex**.

In Codex, the substitute discipline is:

- The executor reads `.pipelines/action-classification.yaml` itself and
  refuses to execute `high_risk` actions without asking the user first.
- The drift-detector and critic (later stages) catch any high-risk action
  that slipped through.

This is weaker than Claude's interceptor pattern. If the project's risk
posture demands real-time supervision, run the executor stage under Claude
Code rather than Codex.

### Stop conditions

The loop stops on the first of:

- A BLOCKED outcome at any human gate (Handler 1 or Handler 4 fall-through)
- A FAILED outcome at the policy stage (Handler 2)
- A FAILED outcome at any agent stage (Handler 3)
- A failed manifest schema validation at A2
- All stages have COMPLETE log entries (fall through to Phase C)
- Mode is "one stage" and one stage just completed (stop and instruct user
  to resume in a fresh session)

Never advance past a non-COMPLETE stage. Never rewrite or delete a log entry.

---

## Phase C — Wrap-up

When every stage has a COMPLETE log entry:

1. Print to the user:

   ```
   Pipeline complete. All stages passed.
   Run: .agent-runs/<run-id>/
   ```

2. List every artifact file in `.agent-runs/<run-id>/` with size (`ls -la`).
3. If `manager-decision.md` exists, read its first non-empty line and display
   it (should start with `**Decision: PROMOTE**`, `**Decision: BLOCK**`, or
   `**Decision: REPLAN**`).
4. Tell the user the next action:
   - PROMOTE: proceed to merge per the manifest's `required_gates`.
   - BLOCK: review `manager-decision.md` for the smallest fix set; address
     and re-run failing stages.
   - REPLAN: the manifest needs revision; re-issue `codex/new-run.md`.

---

## Hard rules (apply throughout)

- **Never silently skip a stage.** Either it produces a COMPLETE log line or
  the pipeline halts.
- **Never advance past a BLOCKED or FAILED stage.** Resuming requires fixing
  the underlying cause and re-pasting this file; the log determines where to
  restart.
- **Never modify the role files** in `.pipelines/roles/` — those are the
  contract.
- **Never modify the manifest** mid-run.
- **Never edit `run.log` retroactively.** Append only.
- **Never invent stages not in the YAML.**
- **Never propose autonomous mode.** Every gate is explicit.
- **At any failure or stop, give the user the exact resume instruction:**
  "Paste `codex/run-pipeline.md` into a fresh Codex session along with the run
  id `<run-id>` to resume."
- **Never merge in-flight PRs while a halt is active.** Stops mean stop —
  including "settled" cleanup PRs.
- **High-risk actions need human approval in this session.** `git push
  --force`, `git reset --hard`, `rm -rf`, `sudo`, non-editable global
  `pip install`, npm `-g` install, any "shippable" / "complete" / "done"
  language in commits — all require an explicit APPROVE from the user before
  execution.
