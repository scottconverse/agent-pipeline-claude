---
name: pipeline-init
description: Initialize a project for v2.0 autonomous pipeline runs. Inspects the project briefly (CLAUDE.md, README, recent commits) and scaffolds the v2.0 payload — `.pipelines/sprint.yaml`, `.pipelines/sprint-task.yaml`, `.pipelines/roles/worker.md`, `scripts/policy/run_status.py`, `scripts/policy/validate_scope.py`. Skips a starter CLAUDE.md if the project already has one. Single chat-message APPROVE; no modal dialog. Invoked as /agent-pipeline-claude:pipeline-init.
---

# Pipeline-init (v2.0)

Follow the canonical workflow in `references/pipeline-init.md`. That document is the single source of truth for orientation, the chat-message APPROVE gate, the scaffold payload, and greenfield handling.

Tool mapping:

- **`Bash`** for `git status`, `ls`, `git log` orientation + the actual scaffolding (calls `python scripts/scaffold_pipeline.py --target <project-root>`).
- **`Read`** to inspect existing CLAUDE.md / README / spec.
- **`Write`** for a starter CLAUDE.md (only if none exists).
- Plain chat message for the APPROVE gate — NO `AskUserQuestion` modal here. Pipeline-init is light; one chat round-trip is the right cost.

`$ARGUMENTS` is one of:

- empty — inspect cwd in greenfield-or-existing mode
- a file path — read as PRD/spec
- a URL — `git clone` first, then init
- a description paragraph — greenfield mode

Hard rules:

- **Scaffold is v2.0 minimal.** 3 pipeline files + 2 policy scripts. Total ~600 lines of payload. NOT the v1.3.x 14-roles + 18-scripts behemoth.
- **Never overwrite an existing `.pipelines/`** without explicit APPROVE. Re-init asks which subset to refresh.
- **Never overwrite an existing CLAUDE.md.** Offer to APPEND or skip — never replace.
- **Never write outside the project root.**
- **Never read or modify the plugin's marketplace dir.**
- **One orientation summary BEFORE scaffolding.** User APPROVE in chat advances the scaffold.
