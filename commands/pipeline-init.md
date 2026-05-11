---
description: Initialize a project for the agentic pipeline. Onboards new projects from a PRD, an existing repo URL, or a description paragraph.
argument-hint: (none — interactive)
---

# /pipeline-init — onboard a project for agentic pipeline runs

You are onboarding a project for use with the agentic pipeline plugin. The user has one of three things and you need to figure out which, then act on it. **You do not skip the orientation step. You do not silently scaffold based on assumptions.**

## What to do

### Step 1 — Detect the input shape

If `$ARGUMENTS` is non-empty, parse it. The user may have passed a path, URL, or quoted description. Otherwise use `AskUserQuestion` to ask:

- **Question:** `What do you have? Drop one of: a PRD/spec document path, a repo URL or local path, or paste a project description.`
- **Header:** `Project input`
- **Options:**
  - Label: `PRD or spec document` — Description: `I have a written specification document for this project. I'll paste the path or contents in the next message.`
  - Label: `Existing repo (URL or local path)` — Description: `I have an existing project repo somewhere. I'll paste the URL or local path in the next message.`
  - Label: `Description paragraph` — Description: `I have a paragraph or two describing what I want to build. I'll paste it in the next message.`

After the user picks an option, ask for the actual content if not already provided.

### Step 2 — Branch by path

#### Path 1: PRD or spec document

