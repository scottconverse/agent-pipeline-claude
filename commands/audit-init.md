---
description: Scaffold dual-AI audit-handoff infrastructure for a project — out-of-repo audit gate + protocol and in-repo 5-lens self-audit. For projects where one AI implements and a different AI audits.
argument-hint: (none — interactive)
---

# /audit-init — scaffold dual-AI audit infrastructure

You are setting up the audit-handoff discipline for a project that uses two AI systems: one implements, the other audits. This complements `/pipeline-init`'s execution-side discipline (research → plan → execute → verify) with a verification-side discipline that catches drift the implementing agent misses.

The user should already have run `/pipeline-init` first if they want both. `/audit-init` can be run standalone if the project doesn't use the full pipeline — the audit discipline is independent.

## What this creates

Three artifacts plus optional per-agent wiring:

1. **`<PROJECT>_AUDIT_GATE.md`** at the desktop level (out-of-repo). Short mandatory gate the auditing agent reads every verification turn.
2. **`<PROJECT>_AUDIT_PROTOCOL.md`** at the desktop level (out-of-repo). Long reference protocol. Contains the 10-section output shape, status-word rules, known drift patterns catalog.
3. **`<project-repo>/docs/process/5-lens-self-audit.md`** in-repo. Shared by both agents. Contains the hostile self-audit the implementer runs before push.

Optional wiring:
- For Claude in either role: a Claude memory feedback file pointing at the right artifact.
- For another AI in either role: the equivalent project-context or skill-registration file for that runtime (varies by runtime — point the operator at where that AI reads its standing instructions).
- Optional update to project-level `CLAUDE.md` or runtime-equivalent project-context file declaring the discipline.

## Step 1 — Gather inputs

Use `AskUserQuestion` to collect:

- **Question:** `What is the project name? (capitalized, e.g. CivicSuite, CivicCast)`
- **Question:** `Which AI system implements code in this project?` Options: `Claude`, `Other (name it)`.
- **Question:** `Which AI system audits in this project?` Options: `Claude`, `Other (name it)`. (If same as implementer, this is a single-agent project — see Step 6.)
- **Question:** `What is the local path to the project repo?` (Use the current directory if it looks like a repo, otherwise ask.)
- **Question:** `What is the desktop-level directory where the gate + protocol should live?` Default: parent of the project repo path.

Capture:
- `<PROJECT_NAME>` — the capitalized project name.
- `<PROJECT_NAME_UPPER>` — uppercase for file names.
- `<IMPLEMENTER_AGENT>` — `Claude` or the operator's named other AI.
- `<AUDITOR_AGENT>` — `Claude` or the operator's named other AI.
- `<PROJECT_REPO_PATH>` — local path.
- `<DESKTOP_PATH>` — out-of-repo path.
- `<AUDIT_GATE_PATH>` — `<DESKTOP_PATH>/<PROJECT_NAME_UPPER>_AUDIT_GATE.md`.
- `<AUDIT_PROTOCOL_PATH>` — `<DESKTOP_PATH>/<PROJECT_NAME_UPPER>_AUDIT_PROTOCOL.md`.

## Step 2 — Sanity check

Before writing anything:
- Check if either of `<AUDIT_GATE_PATH>` or `<AUDIT_PROTOCOL_PATH>` already exists. If yes, ask `AskUserQuestion`: `Existing audit infrastructure detected. Overwrite, augment, or abort?`
- Check if `<PROJECT_REPO_PATH>/docs/process/5-lens-self-audit.md` exists. Same question.
- Confirm the project repo path is a real git repo (`git -C <path> rev-parse`).

## Step 3 — Scaffold the three artifacts

Read the three template files from the plugin:
- `pipelines/templates/audit-gate-template.md`
- `pipelines/templates/audit-protocol-template.md`
- `pipelines/templates/5-lens-self-audit-template.md`

For each, perform placeholder substitution:
- `<PROJECT_NAME>` → captured value
- `<IMPLEMENTER_AGENT>` → captured value
- `<AUDITOR_AGENT>` → captured value
- `<AUDIT_GATE_PATH>` → captured path
- `<AUDIT_PROTOCOL_PATH>` → captured path
- `<PROJECT_REPO_PATH>` → captured path

Write the substituted content:
- Gate → `<AUDIT_GATE_PATH>`
- Protocol → `<AUDIT_PROTOCOL_PATH>`
- 5-lens doc → `<PROJECT_REPO_PATH>/docs/process/5-lens-self-audit.md` (create the `docs/process/` directory if needed)

## Step 4 — Open a PR for the in-repo doc

The in-repo `docs/process/5-lens-self-audit.md` lands via PR, not direct push to main. Open a branch `process/shared-audit-knowledge`, commit the new doc with a message describing the dual-AI setup, push, and open a PR. Don't merge automatically — let the user review and merge.

Commit message template:

```
docs(process): add shared 5-lens self-audit rule for <PROJECT_NAME>

Adds docs/process/5-lens-self-audit.md as the in-repo shared rule both
<IMPLEMENTER_AGENT> (implementer) and <AUDITOR_AGENT> (auditor) read.

Pairs with:
- <AUDIT_GATE_PATH> (out-of-repo, short mandatory gate)
- <AUDIT_PROTOCOL_PATH> (out-of-repo, long reference)

Scaffolded by /audit-init from scottconverse/agent-pipeline-claude v0.3+.
This is process documentation only. No feature work, no code change,
no tag/release impact.
```

