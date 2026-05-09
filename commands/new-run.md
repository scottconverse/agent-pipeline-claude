---
description: Initialize a new pipeline run (creates the manifest skeleton). Run /pipeline-init first if the project isn't initialized.
argument-hint: <pipeline-type> <slug>
---

# /new-run — initialize a pipeline run

You are initializing a new agentic pipeline run. Do not start the pipeline. Do not validate semantic content of the manifest. Just initialize the directory and the manifest skeleton, then hand off to the user.

## Prerequisite

The user's project must have been initialized with `/pipeline-init` first. Verify by checking that `.pipelines/<pipeline-type>.yaml` and `.pipelines/manifest-template.yaml` exist. If not, stop and tell the user to run `/pipeline-init` first.

## Arguments

`$ARGUMENTS` is one line containing two whitespace-separated tokens:

- **`<pipeline-type>`** — must match a YAML in `.pipelines/` (typically `feature` or `bugfix`).
- **`<slug>`** — kebab-case task name, e.g. `auth-timeout`. Lowercase ASCII, hyphens only.

Example: `feature auth-timeout`

If `$ARGUMENTS` does not contain exactly two tokens, stop and tell the user the correct usage: `/new-run <pipeline-type> <slug>`.

## What to do

Execute these steps in order. Do not skip any. Do not run a Bash subshell loop — perform each step as its own tool call.

### 1. Parse arguments

Split `$ARGUMENTS` into `pipeline_type` and `slug`. Trim whitespace.

Validate `pipeline_type` matches a `.pipelines/<pipeline_type>.yaml` file. If not, list available pipelines (every `.yaml` under `.pipelines/` except `manifest-template.yaml`) and stop.

Validate `slug` matches `^[a-z0-9][a-z0-9-]*$`. If not, stop and report the format requirement.

### 2. Generate run id

`run_id = "{today_iso_date}-{slug}"` where `today_iso_date` is `YYYY-MM-DD` from the system date. Use the Bash tool to get today's date: `date +%Y-%m-%d`.

### 3. Verify the pipeline definition exists

Read `.pipelines/<pipeline_type>.yaml`. If the Read tool fails, stop with a usage message listing the YAMLs that DO exist under `.pipelines/`.

### 4. Create the run directory

Use Bash: `mkdir -p .agent-runs/<run_id>`.

If the directory already exists AND already contains a `manifest.yaml`, stop and tell the user the run already exists. Do not overwrite.

### 5. Read the manifest template

Read `.pipelines/manifest-template.yaml` in full. You will use its content as the starting point, modifying only the `id` and `type` fields.

### 6. Write the manifest

Write `.agent-runs/<run_id>/manifest.yaml`. Take the template content verbatim and replace exactly two values:

- The `id: ""` line becomes `id: "<run_id>"`.
- The `type: feature` line becomes `type: <pipeline_type>` (only change if `pipeline_type` differs from the template default).

Preserve every other line of the template, including all comments. The user fills in the rest.

### 7. Display the manifest to the user

Read the file you just wrote and print its contents to the user verbatim inside a fenced code block, so they can see exactly what fields they need to fill in.

### 8. Hand off via AskUserQuestion

Use `AskUserQuestion` to present this question:

- **Question:** `Run initialized at .agent-runs/<run_id>/manifest.yaml`
- **Header:** `Next step`
- **Options:**
  - Label: `I'll fill it in now` — Description: `Open the file in your editor, complete every field, then run /run-pipeline <pipeline_type> <run_id>.`
  - Label: `What goes in each field?` — Description: `Read .pipelines/manifest-template.yaml — every field has an inline comment explaining what it expects.`

Do not start the pipeline. Do not validate the manifest content. The pipeline runner (`/run-pipeline`) does that as its first step.

## Hard rules

- Do not modify `.pipelines/manifest-template.yaml` itself.
- Do not write to any path other than the new `.agent-runs/<run_id>/manifest.yaml`.
- Do not invoke any agent.
- Do not run policy checks, tests, or builds.
- If any validation fails, stop and report — do not paper over the failure with defaults.
