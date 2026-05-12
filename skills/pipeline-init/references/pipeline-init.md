# Pipeline-init procedure — onboard a project

You are onboarding a project for use with the agent-pipeline-claude plugin. Most projects only need to run this once.

The plugin needs three things to do useful work later:
1. A `.pipelines/` directory with role files + pipeline definitions.
2. A `scripts/policy/` directory with the validation scripts.
3. A `CLAUDE.md` capturing the project's conventions (the manifest-drafter reads it).

This command produces all three, drafted from whatever the project already has.

## Argument shapes

`$ARGUMENTS` is one of:

1. **Empty** — the common case. You're standing in the project root; this command inspects what's there.
2. **A file path** — points at a PRD, spec, or description document. Read it as the source of truth for project orientation.
3. **A URL** — a repo URL. The current working directory must be empty; this command will `git clone` then init.
4. **A description paragraph** quoted at the prompt. Treat as inline-content PRD.

## What to do

### Step 1 — orient

Detect the project's current state:

```bash
git status            # Are we in a repo? Clean tree?
ls                    # What's at the root?
git log --oneline -5  # Recent commits — gives context on the project's life
```

Look for spec / release-plan / scope-lock / design-note artifacts using the same patterns the manifest-drafter walks (see `references/pipeline-payload/pipelines/roles/manifest-drafter.md` § "Source-walking protocol"). Look for stack indicators: `pyproject.toml`, `package.json`, `Cargo.toml`, `go.mod`, etc. Look for `.github/workflows/`, `docs/adr/`, `CLAUDE.md`.

### Step 2 — produce a one-message orientation summary

Send the user a single chat message with:

```
Project orientation:

  Name: <inferred>
  Stack: <language, framework, test runner, lint, type checker>
  Existing artifacts: <list of relevant docs found, e.g. "CivicCastUnifiedSpec-v2.md, CivicCast-ReleasePlan, docs/releases/v0.4-scope-lock.md, CLAUDE.md">
  Missing: <gaps, e.g. "no docs/adr/ — the ADR policy gate will be disabled until you add one">
  Test framework: <pytest | jest | unknown>
  CI: <detected workflow files or "none">

Reply `APPROVE` to scaffold .pipelines/ + scripts/policy/ + (if missing) CLAUDE.md.
Reply `WAIT` to fix anything in the summary first.
Reply with corrections in plain English and I'll re-summarize.
```

Do NOT scaffold without an explicit `APPROVE`.

### Step 3 — scaffold on APPROVE

When the user replies `APPROVE`:

**Source of truth for the scaffolded files:** the bundled payload at
`references/pipeline-payload/` inside this skill (resolved relative to the
skill's install directory — `skills/pipeline-init/`). The payload ships INSIDE
the skill so it's always available, including when the plugin runs from an
installed cache where the repo-root `pipelines/` and `scripts/` paths don't
exist.

1. **`.pipelines/` directory.** Copy from `references/pipeline-payload/pipelines/` into the project root as `.pipelines/`:
   - `feature.yaml`
   - `bugfix.yaml`
   - `module-release.yaml` (if user wants module-release support; default yes for projects with version files)
   - `manifest-template.yaml`
   - `self-classification-rules.md`
   - `roles/` (all role files, including `manifest-drafter.md`)
   - `templates/` (the audit-handoff templates)

2. **`scripts/policy/` directory.** Copy from `references/pipeline-payload/scripts/` into the project root as `scripts/policy/`:
   - `__init__.py`
   - `check_manifest_schema.py`
   - `check_allowed_paths.py`
   - `check_no_todos.py`
   - `check_adr_gate.py`
   - `auto_promote.py`
   - `run_all.py`

3. **`.gitignore`** — append `.agent-runs/` if not already present.

4. **`CLAUDE.md`** — if the project doesn't have one, scaffold a starter. The starter is short (no boilerplate) and includes ONLY:
   - One paragraph: what this project is, derived from Step 2 orientation.
   - `## Pipeline drafter notes` section — tells the manifest-drafter where this project keeps its spec, release plan, scope-locks, design notes, ledgers, and HANDOFF. This is the file's most important section for v1.0 operation.
   - `## Order of operations` — three sentences on how changes flow (e.g. "branch from main, work in slices, tag at rung close").
   - `## Tooling` — language, test runner, lint, type checker, pre-commit hooks.
   - `## Non-negotiables` — empty placeholder for the user to fill in.

   The user is expected to edit it. The plugin gives a starting shape, not the final word.

5. **Final scaffold report.** Send a chat message:
   ```
   Scaffold complete.

   Created:
     .pipelines/  (<N> role files, <M> pipeline definitions)
     scripts/policy/  (<K> validation scripts)
     CLAUDE.md  (starter — edit before your first run)
     .gitignore  updated

   Missing pieces (you can fix any time):
     - No docs/adr/ — ADR policy gate disabled until first ADR
     - No tests/ directory — test-tracking will be approximate

   Next step:
     /run "short description of your first run"

   IMPORTANT: if you just installed the plugin via the file-level
   install (clone + JSON patch), restart Cowork before /run becomes
   available in the slash-command palette.
   ```

### Step 4 — the Cowork install reality

The user may be running `/pipeline-init` right after a fresh install. Two scenarios:

**Scenario A — they used the file-level install (Cowork).** They cloned the repo and patched JSON files (or you/Claude did it for them). The slash commands register at session start, so the user is reading this in a fresh Cowork session AFTER restart. Everything works.

**Scenario B — they used `/plugin install` (CLI with that command available).** Same outcome — the slash commands are available.

If `/pipeline-init` itself doesn't appear available, the user can't be reading these instructions. So Scenario A/B is the universe; this command only runs once the plugin is loaded.

What the command DOES need to flag, at end of Step 3: if the user then runs `/run` and gets "command not available," they should restart Cowork. The scaffold report's final paragraph names this.

## Hard rules

- Never overwrite an existing `CLAUDE.md`. If it exists, ask whether to APPEND a `## Pipeline drafter notes` section (the part the drafter needs) or skip.
- Never overwrite an existing `.pipelines/` directory. If it exists, treat as re-init: ask whether to refresh the role files (and which) or skip.
- Never copy any file outside the project root the user is in.
- Never read or modify the plugin's own marketplace dir under `~/.claude/plugins/marketplaces/`.
- Always produce an orientation summary BEFORE scaffolding. Show your reading; let the user correct it.

## Greenfield handling

If `$ARGUMENTS` is a description paragraph (no spec file exists, no repo to read), synthesize a minimal spec inline:

```
You gave me a description but no existing spec. Synthesizing a minimal
spec now — review and reply APPROVE to write it to SPEC.md, or `WAIT`
if you'd rather edit it inline first.

```
[synthesized minimal spec: 1-2 paragraphs of purpose, target audience,
core capabilities, tech-stack inferences, license]
```
```

Once approved, write `SPEC.md` at project root and continue to Step 2 with `SPEC.md` as the read source.

## Re-init handling

If `.pipelines/` already exists, the project was initialized before. Send:

```
Project is already initialized (.pipelines/ exists with <N> files).

Want to:
  (a) Refresh role files from the current plugin version (useful after upgrading the plugin).
  (b) Refresh policy scripts only.
  (c) Refresh everything (role files + policy scripts + manifest template).
  (d) Cancel — leave the existing setup as-is.

Reply with a, b, c, or d.
```

Apply the selected option; do NOT touch the user's `.agent-runs/`, manifests, or CLAUDE.md without explicit consent.
