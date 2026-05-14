# User manual — agent-pipeline-claude v2.0

Step-by-step. Read this if you've installed the plugin and want to ship your first sprint.

---

## 1. Install + activate

In Cowork or Claude Code, install the `agent-pipeline-claude` plugin from the marketplace.

Confirm it loaded:

```
/agent-pipeline-claude:run status
```

This should print `(no runs in .agent-runs/)` if you haven't started any yet. If the command isn't recognized, check that the plugin is enabled.

---

## 2. Initialize a project

In your repository:

```
/agent-pipeline-claude:pipeline-init
```

The skill inspects your project (CLAUDE.md, README, recent commits) and shows an orientation summary. Reply `APPROVE` to scaffold:

```
.pipelines/sprint.yaml
.pipelines/sprint-task.yaml
.pipelines/roles/worker.md
scripts/policy/run_status.py
scripts/policy/validate_scope.py
```

If you don't have a `CLAUDE.md` at root, you'll be asked whether to write a starter (`YES` or `SKIP`).

Add `.agent-runs/` to your `.gitignore` if it isn't already there — run artifacts shouldn't be committed.

---

## 3. Start your first run

Three goal types. Pick what fits.

### 3a. Single-task run

```
/agent-pipeline-claude:run "fix the auth-timeout bug — bump JWT cookie expiry from 24h to 14d"
```

The skill drafts a one-task scope contract and shows it:

```
Goal: Fix the auth-timeout bug — bump JWT cookie expiry from 24h to 14d
Mode: task
Branch: fix/auth-timeout-14d (NEW)
Tasks (1):
  1. Patch JWT cookie expiry constant in backend/auth/jwt.py
Allowed paths: backend/auth/
Complexity: low
```

Then it fires ONE `AskUserQuestion` modal: `GO / REVISE / BLOCK`.

Click **GO**. The autonomous loop starts. The worker subagent:

1. Reads the relevant code.
2. Plans the change internally (no `plan.md` artifact).
3. Edits `backend/auth/jwt.py`.
4. Runs your test suite (`pytest` or whatever CLAUDE.md names).
5. Reports `**Status: passes**` (or `fails`).

If it passes, the orchestrator commits with `fix(auth): bump JWT cookie expiry to 14d`, runs the full integration suite, pushes the branch, opens a PR. Done. One click total.

If it fails, the orchestrator spawns the worker again with the test failure output prepended (Reflexion). Up to 3 attempts. After that, the task is blocked and escalates.

### 3b. Explicit sprint (you've already written a sprint plan)

If you have `docs/sprints/0.4-slice1.md` listing the commits/tasks:

```
/agent-pipeline-claude:run "ship slice 1 of v0.4 per docs/sprints/0.4-slice1.md"
```

The skill reads your sprint plan, lifts its task list verbatim into scope.md, shows the orientation, and fires the scope gate. After GO, it loops through each task in order, committing per task. At the end: integration suite, push, PR open.

### 3c. Open-ended sprint

```
/agent-pipeline-claude:run "get the cleanroom passing for civicrecords-ai on Linux WSL"
```

The skill decomposes this into 3-7 tasks at draft time (read spec/CLAUDE.md, propose ordered task list), shows the proposed decomposition, fires the scope gate. After GO: same loop.

---

## 4. What you'll see during the run

After clicking GO:

```
2026-05-14T17:32:00Z RUN_STARTED
2026-05-14T17:32:00Z SCOPE_APPROVED
2026-05-14T17:32:15Z TASK_STARTED: task-1
2026-05-14T17:33:42Z TASK_PASSED: task-1 (commit a3b4c5d)
2026-05-14T17:33:42Z TASK_STARTED: task-2
2026-05-14T17:35:18Z TASK_PASSED: task-2 (commit b8c9d0e)
2026-05-14T17:35:18Z TASK_STARTED: task-3
2026-05-14T17:36:50Z TASK_FAILED: task-3 (attempt 1; retrying with observation)
2026-05-14T17:38:11Z TASK_PASSED: task-3 (commit c1d2e3f)
2026-05-14T17:38:11Z INTEGRATION_STARTED
2026-05-14T17:39:45Z INTEGRATION_PASSED
2026-05-14T17:39:46Z PR_OPENED: https://github.com/.../pull/123
2026-05-14T17:39:46Z RUN_DONE
```

No modal dialogs after the initial GO. The chat surface stays quiet except for the final report. You can minimize Cowork and come back to a green PR.

---

## 5. Final report

After `RUN_DONE`, the chat shows:

```
Run complete: 2026-05-14-fix-auth-timeout

  Mode:               task
  Tasks:              1/1 passed
  Branch:             fix/auth-timeout-14d → https://github.com/.../pull/123
  Disposition:        SHIPPED
  Integration suite:  PASSED

  Next action:        Review and merge the PR.
```

You merge the PR through your normal review flow. The plugin never admin-merges.

---

## 6. What happens when a task fails

Worker reports `**Status: fails**`. Orchestrator spawns worker again:

```
ATTEMPT: 2 of 3

PRIOR_FAILURE_OBSERVATION:
=================
FAILED tests/test_auth.py::test_jwt_cookie_expiry
    AssertionError: expected 14 days (1209600s), got 24 hours (86400s)
    File: backend/auth/jwt.py line 47
=================
```

The new worker reads this BEFORE touching code, diagnoses the actual cause, picks a different approach if the prior one was the wrong shape, and tries again.

After 3 failures on the same task:

- `TASK_RETRY_EXHAUSTED` logged.
- Task marked `blocked` in `tasks.md`.
- Orchestrator escalates: if ≥50% of total tasks have passed, SHIP_PARTIAL (commit WIP + integration + push + WIP PR). Otherwise HARD_HALT (commit WIP + HANDOFF.md + exit).

You'll see the disposition in the final report:

```
Disposition: SHIPPED-PARTIAL    (or HALTED)
Next action: Review the partial PR / resume via /agent-pipeline-claude:run resume <run-id>
```

---

## 7. Resuming a halted run

If the run halted on a blocker:

```
/agent-pipeline-claude:run resume 2026-05-14-fix-auth-timeout
```

The orchestrator reads `run.log`, finds the last `TASK_PASSED` or `TASK_RETRY_EXHAUSTED`, and resumes at the next task. Prior tasks stay committed; the resumed run continues from where it stopped.

---

## 8. Listing runs

```
/agent-pipeline-claude:run status
```

Prints up to 10 most recent runs:

```
2026-05-14-fix-auth-timeout      mode=task    last: PR_OPENED @ 5m ago    status: SHIPPED
2026-05-14-cleanroom-linux-wsl   mode=sprint  last: TASK_STARTED @ 1h ago  status: RUNNING
2026-05-13-slice1-commits-1-3    mode=sprint  last: RUN_DONE @ 1d ago      status: SHIPPED
```

---

## 9. The scope contract (what you're approving)

When you see the scope gate, you're approving this contract (rendered as `.agent-runs/<run-id>/scope.md`):

```markdown
# Scope contract — 2026-05-14-fix-auth-timeout

**Goal**: Fix the auth-timeout bug — bump JWT cookie expiry from 24h to 14d

**Mode**: task

**Branch**: fix/auth-timeout-14d (NEW branch off master)

**Allowed paths**:
- backend/auth/

**Forbidden paths**:
- docs/adr/
- pyproject.toml
- .github/workflows/
- CHANGELOG.md

**Success criteria**:
- All tests pass (`pytest`)
- Lint clean (`ruff check`)

**Tasks**:

1. Patch JWT cookie expiry constant in backend/auth/jwt.py
   - Description: change the COOKIE_MAX_AGE constant from 86400 (24h) to 1209600 (14d).
     Update the JWT-issue route to read from the constant.
   - Success: test_auth_timeout passes
```

After GO, this contract is **locked**. The worker can't add new files outside `allowed_paths` mid-run; the scope.md is the binding scope contract.

If the contract is wrong, click **REVISE** at the scope gate. You'll be asked what to change; the orchestrator re-drafts and re-fires the gate. Up to 3 revise cycles per run.

---

## 10. CLAUDE.md conventions (recommended)

The orchestrator and worker both read `CLAUDE.md` if present. Useful entries:

```markdown
# CLAUDE.md

Stack: Python 3.12+, pytest, ruff
Test command: pytest -q
Lint command: ruff check .
Type-check: mypy
Branch convention: feature/<slug>, fix/<slug>, rung/<version>
Commit convention: Conventional Commits with scope (auth, api, frontend, etc.)
```

This lets the worker pick the right commands without guessing.

---

## 11. Troubleshooting

**"Plugin loaded but `/agent-pipeline-claude:run` is unrecognized"** — check `claude plugin list`; the plugin must be marked `enabled`.

**Scope gate keeps firing REVISE-loop more than 3 times** — your CLAUDE.md or spec is missing key info (test command, branch convention, etc.). The orchestrator will halt and suggest re-running `pipeline-init` to add the missing metadata.

**Worker keeps reporting `blocked` on the same task** — the task description is probably ambiguous, or there's a missing dependency (test fixture, environment variable, etc.). Read `.agent-runs/<run-id>/task-<id>-attempt-3.md` for the diagnosis. Fix the underlying issue, then resume.

**Integration suite fails after all tasks pass** — the orchestrator gives the worker one final shot (no allowed_paths constraint, since the integration failure may be cross-cutting). If that also fails, it pushes a `[WIP]` PR with the integration error in the body. Read the PR body for what's broken.

**Push fails (auth, branch protection, etc.)** — the run halts before opening the PR. Fix the credential/permission, then resume the run.

---

## 12. What v2.0 will NOT do for you

- **Admin-merge a PR.** Never. Operator-only.
- **Push tags.** Never. Operator-only.
- **Create GitHub releases.** Never. Operator-only.
- **Force-push to main / master.** Never. Operator-only.
- **Touch files outside scope.allowed_paths.** Structurally enforced; the worker reports `fails` if it would.

Those are deliberate constraints. Autonomous-shipping-to-merged-main is a different (and much riskier) class of automation; v2.0 stops at "PR opened" and lets you review.
