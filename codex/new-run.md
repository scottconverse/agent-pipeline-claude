# codex/new-run — initialize a pipeline run (Codex)

**How to use this file:** paste this whole document into a fresh Codex session
inside a project that has already been initialized with `codex/pipeline-init.md`
(i.e., `.pipelines/` exists). On the same message or the next, tell Codex the
pipeline type and slug: e.g. `feature auth-timeout` or `bugfix login-500`.

The Claude Code equivalent is `commands/new-run.md`; the two produce equivalent
results.

---

You are initializing a new agentic pipeline run. Do not start the pipeline. Do
not validate semantic content of the manifest. Just initialize the directory
and the manifest skeleton, then hand off to the user.

## Prerequisite

The project must have been initialized first. Verify by checking that
`.pipelines/<pipeline-type>.yaml` and `.pipelines/manifest-template.yaml`
exist. If not, stop and tell the user to paste `codex/pipeline-init.md` into a
fresh Codex session first.

## Arguments

Expect two whitespace-separated tokens from the user:

- `<pipeline-type>` — must match a `.pipelines/<pipeline-type>.yaml`
- `<slug>` — kebab-case task name (lowercase ASCII, hyphens only)

Example: `feature auth-timeout`

If the user didn't provide both, ask in plain English.

## What to do

Execute these steps in order. One tool call per step.

### 1. Parse and validate

Split the input into `pipeline_type` and `slug`.

- Validate `pipeline_type` matches a `.pipelines/<pipeline_type>.yaml`. If not,
  list available pipelines (every `.yaml` under `.pipelines/` except
  `manifest-template.yaml`) and stop.
- Validate `slug` matches `^[a-z0-9][a-z0-9-]*$`. If not, stop and report.

### 2. Generate run id

`run_id = "<YYYY-MM-DD>-<slug>"` using today's date. Get it via shell:
`date +%Y-%m-%d`.

### 3. Verify pipeline definition exists

Read `.pipelines/<pipeline_type>.yaml`. If it doesn't exist, stop with a usage
message listing the YAMLs that DO exist under `.pipelines/`.

### 4. Create the run directory

`mkdir -p .agent-runs/<run_id>`

If the directory already exists AND already contains a `manifest.yaml`, stop
and tell the user the run already exists. Do not overwrite.

### 5. Read the manifest template

Read `.pipelines/manifest-template.yaml` in full.

### 6. Write the manifest

Write `.agent-runs/<run_id>/manifest.yaml`. Take the template verbatim and
replace exactly two values:

- `id: ""` → `id: "<run_id>"`
- `type: feature` → `type: <pipeline_type>` (only if different)

Preserve every other line, including comments.

### 7. Display the manifest

Print the file contents to the user inside a fenced code block so they can see
exactly which fields they need to fill in.

### 8. Hand off

Tell the user in plain English:

> "Run initialized at `.agent-runs/<run_id>/manifest.yaml`. Open it in your
> editor and fill in every field. The fields are documented in
> `.pipelines/manifest-template.yaml` (each has an inline comment). When the
> manifest is ready, paste `codex/run-pipeline.md` into a fresh Codex session
> along with the run id `<run_id>`."

Do not start the pipeline. Do not validate manifest content. The runner does
that as its first step.

## Hard rules

- Do not modify `.pipelines/manifest-template.yaml`.
- Do not write to any path other than the new
  `.agent-runs/<run_id>/manifest.yaml`.
- Do not invoke other agents or stages.
- Do not run policy checks, tests, or builds.
- If any validation fails, stop and report — do not paper over with defaults.
