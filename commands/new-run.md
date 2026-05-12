---
description: "[DEPRECATED v1.0 → removed v1.1] Initialize a new pipeline run. Use /run instead."
argument-hint: <pipeline-type> <slug>
---

# /new-run — DEPRECATED

This command is deprecated as of v1.0. Use `/run` instead.

## What to do

Print this deprecation notice verbatim to the user:

```
/new-run is deprecated as of v1.0 and will be removed in v1.1.

Use /run instead — it does what /new-run + /run-pipeline did, but in
one step, and it drafts the manifest from your project's spec rather
than asking you to fill in a blank YAML.

  Old: /new-run feature my-task-slug
       (then fill in manifest.yaml by hand)
       /run-pipeline feature 2026-05-11-my-task-slug

  New: /run "short description of the work"
       (review the drafted manifest, reply APPROVE)
```

Then check whether the user wants to continue with the legacy flow or switch to `/run`:

- If `$ARGUMENTS` is present, offer to translate: *"I see you typed `/new-run <args>`. Want me to delegate to `/run "<derived-description-from-args>"` instead? Reply YES to switch, or LEGACY to fall through to the old /new-run behavior for one more run."*
- If the user replies `YES`, hand off to `/run` with the description derived from `$ARGUMENTS` (use the slug as the description if no other context exists).
- If `LEGACY`, fall through to the v0.5.2 behavior below. Note that this path is unmaintained — bugs in the legacy flow will not be fixed.

## Legacy fallback (v0.5.2 behavior, unmaintained)

Only runs when the user explicitly says `LEGACY`. Mirrors the v0.5.2 `/new-run`:

1. Parse `$ARGUMENTS` into `pipeline_type` and `slug`.
2. Validate `pipeline_type` matches a `.pipelines/<pipeline_type>.yaml`.
3. Validate `slug` matches `^[a-z0-9][a-z0-9-]*$`.
4. `run_id = YYYY-MM-DD-<slug>`.
5. `mkdir -p .agent-runs/<run_id>/`.
6. Read `.pipelines/manifest-template.yaml`.
7. Write `.agent-runs/<run_id>/manifest.yaml` with `id` + `type` substituted, everything else from the template.
8. Print the manifest in chat for the user to fill in by hand.
9. Tell the user the next command is `/run-pipeline <pipeline_type> <run_id>` (also deprecated).

This shim exists for one minor release to give v0.5.2 users a soft cutover. It will be removed at v1.1.

## Hard rules

- Always print the deprecation notice. Never silently delegate.
- Never modify files in `.pipelines/` or `scripts/policy/`.
- Never start a pipeline run from this command (legacy fallback only writes the manifest; the user has to type `/run-pipeline` or `/run` to start).
