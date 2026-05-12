# v1.0 UX Redesign — Audit Receipts

**Date:** 2026-05-11
**Lead:** Senior UI/UX Designer (via the `anthropic-skills:coder-ui-qa-test` skill).
**Supporting:** Principal Engineer, Senior QA Engineer (cross-reads in the same audit).
**Subject:** `agent-pipeline-claude` v0.5.2 → v1.0.0.

This document captures the audit that drove the v1.0 rewrite. It exists in the repo so future contributors understand *why* v1.0's surface is what it is. The audit was conducted during a live session where a CivicCast operator was attempting to use the plugin and surfaced concrete UX failures.

---

## The triggering session

Scott (the project director) attempted to install and use the v0.5.2 plugin during a CivicCast development session in his Cowork environment.

**Friction 1 — install path.** README said: `/plugin install scottconverse/agent-pipeline-claude`. Scott typed `/plugin marketplace add scottconverse/agent-pipeline-claude` and got `/plugin isn't available in this environment.` The v0.5.2 plugin had no documented Cowork install path.

**Friction 2 — restart-required not surfaced.** After a file-level install completed cleanly (commit `79db3a7` cloned into `~/.claude/plugins/marketplaces/`, plus three JSON config patches), the slash commands `/pipeline-init`, `/run`, etc. did not appear in the current Cowork session. The product copy gave no signal that a restart was required.

**Friction 3 — manifest ceremony.** Scott asked what a "manifest skeleton" was. The answer turned out to be 60 lines of YAML he was expected to fill in. He said: *"this is what the USER puts in?"* with audible disbelief, given that CivicCast already has:

- `CivicCastUnifiedSpec-v2.md`
- `CivicCast-ReleasePlan-0.1-to-1.0.md`
- `docs/releases/v0.4-scope-lock.md`
- `docs/research/v04-slice1-broadcast-spine-design.md`
- `CLAUDE.md`
- audit-team findings ledgers
- HANDOFF.md

The manifest was asking him to re-derive content that already lived in those documents.

**Friction 4 — meta-failure.** When asked to redesign the plugin, the agent produced a four-page response with phase plans and decision matrices for Scott to approve. Scott replied: *"sigh. more fucked up results. STOP giving me choices and FUCKING WRITE IT."*

---

## Audit findings (severity-ranked)

13 findings surfaced. Two BLOCKER, three CRITICAL, five MAJOR, three MINOR.

| # | Severity | Finding |
|:--|:---------|:--------|
| F-01 | BLOCKER | Install instructions assume CLI; Cowork users hit a dead end. |
| F-02 | BLOCKER | "Evoke for this session" is structurally impossible; product copy doesn't acknowledge it. |
| F-03 | CRITICAL | The manifest fill-in treats every project as if it had no spec. |
| F-04 | CRITICAL | The two-step `/new-run` + `/run-pipeline` is friction for no benefit. |
| F-05 | CRITICAL | "Manifest skeleton" is the wrong noun (carries Docker/k8s connotations that mislead users). |
| F-06 | MAJOR | README is stage-list heavy, journey-light. |
| F-07 | MAJOR | `AskUserQuestion` round-trip in Cowork is heavy for routine gates. |
| F-08 | MAJOR | Predecessor naming bleed-through (old `agentic-pipeline` install conflicts with new `agent-pipeline-claude`). |
| F-09 | MAJOR | "Pipeline run" run-id encoding (`YYYY-MM-DD-<slug>`) is undocumented. |
| F-10 | MAJOR | Pipeline failure modes are opaque (raw Python tracebacks in chat). |
| F-11 | MINOR | `CLAUDE.md` scaffolding overwrites blind. |
| F-12 | MINOR | Glossary is undermaintained. |
| F-13 | MINOR | No example `.agent-runs/` in the repo. |

