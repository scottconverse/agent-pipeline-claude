---
name: pipeline-init
description: Initialize a project for pipeline runs. Inspects what the project already has (spec, release plan, CLAUDE.md, tests, CI), produces an orientation summary for chat APPROVE, then scaffolds .pipelines/, scripts/policy/, and a starter CLAUDE.md if missing. Invoked as /agent-pipeline-claude:pipeline-init.
---

# Pipeline-init

Follow the canonical workflow in `references/pipeline-init.md`. That document is the single source of truth for orientation, scaffolding contents, the APPROVE gate, greenfield handling, and re-init handling.

Tool mapping for Claude Code:

- Use **Bash** for `git status`, `ls`, `git log` orientation.
- Use **Read** to inspect the project's existing spec / release plan / CLAUDE.md.
- Use **Write** for scaffolded files; use **Edit** for amending an existing CLAUDE.md only with explicit user APPROVE.
- Render the orientation summary as a plain chat message — do not use `AskUserQuestion` for the APPROVE gate.

`$ARGUMENTS` is one of: empty (inspect cwd), a file path (read as PRD), a URL (`git clone` first), or a description paragraph (greenfield mode).

Hard rules:

- Never overwrite an existing `CLAUDE.md` without explicit user APPROVE.
- Never overwrite an existing `.pipelines/` directory; treat as re-init and ask which subset to refresh.
- Never copy any file outside the project root.
- Never read or modify the plugin's own marketplace dir under `~/.claude/plugins/marketplaces/`.
- Always produce the orientation summary BEFORE scaffolding.
