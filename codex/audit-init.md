# codex/audit-init — scaffold dual-AI audit infrastructure (Codex)

**How to use this file:** paste this whole document into a fresh Codex session
inside a project. Codex will ask the questions needed to scaffold the
audit-handoff infrastructure. The Claude Code equivalent is
`commands/audit-init.md`.

This complements `codex/pipeline-init.md`'s execution discipline with a
verification-side discipline for projects that use two AI systems: one
implements, the other audits. Can be run standalone if the project doesn't
use the full pipeline.

---

You are setting up audit-handoff discipline for a project. Three artifacts get
created, plus optional per-agent wiring:

1. **`<PROJECT>_AUDIT_GATE.md`** at the desktop level (out-of-repo). Short
   mandatory gate the auditor reads every verification turn.
2. **`<PROJECT>_AUDIT_PROTOCOL.md`** at the desktop level. Long reference
   protocol with 10-section output shape, status-word rules, drift catalog.
3. **`<project-repo>/docs/process/5-lens-self-audit.md`** in-repo. Shared by
   both agents; the hostile self-audit the implementer runs before push.

## Step 1 — Gather inputs

Ask the user, in plain English:

- Project name (capitalized, e.g. `CivicSuite`, `CivicCast`)
- Which AI system implements code? (Claude / Codex / Other)
- Which AI system audits? (Claude / Codex / Other — if same as implementer,
  see Step 6)
- Local path to the project repo
- Desktop-level directory where the out-of-repo gate + protocol should live
  (default: parent of the project repo path)

Capture as: `<PROJECT_NAME>`, `<PROJECT_NAME_UPPER>`, `<IMPLEMENTER_AGENT>`,
`<AUDITOR_AGENT>`, `<PROJECT_REPO_PATH>`, `<DESKTOP_PATH>`, `<AUDIT_GATE_PATH>`,
`<AUDIT_PROTOCOL_PATH>`.

## Step 2 — Sanity check

- If `<AUDIT_GATE_PATH>` or `<AUDIT_PROTOCOL_PATH>` already exists, ask:
  "Existing audit infrastructure detected. Overwrite, augment, or abort?"
- If `<PROJECT_REPO_PATH>/docs/process/5-lens-self-audit.md` exists, same
  question.
- Confirm the project repo is a git repo: `git -C <path> rev-parse`.

## Step 3 — Scaffold the three artifacts

Read the three template files from the agentic-pipeline plugin source:

- `<plugin>/pipelines/templates/audit-gate-template.md`
- `<plugin>/pipelines/templates/audit-protocol-template.md`
- `<plugin>/pipelines/templates/5-lens-self-audit-template.md`

Substitute placeholders:

- `<PROJECT_NAME>` → captured value
- `<IMPLEMENTER_AGENT>` → captured
- `<AUDITOR_AGENT>` → captured
- `<AUDIT_GATE_PATH>` → captured path
- `<AUDIT_PROTOCOL_PATH>` → captured path
- `<PROJECT_REPO_PATH>` → captured path

Write the substituted content:

- Gate → `<AUDIT_GATE_PATH>`
- Protocol → `<AUDIT_PROTOCOL_PATH>`
- 5-lens doc → `<PROJECT_REPO_PATH>/docs/process/5-lens-self-audit.md`
  (create `docs/process/` if needed)

## Step 4 — Open a PR for the in-repo doc

The in-repo `docs/process/5-lens-self-audit.md` lands via PR, not direct push.

```sh
cd <PROJECT_REPO_PATH>
git checkout -b process/shared-audit-knowledge
git add docs/process/5-lens-self-audit.md
git commit -m "docs(process): add shared 5-lens self-audit rule for <PROJECT_NAME>"
git push -u origin process/shared-audit-knowledge
gh pr create --title "docs(process): shared 5-lens self-audit rule" --body-file <body>
```

Commit message body:

```
Adds docs/process/5-lens-self-audit.md as the in-repo shared rule both
<IMPLEMENTER_AGENT> (implementer) and <AUDITOR_AGENT> (auditor) read.

Pairs with:
- <AUDIT_GATE_PATH> (out-of-repo, short mandatory gate)
- <AUDIT_PROTOCOL_PATH> (out-of-repo, long reference)

Scaffolded by codex/audit-init from scottconverse/agentic-pipeline v0.6+.
This is process documentation only. No feature work, no code change.
```

Do not merge automatically — let the user review and merge.

## Step 5 — Per-agent wiring

### If Codex is the auditor

Append to the Codex project-control-plane skill
(`~/.codex/skills/project-control-plane/SKILL.md` or equivalent):

```markdown
## <PROJECT_NAME> audit-handoff discipline (Codex is auditor)

For any <PROJECT_NAME> audit, audit-fix, release-gate, or report verification:
- Read `<AUDIT_GATE_PATH>` completely every turn.
- Read `<AUDIT_PROTOCOL_PATH>` for full reference.
- Read `<PROJECT_REPO_PATH>/docs/process/5-lens-self-audit.md` for the shared
  implementer-side rule.

The mandatory 10-section verification output and 5-lens self-audit are
non-negotiable.
```

### If Codex is the implementer

Same skill file, different section:

```markdown
## <PROJECT_NAME> 5-lens self-audit (Codex is implementer)

Before any `git push` on <PROJECT_NAME> work, run a hostile 5-lens self-audit
on the actual diff. Include the audit result in the push report.

Reference: `<PROJECT_REPO_PATH>/docs/process/5-lens-self-audit.md`
```

### If Claude is in either role

Create a memory feedback file at
`~/.claude/projects/<encoded-cwd>/memory/feedback_<project>_audit_protocol.md`
(or the implementer variant). Append a pointer line to `MEMORY.md`.

Content matches the patterns in the Claude Code `commands/audit-init.md`.

### If "Other" is in either role

Print the file paths and a one-paragraph summary. The user wires it manually.

## Step 6 — Single-agent fallback

If the same agent plays both roles, the dual-AI discipline collapses to a
single-agent self-audit pass. Tell the user this explicitly and ask if they
want to proceed. If yes, scaffold only the in-repo 5-lens doc; skip the
out-of-repo gate/protocol.

## Step 7 — Update project-level CLAUDE.md or AGENTS.md

If the project has a `CLAUDE.md` or `AGENTS.md` at root, ask before editing. If
approved, add a "HARD GATE — <PROJECT_NAME> Cross-Agent Audit Protocol"
section pointing at the gate and protocol files.

## Step 8 — Summary

Print to the user:

```text
Audit-handoff infrastructure scaffolded for <PROJECT_NAME>:

Out-of-repo:
- <AUDIT_GATE_PATH>
- <AUDIT_PROTOCOL_PATH>

In-repo (PR opened):
- <PROJECT_REPO_PATH>/docs/process/5-lens-self-audit.md
  (branch: process/shared-audit-knowledge, PR #<n>)

Per-agent wiring:
- <IMPLEMENTER_AGENT> implementer: <path / "none — Other agent">
- <AUDITOR_AGENT> auditor: <path / "none — Other agent">

Next steps:
1. Review the PR and merge.
2. Verify each agent reads its pointer on next session.
3. As audits surface drift patterns, add them to section 22 of the protocol
   AND to the in-repo 5-lens doc.
```

## What this does NOT do

- It does not configure agent-specific runtime behavior beyond pointer files.
- It does not enforce the discipline — that's on the human director and the
  agents following the docs they're pointed at.
- It does not produce project-specific drift patterns. Those accumulate over
  time.
