# Pipeline-init procedure (v2.0)

Initialize a project for autonomous pipeline runs. Scaffold the v2.0 minimal payload — one pipeline shape (sprint), one worker role, two policy helpers.

## Argument shapes

`$ARGUMENTS`:

| Shape | Action |
|---|---|
| empty | Inspect `$PWD`. If git repo → existing-project mode. If empty dir → greenfield mode. |
| File path | Read as PRD/spec. Existing-project mode. |
| URL | `git clone <url>` into a temp dir, then existing-project mode against the clone. |
| Description paragraph | Greenfield mode with this description as the project intent. |

---

## Path 1 — existing-project mode (most common)

### Step 1 — orient

Read in this order (`Read` tool):

1. `CLAUDE.md` at project root (if present) — quote the non-negotiables.
2. `README.md` — extract project description.
3. `.git/HEAD` + `git log --oneline -10` — current branch, recent activity, commit-message convention.
4. Existing `.pipelines/` (if present) — flag for re-init handling.
5. Existing `scripts/policy/` (if present) — flag for re-init.

### Step 2 — show orientation summary

Plain chat message (NO modal). Format:

```
Orientation — <project name from README or dir name>

  CLAUDE.md:                 found | missing
  README.md:                 found | missing
  Branch:                    <current>
  Commit convention:         <detected: Conventional Commits | conventional with scope | plain | unknown>
  Existing .pipelines/:      <present (will preserve) | absent>
  Existing scripts/policy/:  <present (will preserve) | absent>

Plan:
  - Scaffold .pipelines/sprint.yaml, .pipelines/sprint-task.yaml,
    .pipelines/roles/worker.md
  - Scaffold scripts/policy/run_status.py, scripts/policy/validate_scope.py
  - (Optional) write starter CLAUDE.md if missing

  Reply APPROVE to scaffold, or REVISE to change the plan.
```

Wait for user reply.

### Step 3 — handle the reply

- **APPROVE** → run `python scripts/scaffold_pipeline.py --target <project-root>` (use `--force` only if user explicitly said to overwrite an existing `.pipelines/`).
- **REVISE** → wait for the user's revision; common revisions: "don't write CLAUDE.md", "force-overwrite the .pipelines/", "skip the policy scripts".
- Any other text → treat as REVISE.

### Step 4 — scaffold

Use the bundled `scripts/scaffold_pipeline.py` (located at the plugin's `scripts/scaffold_pipeline.py`, which finds its bundled payload via `DEFAULT_PAYLOAD`).

Confirm with a final chat message after success:

```
Scaffolded into <project-root>:
  .pipelines/sprint.yaml
  .pipelines/sprint-task.yaml
  .pipelines/roles/worker.md
  scripts/policy/run_status.py
  scripts/policy/validate_scope.py

Next: invoke `/agent-pipeline-claude:run "<your goal>"` to start your first sprint.
```

### Step 5 — starter CLAUDE.md (only if missing)

If no CLAUDE.md exists at root, ASK whether to write a starter — don't write unilaterally:

```
No CLAUDE.md at project root. Want me to scaffold a starter?
It will name the project's stack, test command, lint command, and branch convention based on what I saw — you edit from there. Reply YES or SKIP.
```

If YES, write a minimal CLAUDE.md at `<project>/CLAUDE.md` derived from the orientation. Keep it ≤ 50 lines.

---

## Path 2 — greenfield mode

If `$PWD` is an empty directory OR `$ARGUMENTS` is a description paragraph (not a file path or URL):

1. Show orientation: "Greenfield project. I'll write a starter README.md + CLAUDE.md + a sprint.yaml/sprint-task.yaml/worker.md scaffold."
2. APPROVE in chat → scaffold all of: starter README, starter CLAUDE.md, the v2.0 payload.

---

## Path 3 — URL mode

If `$ARGUMENTS` is a URL (matches `^https?://` or `^git@`):

1. `git clone <url>` into a sibling temp dir.
2. `cd` into the clone.
3. Continue with Path 1 (existing-project mode).

---

## Re-init handling

If `.pipelines/` already exists in the target:

1. The orientation message names this explicitly.
2. APPROVE without `--force` is a NO-OP for the .pipelines/ side (script returns exit 1 with a clean error).
3. To overwrite, the user replies `APPROVE --force` (treat as the force flag) OR explicitly says "overwrite the existing .pipelines/".

For an old v1.3 layout in `.pipelines/` (feature.yaml + 14 role files + manifest-template.yaml), pipeline-init does NOT auto-migrate. Offer:

- "Backup the v1.3 .pipelines/ to .pipelines.v1.3.bak and write v2.0 fresh? (Reply YES or BACKUP-ONLY)"

The user makes the call. Migration is not automatic; v2.0 is a deliberate scope reduction and the operator should see what's being dropped.

---

## Hard rules

- **Never overwrite CLAUDE.md** without explicit YES.
- **Never overwrite `.pipelines/`** without explicit `--force` or "overwrite" intent.
- **Never write outside the project root.**
- **Never read the plugin's `~/.claude/plugins/marketplaces/` directory.** Read only the project under inspection.
- **One chat-APPROVE per init.** No modal dialog. Pipeline-init is light.
- **The scaffold is deterministic.** `scripts/scaffold_pipeline.py` is the single source — there's no manual file-by-file copy from the skill.
