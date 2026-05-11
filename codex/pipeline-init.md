# codex/pipeline-init — onboard a project for agentic pipeline runs (Codex)

**How to use this file:** paste this whole document into a fresh Codex session
as the first message. Codex will follow the steps to scaffold the pipeline into
the current project. The Claude Code equivalent is `commands/pipeline-init.md`;
the two produce equivalent results.

---

You are onboarding a project for the agentic-pipeline discipline
(https://github.com/scottconverse/agentic-pipeline). The user has one of three
things, and your first job is to figure out which:

1. A PRD/spec document (path or pasted text).
2. An existing repo (URL or local path).
3. A description paragraph for a new project.

Do not skip the orientation step. Do not silently scaffold based on assumptions.

## Step 1 — Detect the input

If the user has already pasted a path, URL, or description in their message,
parse it. Otherwise ask the user in plain English:

> "What do you have? (a) a PRD/spec document path, (b) a repo URL or local path,
> or (c) a description paragraph?"

After they pick, ask for the actual content if not yet provided.

## Step 2 — Branch by path

### Path 1 — PRD or spec document

1. Read the document.
2. Extract: project name, one-sentence purpose, target audience, primary
   capabilities, technical constraints, license posture, named conventions.
3. Identify the project working directory. If empty, ask whether to scaffold
   here or in a subdirectory.
4. Run Step 3.

### Path 2 — Existing repo

1. If remote URL: `git clone` it (ask where).
2. If local path: change into it.
3. Inspect:
   - `git log --oneline -5`
   - Read `README.md`, `CLAUDE.md`, `AGENTS.md` if present
   - Read `pyproject.toml` / `package.json` / `Cargo.toml` / `go.mod` /
     `Gemfile` (whichever exist)
   - List `.github/workflows/`, `docs/adr/`
   - Check for existing `.pipelines/` (if present, ask whether to re-init or
     update)
4. Produce a project-orientation summary inline (markdown):
   - Project name + inferred purpose
   - Detected stack (language, framework, test runner, lint, type checker)
   - Detected conventions (commit format, branch naming, ADR presence)
   - Missing pieces flagged
5. Ask the user: "Orientation correct? Type APPROVE to scaffold, or describe
   what's wrong."
6. On APPROVE, run Step 3.

### Path 3 — Description paragraph

1. Read the description.
2. Ask: "New project to scaffold from scratch, or context for an existing repo?"
3. New project: ask for a kebab-case name, synthesize a minimal PRD, treat as
   Path 1.
4. Existing repo: ask for URL or local path, treat as Path 2 with the
   description as orientation context.

## Step 3 — Scaffold

Once the working directory is identified and orientation is settled, scaffold
these files from the agentic-pipeline plugin source. The plugin repo lives at
the user's clone path (ask if not obvious — typical:
`~/agentic-pipeline/` or wherever they checked it out).

1. **`.pipelines/` directory** — copy from `<plugin>/pipelines/`:
   - `feature.yaml`
   - `bugfix.yaml`
   - `module-release.yaml` (optional; ask)
   - `manifest-template.yaml`
   - `action-classification.yaml` (optional; only if user wants judge layer)
   - `self-classification-rules.md`
   - `roles/` (all role files: `researcher.md`, `planner.md`,
     `test-writer.md`, `executor.md`, `verifier.md`, `drift-detector.md`,
     `critic.md`, `manager.md`, plus `judge.md` if action-classification was
     copied)

2. **`scripts/policy/` directory** — copy from `<plugin>/scripts/`:
   - `__init__.py`
   - `check_manifest_schema.py`
   - `check_allowed_paths.py`
   - `check_no_todos.py`
   - `check_adr_gate.py`
   - `auto_promote.py`
   - `run_all.py`

3. **`.gitignore`** — append `.agent-runs/` (idempotent; check for existing
   entry first).

4. **`AGENTS.md`** — only if this project will use Codex. Copy
   `<plugin>/pipelines/templates/AGENTS.md` to the repo root. The user is
   expected to edit it with project-specific conventions.

5. **`CLAUDE.md`** — only if this project will use Claude Code AND no
   `CLAUDE.md` exists. Scaffold a minimal one populated from the orientation
   summary.

Ask the user which AI runtimes they intend to use (Claude Code, Codex, or both)
and scaffold accordingly. If both, scaffold both `AGENTS.md` and `CLAUDE.md`.

## Step 4 — Display summary

Print to the user:

- What was scaffolded (file list).
- What was inferred (stack, conventions).
- What's missing (no `docs/adr/`? no CI? no tests directory?) and what each
  gap means for downstream pipeline behavior.
- Next step: paste `codex/new-run.md` into a fresh Codex session to start the
  first pipeline run.

## Hard rules

- Do not modify any file outside the user's project directory and the plugin's
  read-only template files.
- Do not silently overwrite existing `CLAUDE.md`, `AGENTS.md`, `.pipelines/`, or
  `scripts/policy/`. Ask first.
- Do not skip the orientation summary even if "it seems obvious."
- Do not propose autonomous mode. The plugin's defaults are explicit-gate-only.
- If input is malformed or contradicts itself, STOP and ask for clarification.
- If `.pipelines/` already exists, treat as re-init — ask which files to update
  rather than overwrite blindly.

## Output checklist

Stage complete only when:

- Project working directory is identified.
- Orientation summary was shown to the user.
- `.pipelines/` is present with the expected files.
- `scripts/policy/` is present with the expected files.
- `.gitignore` has `.agent-runs/`.
- `AGENTS.md` exists (if Codex is in scope).
- `CLAUDE.md` exists (if Claude Code is in scope).
- User has been told the next step.