The full audit text (with severity definitions, evidence citations, and remediation per finding) lives in the [original session transcript on the v0.5.2 → v1.0 redesign turn](https://github.com/scottconverse/agent-pipeline-claude/commits/v1) — the audit is preserved here as a summary; the receipts are in the commit messages and CHANGELOG.

---

## The four load-bearing v1.0 decisions

The audit findings cluster around four decisions the redesign had to make. v1.0 made all four:

### 1. Cowork-first, not CLI-first

Every install path documented for Cowork users first. The CLI path remains supported via a one-line convenience note. The Cowork bootstrap prompt (paste into any Claude session) is the primary documented install method.

**Addresses:** F-01, F-02 (BLOCKER), F-08 (MAJOR).

### 2. Spec-aware drafting, not spec-blind authoring

The plugin reads the project's existing artifacts (spec, release plan, scope-lock, design notes, ADRs, ledgers, `CLAUDE.md`) and drafts the manifest. The user reviews a filled YAML in chat and replies `APPROVE`. The user does not hand-author from blank.

Implementation: new `manifest-drafter` role file + new `/run` orchestrator that invokes it as a pre-stage.

**Addresses:** F-03, F-05 (CRITICAL), F-04 (CRITICAL collapse: the manifest no longer needs the operator's authoring time).

### 3. One slash command, not three

`/run "<short description>"` replaces `/new-run` + `/run-pipeline`. The drafter invocation, manifest write, chat-message review, and orchestrator hand-off all happen inside a single user-facing command.

`/run resume <run-id>` handles resumption; `/run status` handles listing.

**Addresses:** F-04 (CRITICAL), F-09 (MAJOR — run-id encoding becomes an internal detail).

### 4. Chat-native gates, not modal popups

The three human gates (manifest / plan / manager) prompt via chat messages with the universal verbs `APPROVE`, `REPLAN <description>`, `BLOCK` (manager only). `AskUserQuestion` is reserved for mid-stage disambiguating questions where modal interaction adds value (rare).

**Addresses:** F-07 (MAJOR).

---

## What v1.0 preserved unchanged

The audit was explicit: the v0.5 hardening mechanism is sound; only the surface around it is broken. v1.0 preserves intact:

- Critic stage (v0.5 — adversarial cold read).
- Drift-detector stage (v0.5 — manifest contract vs assembled state).
- Pre-edit fact-forcing in executor (v0.5).
- Judge layer (v0.4 — opt-in via file presence).
- Machine-checkable auto-promote (v0.5 — six conditions).
- Strict manifest schema validation (v0.5 — only the error-message *shape* changed; the rules are unchanged).
- The 13 role files (`researcher`, `planner`, `test-writer`, `executor`, `verifier`, `drift-detector`, `critic`, `manager`, `judge`, `preflight-auditor`, `local-rehearsal`, `cross-agent-auditor`, `implementer-pre-push`).
- The six policy scripts.
- The three pipeline definitions (`feature`, `bugfix`, `module-release`).
- The `.agent-runs/<run-id>/` artifact stack.
- The v0.3 audit-handoff scaffold (`/audit-init`).

The 14th role file added in v1.0 is `manifest-drafter`. The seventh policy artifact added is the `draft-provenance.md` audit trail.

---

## What v1.0 deprecates

`/new-run` and `/run-pipeline` survive as deprecated shims through v1.0. Each prints a one-paragraph deprecation notice on invocation, offers to delegate to `/run`, and only falls through to legacy v0.5.2 behavior if the user explicitly replies `LEGACY`.

**Removal date:** v1.1. Soft cutover = one minor release of muscle-memory accommodation.

---

## Cross-reads from the supporting roles

### Principal Engineer

> Implementable in the plugin's architecture. Three structural notes:
>
> 1. Drafter is a new agent role at `pipelines/roles/manifest-drafter.md`. The `/run` orchestrator spawns it as a pre-stage; its output (`manifest.yaml`) is the input to the manifest gate the existing pipeline definitions already have.
> 2. `/run` is a new entry point at `commands/run.md`. Replaces `/new-run` + `/run-pipeline`. The deprecated commands become thin shims.
> 3. Hot-loading slash commands isn't feasible in current Cowork. The "restart required" reality is structural; the install bootstrap must surface it clearly.
>
> Schema-level changes: none. The drafter writes the same `manifest.yaml` shape the existing schema validator already enforces.
>
> Test surface: schema-validator tests (added in v1.0), plus the new manifest-drafter integration fixtures (added in v1.0 under `tests/fixtures/`). A fully-automated drafter integration test that spawns a real Claude session is out of scope for v1.0.
>
> Estimated effort: 2-4 focused days. The actual v1.0 shipped in one session.

### Senior QA Engineer

> Regression surface:
>
> 1. Old `/new-run` + `/run-pipeline` muscle-memory users must still get a working run. Mitigation: deprecated shims with LEGACY fall-through. Tests: not added in v1.0 (the shims are markdown role files, not Python — they're spec-tested via manual exercise).
> 2. Drafter against unfamiliar project shapes (spec.md / SPEC.md / spec in README / no spec). Mitigation: the manifest-drafter role file documents the source-walking protocol with fall-throughs at each step.
> 3. Greenfield fallback (paste a description, drafter synthesizes a spec). Mitigation: explicit State-2 prompt in the orchestrator; greenfield fixture at `tests/fixtures/greenfield/` documents the expected behavior.
> 4. Manifest drift between draft and final (user edits the YAML after the drafter writes it). Mitigation: orchestrator re-reads the YAML at run-start, doesn't cache the draft.
> 5. Install conflict with old `agentic-pipeline` plugin. Mitigation: install bootstrap prompt explicitly disables the old plugin if present.
>
> Blind spots: drafter quality is uneven across projects (sloppy artifacts produce sloppy drafts). v1.0 surfaces this honestly in copy ("the more structured your docs, the better this works") and provides the `## Pipeline drafter notes` CLAUDE.md section as an explicit override path.

---

## What ships in v1.0

Two structured commits on the `v1` branch:

- **`e099c92`** — Phase 1: `commands/run.md` (single entry-point orchestrator with 5-state manifest-review screen + chat-native gate prompts), `pipelines/roles/manifest-drafter.md` (spec-walking drafter). Plugin manifests bumped to 1.0.0.

- **`1bf5ed1`** — Phase 2: deprecated shims for `/new-run` + `/run-pipeline`, Cowork-first rewrite of `/pipeline-init`, README + USER-MANUAL + CHANGELOG rewritten around the new surface, `check_manifest_schema.py` errors now surface with field/problem/current/suggestion/footer remediation pointers.

Plus a Phase 3 (this commit and the one that follows): ARCHITECTURE.md updated, landing page updated, `CONTRIBUTING.md` written, `tests/test_check_manifest_schema.py` added with 11 tests, fixture projects at `tests/fixtures/civiccast-shaped/` + `tests/fixtures/greenfield/`, this audit doc, version-sync verification.

The v1 branch lives at https://github.com/scottconverse/agent-pipeline-claude/tree/v1. The v1.0.0 tag is cut from `1bf5ed1` (or the latest Phase 3 SHA, whichever is HEAD at tag time).

---

## Why this is captured in the repo

Future contributors will ask: *"why is `/run` one command? why doesn't the user fill in the manifest? why does the README lead with a Cowork bootstrap prompt instead of `/plugin install`?"*

This doc is the answer. The audit was driven by real friction. The decisions were made to address that friction. Reverting the decisions reintroduces the friction.

If a future change wants to revisit any of the four load-bearing decisions, the contributor should open a discussion at https://github.com/scottconverse/agent-pipeline-claude/discussions with evidence that the new design addresses the same friction in a better way.