## Step 5 — Per-agent wiring

Based on the role assignment, write the per-agent pointers:

### If Claude is the auditor
Create a memory feedback file at `~/.claude/projects/<encoded-cwd>/memory/feedback_<project>_audit_protocol.md` with:

```markdown
---
name: <PROJECT_NAME> audit protocol — Claude is auditor
description: When auditing <PROJECT_NAME> work from <IMPLEMENTER_AGENT>, read the gate first.
type: feedback
---
For any <PROJECT_NAME> audit, audit-fix, release-gate, or report verification:

1. Read `<AUDIT_GATE_PATH>` completely every turn.
2. Read `<AUDIT_PROTOCOL_PATH>` for full reference.
3. Read `<PROJECT_REPO_PATH>/docs/process/5-lens-self-audit.md` for the shared implementer-side rule.

**Why:** This project uses dual-AI audit-handoff discipline. The gate and protocol
are out-of-repo so they apply to verification turns specifically. The in-repo doc
is the shared rule.

**How to apply:** Every <PROJECT_NAME> verification turn produces the mandatory
10-section output defined in the gate. Section 9 (paste-ready directive) is never
skipped.
```

Append a pointer line to `~/.claude/projects/<encoded-cwd>/memory/MEMORY.md` under the appropriate section.

### If Claude is the implementer
Create a memory feedback file at `~/.claude/projects/<encoded-cwd>/memory/feedback_<project>_5_lens_self_audit.md` with:

```markdown
---
name: <PROJECT_NAME> 5-lens self-audit — Claude is implementer
description: Before every <PROJECT_NAME> push, run the in-repo 5-lens self-audit.
type: feedback
---
**HARD RULE.** Before any `git push` on <PROJECT_NAME> work, run a hostile 5-lens
self-audit on the actual diff. Include the audit result in the push report.

Reference: `<PROJECT_REPO_PATH>/docs/process/5-lens-self-audit.md`

**Why:** Catches drift before it lands. The auditing agent (<AUDITOR_AGENT>) finds
real drift on every cycle when this rule isn't followed.

**How to apply:** Five lenses (Engineering / UX / Tests / Docs / QA) on the diff,
plus the artifact-state checklist, plus the post-push SHA-propagation step.
```

### If a non-Claude AI is in either role
Print the relevant file paths and a one-paragraph summary of what that agent needs to read every turn. The user wires it into the other AI's standing-instructions surface manually (skill file, project-context file, system prompt, custom GPT instructions — whatever the runtime exposes). Pattern to convey:

```markdown
## <PROJECT_NAME> audit-handoff discipline

When working on <PROJECT_NAME> as the <role>:
- Read `<AUDIT_GATE_PATH>` (auditor) or `<PROJECT_REPO_PATH>/docs/process/5-lens-self-audit.md` (implementer) every turn.
- Reference: `<AUDIT_PROTOCOL_PATH>` for full audit protocol.
- The mandatory 10-section verification output and the 5-lens self-audit are non-negotiable.
```

## Step 6 — Single-agent fallback

If the same agent plays both roles, the dual-AI discipline collapses to a single-agent self-audit-and-verify pass. Still useful, but the structural benefit is reduced. Tell the user this explicitly and ask if they want to proceed anyway. If yes, scaffold the in-repo 5-lens doc only (skip the out-of-repo gate/protocol since there's no separate verifier needing them).

## Step 7 — Update project-level CLAUDE.md or AGENTS.md

If the project has a `CLAUDE.md` or `AGENTS.md`, ask before editing. If approved, add a "HARD GATE — <PROJECT_NAME> Cross-Agent Audit Protocol" section pointing at the gate and protocol. Pattern:

```markdown
## HARD GATE - <PROJECT_NAME> Cross-Agent Audit Protocol

For any <PROJECT_NAME> audit, audit-fix, release-gate, <IMPLEMENTER_AGENT>/<AUDITOR_AGENT>
report verification, status-check, merge/tag-readiness decision, or directive-writing
task, read this short gate first and follow it:

`<AUDIT_GATE_PATH>`

Long reference protocol:

`<AUDIT_PROTOCOL_PATH>`
```

## Step 8 — Summary

Print a summary to the user:

```text
Audit-handoff infrastructure scaffolded for <PROJECT_NAME>:

Out-of-repo:
- <AUDIT_GATE_PATH>
- <AUDIT_PROTOCOL_PATH>

In-repo (PR opened):
- <PROJECT_REPO_PATH>/docs/process/5-lens-self-audit.md (branch: process/shared-audit-knowledge, PR #<n>)

Per-agent wiring:
- <IMPLEMENTER_AGENT> implementer: <path to memory file / skill addition / "none — Other agent">
- <AUDITOR_AGENT> auditor: <path to memory file / skill addition / "none — Other agent">

Next steps:
1. Review the PR and merge to land the in-repo doc.
2. Verify each agent reads its pointer on next session.
3. As audits surface drift patterns, add them to section 22 of the protocol AND as
   artifact-state checklist items in the in-repo 5-lens doc.
```

## What this command does NOT do

- It does not configure agent-specific runtime behavior beyond the pointer files. Each agent's existing behavior (skills, memory, system prompts) still governs everything else.
- It does not enforce the discipline. The discipline is enforced by the agents reading the docs they're pointed at and the human director rejecting outputs that don't meet the protocol.
- It does not produce project-specific drift patterns. Those accumulate over time as audits surface them. The protocol template has an empty section 22 you fill in.