1. Read the document (Read tool if it's a file path; treat as inline text otherwise).
2. Extract: project name, one-sentence purpose, target audience, primary capabilities, technical constraints, license posture, any named conventions (e.g., "uses Python 3.12", "frontend is React", "DB is Postgres").
3. Determine the project's working directory:
   - If the user is currently in a project directory with files (i.e., `git status` returns a real result), use that directory.
   - If the current directory is empty, ask `AskUserQuestion`: `Use this directory or create a subdirectory?` with options `Use current directory` / `Create subdirectory`. If subdirectory, ask for the name (kebab-case).
4. Run **Step 3 (scaffold)** with the extracted context.

#### Path 2: Existing repo (URL or local path)

1. Determine if it's a remote URL (starts with `https://` or `git@`) or a local path.
2. If remote and not already cloned: ask `AskUserQuestion`: `Clone to current directory or specify a target?` then `git clone` it.
3. If local: `cd` to it.
4. Inspect the repo:
   - `git log --oneline -5` — recent commits
   - Read `README.md` (or `README` or `readme.md`) if present
   - Read `CLAUDE.md` at root if present
   - Read `pyproject.toml`, `package.json`, `Cargo.toml`, `go.mod`, `Gemfile`, etc. — whichever exist
   - List `.github/workflows/` if it exists
   - List `docs/adr/` if it exists
   - Check for an existing `.pipelines/` directory (if present, the project is already initialized — ask if user wants to re-init or update)
5. Produce a **project-orientation summary** for the user (markdown, displayed inline, NOT written to a file at this stage):
   - Project name + one-sentence inferred purpose
   - Detected stack (language, framework, test runner, lint, type checker)
   - Detected conventions (commit format, branch naming, ADR presence, CLAUDE.md presence)
   - Missing pieces flagged (e.g., "no CLAUDE.md found — I'll scaffold a minimal one", "no docs/adr/ — ADR gate will be disabled until you add one")
6. Ask user via `AskUserQuestion`: `Project orientation looks correct? Type APPROVE to scaffold the pipeline, or describe what's wrong.` If APPROVE, run **Step 3 (scaffold)**. Otherwise, take their feedback and adjust.

#### Path 3: Description paragraph

1. Read the description.
2. Ask `AskUserQuestion`: `Is this a NEW project to scaffold from scratch, or context for an EXISTING repo?` with options `New project` / `Existing repo`.
3. If **new project**: prompt for a project name (kebab-case), then synthesize a minimal PRD from the description and treat as Path 1.
4. If **existing repo**: prompt for repo URL or local path and treat as Path 2 (the description goes into the orientation summary as user-provided context).

### Step 3 — Scaffold (shared across all paths)

Once the project's working directory is identified and the orientation is settled, scaffold:

1. **`.pipelines/` directory** — copy from the plugin's `pipelines/` directory:
   - `feature.yaml`
   - `bugfix.yaml`
   - `manifest-template.yaml`
   - `roles/` (all 6 role files)

2. **`scripts/policy/` directory** — copy from the plugin's `scripts/`:
   - `__init__.py`
   - `check_allowed_paths.py`
   - `check_no_todos.py`
   - `check_adr_gate.py`
   - `run_all.py`

3. **`.gitignore`** — append `.agent-runs/` (create file if it doesn't exist; check for existing entry before appending to avoid duplicates).

4. **`CLAUDE.md`** — only if the project doesn't have one:
   - Scaffold a minimal `CLAUDE.md` populated from the orientation summary (project purpose, stack, conventions). Include sections for: order of operations, layered audit pattern (4 altitudes), closed architectural decisions (empty until first ADR), open decisions (empty), tooling, non-negotiables (empty placeholder), git workflow, role posture, and "What you never do" list.
   - The user is expected to edit this. The plugin gives them a starting structure, not the final word.

5. **`AGENTS.md`** (v0.6+) — only if the project will also use Codex. Ask via `AskUserQuestion`: `Will this project be worked on by Codex as well as Claude Code?` with options `Yes — scaffold AGENTS.md too` / `Claude Code only — skip AGENTS.md`. If yes, copy the plugin's `pipelines/templates/AGENTS.md` to the project root. Do not overwrite an existing `AGENTS.md`; ask first.

5. **Display a summary** to the user:
   - What was scaffolded (file list)
   - What was inferred about the project
   - What's missing (no `docs/adr/`? no CI? no tests directory?) and what each gap means for downstream pipeline behavior
   - Next step: `/new-run feature <slug>` to start the first pipeline run

### Step 4 — Hand off via AskUserQuestion

Use `AskUserQuestion` (load via ToolSearch if not available):

- **Question:** `Project initialized. Ready to start your first pipeline run?`
- **Header:** `Next step`
- **Options:**
  - Label: `Yes — start a feature run` — Description: `I'll suggest /new-run feature <slug> with a slug derived from the project context.`
  - Label: `Yes — start a bugfix run` — Description: `I'll suggest /new-run bugfix <slug>.`
  - Label: `Not yet — let me edit CLAUDE.md and the manifest template first` — Description: `Recommended if you want to customize the project conventions before the first run.`

## Hard rules

- Do not modify any file outside the user's project directory and the plugin's read-only template files.
- Do not silently overwrite existing `CLAUDE.md`, `.pipelines/`, or `scripts/policy/` if they already exist. Ask first.
- Do not skip the orientation summary even if "it seems obvious from the inputs." Show your work.
- Do not propose autonomous mode at any point. The plugin's defaults are explicit-gate-only.
- If the user provides input that's malformed or contradicts itself (e.g., "PRD" but the file is empty), STOP and ask for clarification — do not improvise from defaults.
- If the user is in a directory that already has a `.pipelines/` directory, treat as a re-init: ask whether to update the role/policy files (and which) rather than overwrite blindly.

## Output checklist

Stage complete only when:
- Project's working directory is identified.
- Orientation summary was shown to the user.
- `.pipelines/` is present in the project with the 4 expected files (feature.yaml, bugfix.yaml, manifest-template.yaml, roles/).
- `scripts/policy/` is present with 5 expected files (__init__.py + 4 scripts).
- `.gitignore` has `.agent-runs/` (or was created).
- `CLAUDE.md` exists (either pre-existing or scaffolded).
- `AGENTS.md` exists if Codex is in scope (v0.6+), otherwise skipped.
- User has been told what to do next (`/new-run feature <slug>` or similar).
