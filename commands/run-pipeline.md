---
description: Orchestrate an agentic pipeline run end-to-end (resumable). Stops at human gates and on failure.
argument-hint: <pipeline-type> <run-id>
---

# /run-pipeline — orchestrate a pipeline run

You are the orchestrator of an agentic pipeline. The pipeline definition lives in `.pipelines/<pipeline-type>.yaml`. The run state lives in `.agent-runs/<run-id>/`. You execute every stage in order, write progress to `run.log`, and stop only at human-approval gates or on failure.

You do NOT do the work of any stage yourself. You delegate every agent stage to a subagent via the `Agent` tool, run policy stages via Bash, and ask the user via `AskUserQuestion` at human gates. Your job is the loop and the logging.

## Arguments

`$ARGUMENTS` contains two whitespace-separated tokens:

- **`<pipeline-type>`** — must match a YAML in `.pipelines/`.
- **`<run-id>`** — the directory name under `.agent-runs/` (typically `YYYY-MM-DD-<slug>`).

If `$ARGUMENTS` does not contain exactly two tokens, stop and report usage: `/run-pipeline <pipeline-type> <run-id>`.

---

## Phase A — Setup

### A1. Read the pipeline definition

Read `.pipelines/<pipeline-type>.yaml`. Parse the stages list in document order. Each stage has these fields:

- `name` — string, e.g. `manifest`, `research`, `policy`
- `role` — one of `human`, `pipeline`, `researcher`, `planner`, `test-writer`, `executor`, `verifier`, `manager`
- `artifact` — filename written under `.agent-runs/<run-id>/`
- `gate` (optional) — `human_approval` if a human must sign off after the stage produces its artifact
- `command` (optional) — only on `role: pipeline` stages; the shell command to execute

If the YAML is missing or unparseable, stop and report.

### A2. Read and validate the manifest

Read `.agent-runs/<run-id>/manifest.yaml`. If it does not exist, stop and tell the user to run `/new-run <pipeline-type> <slug>` first.

Inspect the manifest text. The `goal:` line must contain a non-empty quoted string. If it is `goal: ""`, stop and tell the user to fill in the manifest before starting the pipeline.

### A3. Read the run log (resume state)

Read `.agent-runs/<run-id>/run.log` if it exists. The log format is one event per line:

```
TIMESTAMP | STAGE_NAME | STATUS | NOTE
```

Where `STATUS` is one of `COMPLETE`, `FAILED`, `BLOCKED`. Parse the lines into a list of completed stages (`COMPLETE` only — `FAILED` and `BLOCKED` mean the stage is still incomplete and must re-run).

If `run.log` does not exist, treat the completed-stages list as empty.

### A4. Determine the resume point

Walk the stage list from the YAML in order. The first stage whose `name` is NOT in the completed set is where you resume.

If every stage is complete, jump to **Phase C — Wrap-up**.

### A5. Report the plan to the user

Print to the user (no tool call needed — just plain text):

- The pipeline name (`<pipeline-type>`)
- The run id
- Total stage count and their names in order
- Which stages are already complete (from the log)
- Which stage is starting now
- A note that the run will stop at any human gate or stage failure, and can be resumed by re-invoking `/run-pipeline <pipeline-type> <run-id>` with the same arguments

---

## Phase B — Stage execution loop

For each stage starting at the resume point, in order, execute the appropriate handler below. After the handler completes, write a log line and proceed to the next stage. If any handler returns FAILED or BLOCKED, stop the loop immediately — do not advance.

### Logging

For every stage outcome, append one line to `.agent-runs/<run-id>/run.log` using the Bash tool. Get the timestamp with `date -u +"%Y-%m-%dT%H:%M:%SZ"`. Format:

```
2026-05-09T04:30:00Z | <stage_name> | COMPLETE | <note>
```

Use the Bash redirect `>> ` so the log appends rather than overwrites. Quote the line carefully — the note may contain spaces.

### Handler 1 — `role: human` with `gate: human_approval`

These stages exist at the start of the pipeline (the `manifest` stage). They represent a checkpoint where the human director must approve before any agent runs.

Steps:

1. If the stage has a previously-produced artifact (look at the prior stages for the artifact filename), instruct the user to review it: `Review .agent-runs/<run-id>/<artifact_filename> before continuing.`
2. Use `AskUserQuestion` with:
   - Question: `Gate: <stage_name> — type APPROVE to proceed, or describe what needs to change to stop the pipeline.`
   - Header: `Gate`
   - Options:
     - Label: `APPROVE` — Description: `Proceed to the next stage.`
     - Label: `Block — needs changes` — Description: `Stop the pipeline; describe required changes in the next message.`
3. If the user selects `APPROVE`: append `<TS> | <stage_name> | COMPLETE | human approved` to `run.log` and continue to the next stage.
4. If the user selects `Block — needs changes` OR types any other free-form response: append `<TS> | <stage_name> | BLOCKED | <user response, single line>` to `run.log`. Report the block reason to the user. STOP the pipeline. Do not advance.

### Handler 2 — `role: pipeline` with a `command`

The standard stage of this type is `policy`. It runs `python scripts/policy/run_all.py --run <run-id>`.

Steps:

1. Substitute `{run_id}` in the `command` field with the actual run id.
2. Use the Bash tool to run the command from the repo root. Capture both stdout and stderr (`2>&1`). Save the combined output.
3. Write the captured output to `.agent-runs/<run-id>/<artifact_filename>` (use the Write tool — do not use shell redirection because the orchestrator must see the output too).
4. If the Bash exit code is `0`: append `<TS> | <stage_name> | COMPLETE | command exit 0` to `run.log` and continue.
5. If the exit code is non-zero: append `<TS> | <stage_name> | FAILED | see <artifact_filename>` to `run.log`, display the report content to the user, and STOP the pipeline.

### Handler 3 — agent role (`researcher`, `planner`, `test-writer`, `executor`, `verifier`, `manager`)

These stages do real work: an isolated subagent reads inputs, produces an artifact, and exits.

Steps:

1. Read `.pipelines/roles/<role>.md` in full. This is the role's instructions — the subagent will see it verbatim as its prompt header.
2. Build the run-context block:
   - Open with: `--- manifest.yaml ---\n` followed by the manifest content
   - For each prior stage in YAML order whose `artifact` file exists in `.agent-runs/<run-id>/`, append: `\n--- <artifact_filename> ---\n` followed by the file content
   - Skip stages whose artifact file does not exist
3. Spawn an Agent (use `subagent_type: general-purpose`) with:
   - **Description:** `<role> stage for run <run-id>`
   - **Prompt:** the role file content verbatim, followed by `\n\n---\n\nRUN CONTEXT:\n` followed by the run-context block, followed by `\n\nRUN ID: <run-id>\nWORKING DIR: .agent-runs/<run-id>/\nWrite your output to .agent-runs/<run-id>/<expected_artifact_filename> and stop.`
4. After the Agent completes, verify the expected artifact exists. The expected filename is the stage's `artifact` field. Use the Bash tool: `test -s .agent-runs/<run-id>/<artifact>` (the `-s` flag also catches empty files).
5. If the artifact file is missing or empty: append `<TS> | <stage_name> | FAILED | artifact not produced (or empty)` to `run.log`. Report the failure with the agent's last message. STOP the pipeline.
6. If the artifact exists and is non-empty: append `<TS> | <stage_name> | COMPLETE | <artifact_filename> written` to `run.log`. Briefly report the stage completed and continue to the next stage.

### Stop conditions

The loop stops on the FIRST of:

- A `BLOCKED` outcome at any human gate (handler 1)
- A `FAILED` outcome at the policy stage (handler 2)
- A `FAILED` outcome at any agent stage (handler 3)
- All stages have `COMPLETE` log entries — fall through to Phase C

Never advance past a non-`COMPLETE` stage. Never rewrite or delete an existing log entry.

---

## Phase C — Wrap-up

When every stage has a `COMPLETE` log entry:

1. Print to the user:
   ```
   Pipeline complete. All stages passed.
   Run: .agent-runs/<run-id>/
   ```
2. List every artifact file in `.agent-runs/<run-id>/` with its size (use `ls -la` via Bash).
3. If `manager-decision.md` exists, read its first non-empty line and display it. (It should start with `**Decision: PROMOTE**`, `**Decision: BLOCK**`, or `**Decision: REPLAN**`.)
4. Tell the user the pipeline run is done and what the next action is based on the manager decision:
   - `PROMOTE` — proceed to merge per the manifest's `required_gates` (the final `human_approval_merge` gate is outside this pipeline; the user merges via PR review).
   - `BLOCK` — review the manager-decision.md for the smallest fix set; address it and re-run the failing stages.
   - `REPLAN` — the manifest needs to be revised; review the manager's recommended changes.

---

## Hard rules (apply throughout)

- **Never silently skip a stage.** Either it produces a `COMPLETE` log line or the pipeline halts.
- **Never advance past a `BLOCKED` or `FAILED` stage.** Resuming requires the operator to fix the underlying cause and re-run; the runner will pick up at the right place.
- **Never modify the role files** in `.pipelines/roles/` — those are the contract. If a role is wrong, that's a separate fix the operator must make outside the pipeline.
- **Never modify the manifest** mid-run. The manifest is the contract for the entire run; if it needs to change, the manager returns `REPLAN` and the operator re-issues `/new-run`.
- **Never edit `run.log` retroactively.** Append only.
- **Never run agent stages with the same Agent slot you're using.** Always use the `Agent` tool to spawn isolated subagents — they must not see this orchestrator's conversation history.
- **Never invent stages not in the YAML.** The pipeline schema is the source of truth.
- **Never assume tool availability.** If `AskUserQuestion`, `Agent`, or any other tool is in the deferred list, load it via `ToolSearch` before invoking.
- **Never propose autonomous mode.** Every gate is explicit. If the user wants autonomous, they explicitly raise it; the runner does not suggest it.
- **At any failure or stop, give the user the exact resume command:** `/run-pipeline <pipeline-type> <run-id>` — re-invoking is safe because the log determines where to start.
- **Never merge in-flight PRs while a halt is active.** If the orchestrator is stopped on any gate or any open question, no other repo state changes happen — including cleanup PRs that "seem safe."
