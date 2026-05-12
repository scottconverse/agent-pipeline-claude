# Changelog

All notable changes to `agent-pipeline-claude` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project follows [Semantic Versioning](https://semver.org/).

## [1.0.2] — 2026-05-11

**Critical manifest fix — v1.0.0 and v1.0.1 never actually loaded.**

`claude plugin list` reveals the real story: in v1.0.0 and v1.0.1, the plugin manifest at `.claude-plugin/plugin.json` had `repository` as an npm-style object (`{"type": "git", "url": "..."}`), but Claude Code's plugin schema requires a plain string. The loader **rejected the entire manifest**:

```
Status: ✘ failed to load
Validation errors: repository: Invalid input: expected string, received object
```

A failed manifest means the plugin's commands AND skills never register. That's why `/run` did nothing in Cowork for two releases — not because of `commands/` vs `skills/` layout, not because of YAML parse errors (those existed too, but were secondary). The primary bug was that the entire plugin failed to load at the manifest stage.

Also surfaced: latent YAML parse error in `commands/run.md` and `skills/run/SKILL.md` `argument-hint` line (closing quote followed by unquoted text — invalid YAML). Inherited from v0.5.2 in commands/, copied forward into skills/ during v1.0.1. Would have broken /run specifically even after the manifest loaded.

### Fixed

- **`.claude-plugin/plugin.json` `repository` field** — changed from npm-style `{type, url}` object to plain string per Claude Code plugin schema. This single change unblocks the entire plugin.
- **`commands/run.md` frontmatter** — `argument-hint` rewritten as single-quoted YAML scalar so it parses cleanly.
- **`skills/run/SKILL.md` frontmatter** — same fix.

### Added

- **`tests/check_plugin_structure.py`** — comprehensive validator that runs every commit-worthy plugin artifact through real YAML/JSON parsers and checks required fields. Catches both bug classes from v1.0.0–v1.0.1 in one pass. Use before any push that touches manifests, commands, skills, or roles.

### Verification

`claude plugin list` after the v1.0.2 patch shows `Status: ✔ enabled`. (Same load succeeds in Cowork — Cowork uses the same plugin loader.)

### Action required for v1.0.0 / v1.0.1 users

After upgrading the install to v1.0.2, **fully quit Cowork and restart** (not just open a new conversation — the plugin metadata is read at app startup). Then `/run status` should be recognized.

## [1.0.1] — 2026-05-11

Critical Cowork compatibility fix. v1.0.0 shipped the primary `/run` entry point as a plugin command under `commands/run.md`, but Cowork only loads plugin-provided user commands from the `skills/<name>/SKILL.md` layout. Net result on v1.0.0: every Cowork user typing `/run` saw *"/run isn't a recognized command here. Some commands only work in the Claude Code terminal."* — making the plugin's primary UX unreachable for the audience it was specifically rewritten for.

Surfaced the first time `/run` was exercised in a live Cowork session (CivicCast Slice 1 Commit 8 test-drive, 2026-05-11). Fix is purely additive — same content, correct loader-visible layout.

### Fixed

- **`/run`, `/pipeline-init`, `/new-run`, `/run-pipeline`, `/audit-init` now load in Cowork.** Each command is mirrored as `skills/<name>/SKILL.md` (identical body content, frontmatter gains a `name:` field). The legacy `commands/*.md` files are kept for any CLI consumer that still scans them, but the `skills/` layout is the authoritative path going forward — it's the layout the Anthropic claude-plugins-official examples use and the one Cowork's plugin loader discovers.
- **Documented Cowork command-loading reality.** The v1.0.0 README and `pipeline-init.md` Step 4 claimed slash commands "register at session start" without distinguishing the `commands/` vs `skills/` layouts. This patch supersedes that claim mechanically by shipping the correct layout; a documentation pass to update the prose is queued for v1.0.2.

### Preserved unchanged

- All v1.0.0 content, role files, policy scripts, schema validator, drafter logic, orchestration rules, gate semantics, and pipeline definitions. The patch only changes file layout, not behavior.

### Action required for v1.0.0 users

After upgrading the plugin install to v1.0.1, restart your Cowork session so the newly-discoverable `skills/` directory is picked up. Then type `/run status` to confirm registration.

## [1.0.0] — 2026-05-11

UX rewrite. The v0.5 hardening mechanism (critic + drift-detector + judge layer + auto-promote + strict schema) is preserved unchanged; everything around it that touches a user is rebuilt around four load-bearing decisions: Cowork-first, spec-aware drafting, one command, chat-native gates.

Built from a real audit run during this very session — a CivicCast operator hit "/plugin isn't available" at the install step, then "really really bad UX" at the manifest fill-in step, then asked to rewrite the plugin. v1.0 is that rewrite.

### Added

- **`/run` slash command** (`commands/run.md`). Single entry point replacing v0.5.2's two-step `/new-run` + `/run-pipeline`. Argument shapes: `/run "<description>"` to start, `/run resume <run-id>` to pick up, `/run status` to list. Drafts a manifest from your project's spec, presents it in chat, loops on revision, then orchestrates the pipeline end-to-end.
- **Manifest drafter role** (`pipelines/roles/manifest-drafter.md`). A new fresh-context subagent the `/run` orchestrator invokes before any stage. The drafter walks the project root for spec / release-plan / scope-lock / design-note / ADR / ledger artifacts, then auto-derives 9 of 11 manifest fields from those sources. Writes `manifest.yaml` + `draft-provenance.md` (per-field source attribution). Returns a one-line summary string for the orchestrator's chat prompt.
- **Spec source-walking protocol** documented in `manifest-drafter.md`. Recognizes `*UnifiedSpec*.md`, `SPEC.md`, `PRD.md`, `*ReleasePlan*.md`, `ROADMAP.md`, `docs/releases/v*-scope-lock.md`, `docs/research/<version>-design.md`, `docs/adr/*.md`, `CLAUDE.md`, `audit-*/`. Operators can also override discovery via a `## Pipeline drafter notes` section in `CLAUDE.md`.
- **Cowork-first install instructions** in `README.md` and `USER-MANUAL.md`. A paste-able bootstrap prompt the user drops into any Claude session — Cowork or CLI — that does the file-level install (clone + JSON patches). The CLI-only `/plugin install scottconverse/agent-pipeline-claude` becomes a convenience note for users whose build has the command available.
- **Explicit restart-required signal post-install.** Every install path ends with the user being told to restart their session before the slash commands register. v0.5.2 didn't surface this; v1.0 makes it a first-class step.
- **Chat-native gate prompts** at the three human gates (manifest / plan / manager). Three universal verbs: `APPROVE`, `REPLAN <description>` (or freeform changes), `BLOCK` (manager gate only). Replaces v0.5.2's modal `AskUserQuestion` popups for the three gates. `AskUserQuestion` stays available for genuinely-disambiguating mid-stage questions.
- **Failure-message shape with remediation pointers.** Every error surface — `check_manifest_schema.py` failures, missing manifests, schema-rejected drafts, stage failures — follows a standard shape: *what failed / where / current value / suggestion / full-context pointer*. No raw Python tracebacks reach the user.
- **`commands/run.md` Step 6 five-state walkthrough.** The manifest-review screen has five explicit states (populated draft, greenfield, partial, schema-error, loading) so the orchestrator never surprises the user with an unfamiliar shape.

### Changed

- **`commands/pipeline-init.md` rewritten.** Now produces a one-message orientation summary first, asks for APPROVE, then scaffolds. The `CLAUDE.md` starter is shorter and explicitly includes a `## Pipeline drafter notes` section telling the drafter where this project keeps its spec / release plan / design notes / ledgers. The legacy "11-section template CLAUDE.md scaffold" is gone — projects fill in what they need.
- **`scripts/check_manifest_schema.py` error-message rewrite.** Each violation now surfaces with field name + problem + current value + concrete suggestion, plus a footer telling the operator which file to edit and which `/run resume` command to re-trigger validation. The schema *rules* are unchanged from v0.5.2; only the human-facing output shape changed.
- **Plugin manifests (`plugin.json` + `marketplace.json`) bumped to v1.0.0** with new short descriptions matching the redesign.
- **README.md fully rewritten.** Journey-first ("here's what a `/run` looks like") instead of stage-list-first. Cowork-first install. Concrete examples of a drafted manifest inline. Migration story for v0.5.x users.
- **USER-MANUAL.md updated** to match the new surface. Restart-required surfaced. Greenfield fallback path documented. Two universal verbs (`APPROVE` / `REPLAN`) introduced before any walkthrough.

### Deprecated

- **`/new-run` and `/run-pipeline`** survive as deprecated shims at v1.0.0. Each prints a one-paragraph deprecation notice on invocation, offers to delegate to `/run`, and only falls through to legacy v0.5.2 behavior if the user replies `LEGACY`. **These shims will be removed at v1.1.** v0.5.2 muscle-memory has one minor release of soft cutover.

### Preserved unchanged

- The manifest schema (`pipelines/manifest-template.yaml` + `check_manifest_schema.py` rule set).
- All 13 v0.5.2 role files (`researcher`, `planner`, `test-writer`, `executor`, `verifier`, `drift-detector`, `critic`, `manager`, `judge`, `preflight-auditor`, `local-rehearsal`, `cross-agent-auditor`, `implementer-pre-push`).
- The six policy scripts (`check_manifest_schema`, `check_allowed_paths`, `check_no_todos`, `check_adr_gate`, `auto_promote`, `run_all`).
- The three pipeline definitions (`feature.yaml`, `bugfix.yaml`, `module-release.yaml`).
- The `.agent-runs/<run-id>/` artifact stack (research.md, plan.md, verifier-report.md, etc.).
- The opt-in judge layer (file-presence activation via `.pipelines/action-classification.yaml`).
- The six-condition auto-promote check.
- The v0.3 audit-handoff scaffold (`/audit-init` + the three out-of-repo + in-repo audit artifacts).

### Migration from v0.5.x

1. `cd ~/.claude/plugins/marketplaces/agent-pipeline-claude && git pull && git checkout v1.0.0`.
2. Restart your Cowork or CLI session.
3. The `installed_plugins.json` entry should auto-update on next plugin scan. If it doesn't, manually update `gitCommitSha` to the v1.0.0 tag SHA.
4. Your existing `.pipelines/`, `scripts/policy/`, `CLAUDE.md`, and `.agent-runs/` are unchanged. v1.0 reads them as-is.
5. Your old `/new-run` + `/run-pipeline` muscle memory still works (with a deprecation notice) through v1.0. New runs should use `/run`.

### Compatibility caveats

- The shape of `manifest.yaml` is unchanged. Old manifests at `.agent-runs/<run-id>/manifest.yaml` from v0.5.x still validate against v1.0.
- The `.agent-runs/<run-id>/` artifact filenames are unchanged. Old runs can be resumed via `/run resume <run-id>`.
- The new manifest-drafter writes one additional artifact (`draft-provenance.md`) alongside the manifest. This is informational; no other stage reads it.

## [0.5.2] — 2026-05-11

Rename + scope-narrowing release. The plugin is now `agent-pipeline-claude` (was `agentic-pipeline`) and is published as a Claude Code plugin only. Codex Desktop App support has been removed from the upstream repo and will live in a separate downstream repo.

### Changed

- **Plugin rename.** `agentic-pipeline` → `agent-pipeline-claude` across all live files: `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, the four policy scripts' `--version` strings, README / USER-MANUAL / ARCHITECTURE / CHANGELOG bodies, `docs/index.html` (landing page), discussion seed posts, command and role-file references. Historical CHANGELOG entries (v0.1-beta through v0.5.1) describe the same plugin under its previous name for continuity.
- **Repo rename.** GitHub repo renamed `scottconverse/agentic-pipeline` → `scottconverse/agent-pipeline-claude`. GitHub redirects clone URLs and HTTP routes for the old name automatically; existing `/plugin install scottconverse/agentic-pipeline` references break only on plugin-marketplace tooling that doesn't follow HTTP redirects.
- **Codex Desktop App support removed.** The Codex parallel implementation (skill files, `.codex-plugin/plugin.json`, `pipelines/templates/AGENTS.md`, `docs/codex-desktop-adaptation.md`) is not part of this release. Will be re-published as a separate downstream repo. References to Codex in audit-handoff documentation have been genericized — the dual-AI audit pattern (v0.3) still works with any second AI, but the plugin no longer ships Codex-specific scaffolding.
- **`pipelines/roles/drift-detector.md` invariant 8a simplified.** The version-string-consistency invariant now describes a single plugin manifest (no Codex-side parallel). Clearer rules, no adapter-suffix edge cases.

### Why this release exists

The Codex Desktop App side and the Claude Code side had been entangled in one repo, with parallel plugin manifests, parallel orchestration logic, and a version-string invariant that had to handle both. The two sides have different runtime models, different distribution mechanisms, and different release cadences. Separating them removes the entanglement and lets each side ship on its own schedule.

`0.5.2` rather than `0.6.0` because the surface area of the plugin (commands, roles, policy scripts, pipeline definitions, run state) is unchanged. The change is purely identity (name) and scope (single-runtime).

### Migration

Existing installs:

```bash
# Update the plugin reference
/plugin uninstall agentic-pipeline
/plugin install scottconverse/agent-pipeline-claude
```

Projects already initialized with `/pipeline-init` continue to work — the scaffolded `.pipelines/`, `scripts/policy/`, and `.agent-runs/<run-id>/` files are unchanged. Re-running `/pipeline-init` to refresh the scaffolded scripts is recommended but not required.

The GitHub repo URL change propagates automatically via GitHub's redirect for git clone, but bookmarks to `https://github.com/scottconverse/agentic-pipeline` and `https://scottconverse.github.io/agentic-pipeline/` should be updated to use the new name.

---

## [0.5.1] — 2026-05-11

Patch release. Adds standing doc-currency invariants to the drift-detector role so cumulative drift cannot ship under a feature-scoped manifest.

### Why this release exists

v0.5's drift-detector was contracted against the manifest's `expected_outputs` only. That contract is sound for the run's own scope but lets cumulative drift accumulate across releases: a feature-scoped manifest legitimately ships its feature, the verifier passes, but the project's top-of-file content (counts, tables, diagrams, version strings, section orderings) goes stale because nothing in the manifest names the back-audit.

The v0.5 dogfood run (`.agent-runs/2026-05-11-version-flag/`) had this exact gap — the drift-detector caught the in-scope `--version` drift but did not flag months-stale top-of-file content in README, USER-MANUAL, and `docs/index.html`. The fix is structural: invariants every release silently makes get their own enforcement, independent of any manifest.

### Changed

- `pipelines/roles/drift-detector.md` — added §8 **Standing doc-currency invariants**. Five invariants checked on EVERY run regardless of manifest scope:
  - **8a Version-string consistency** (`blocker` on mismatch): every authoritative version string in the repo agrees — `plugin.json`, `marketplace.json` (top-level metadata AND each plugin entry), `pyproject.toml` if present, every `argparse action="version"` string under `scripts/`, the top `## [X.Y.Z]` in `CHANGELOG.md`, `<div class="badge">vX.Y.Z` in `docs/index.html`, `**Version:** X.Y.Z` in `USER-MANUAL.md`.
  - **8b File-inventory tables** (`non-blocker` on small drift, `blocker` on whole-release-missing): USER-MANUAL "What you get" counts match `ls` reality; README scaffold block lists every file actually in `pipelines/roles/` and `scripts/`.
  - **8c Pipeline-diagram parity** (`blocker` on docs releases): `docs/index.html` `.pipeline-diagram` stages match `pipelines/feature.yaml` stage list and order.
  - **8d Section-ordering sanity** (`non-blocker`): per-version sections in README and USER-MANUAL appear in monotonic order; a `## v0.5:` followed by a `## v0.4:` is a reliable back-audit signal.
  - **8e Stability-posture currency** (`non-blocker`): any explicit current-release version reference in `docs/index.html` matches the current release.
- Output checklist updated to require explicit PASS/FAIL on every standing invariant.
- Drift item numbering shifted: §8 was Drift items; now §9. The count line in §2 was already abstracted across all numbered drift sections, so this is a forward-compatible rename.
- `--version` flag bumped to `agent-pipeline-claude 0.5.1` on `scripts/auto_promote.py` and `scripts/check_manifest_schema.py`.

### Stacking with v0.2, v0.3, v0.4, v0.5

No new stages, no new role files, no new policy scripts. v0.5.1 extends the contract of the existing drift-detector role file. All v0.5 behavior is preserved; the only behavioral change is that more drift items will be flagged on future runs.

### Honest limit

The standing invariants are enforced by a role file the drift-detector subagent reads. A subagent could in principle disregard a hard rule. The structural backstop is `auto_promote.py`'s read of the drift count line — if the drift-detector reports blocker drift, auto-promote refuses to fire, and the manager human-approval gate runs. The invariants harden the role contract but do not replace the auto-promote gate.

---

## [0.5.0] — 2026-05-11

The single-AI hardened release. Six structural changes that compensate for dropping dual-AI cross-family verification: two new agent roles (critic, drift-detector), pre-edit fact-forcing in the executor, expanded judge classification, machine-checkable auto-promote, and strict manifest schema validation. Built from the design question "can the pipeline do both action-level judge AND post-hoc audit with one AI?" Answer: yes, with the structural defense in this release.

The release is a structural substitute for the dual-AI audit-handoff discipline (v0.3) when running with a single AI. Existing dual-AI projects keep working; nothing in this release removes capability. The shipped honest limit: same-model-family verification cannot fully replace cross-family verification. The CHANGELOG entry below names the residual risk and the recommended mitigation.

### Added

- `pipelines/roles/critic.md` — adversarial critic role file. Fires after the verifier in a fresh context. Reads every artifact cold and produces a structured findings report with a parseable §2 count line (`**Findings: T total, B blocker, C critical, M major, N minor**`). Walks six adversarial lenses: engineering, UX, tests, docs, QA, scope. Hard rules forbid encouragement, severity softening, "no findings" without per-lens evidence, and trusting the verifier or executor at face value. Structural substitute for cross-family verification in single-AI runs.
- `pipelines/roles/drift-detector.md` — drift-detector role file. Fires after the verifier (before the critic). Compares manifest fields against the final assembled state. Catches the gap class neither the judge (per-action) nor the verifier (per-criterion) can see — durable doc drift, cross-file consistency, status-word abuse, ledger top-totals vs row counts, "Closed" without evidence. Emits parseable §2 count line (`**Drift: T total, B blocker**`).
- `scripts/check_manifest_schema.py` — manifest schema validator. Wired into both run-pipeline.md Phase A2 (run-start, before any stage fires) and `scripts/run_all.py` CHECKS (policy stage, defense in depth). Rules: `goal` >= 30 chars, `definition_of_done` >= 80 chars, `expected_outputs` non-empty, `non_goals` non-empty, `rollback_plan` non-empty, broad `allowed_paths` requires non-empty `forbidden_paths`, forbidden status words (`done`, `complete`, `ready`, `shippable`, `taggable`) banned from goal/dod. The fuzzy-manifest class of failure now blocks at the gate before it cascades into downstream work.
- `scripts/auto_promote.py` — machine-checkable promote decision. Reads verifier-report.md, critic-report.md, drift-report.md, policy-report.md, judge-metrics.yaml (when present), and implementation-report.md. Evaluates six conditions: verifier-clean (zero NOT MET, zero PARTIAL), critic-clean (zero blocker, zero critical), drift-clean (zero blocker), policy-passed, judge-clean (zero judged_block, zero human_blocked, vacuous when judge inactive), tests-passed. When all six pass, writes a preset `manager-decision.md` with `**Decision: PROMOTE**` and a citation block; otherwise writes `auto-promote-report.md` naming the failing conditions and exits 1.
- `--version` flag on `scripts/auto_promote.py` and `scripts/check_manifest_schema.py`. Operators run either script with `--version` to print `agent-pipeline-claude 0.5.0` and confirm which release is installed. The flag uses argparse's built-in `action="version"`, so it fires before required-arg validation — `auto_promote.py --version` works without supplying `--run`. Output is `agent-pipeline-claude 0.5.0` on stdout, exit code 0. Added as the deliverable of the v0.5 self-dogfood pipeline run (`.agent-runs/2026-05-11-version-flag/`, gitignored), which exercised every new v0.5 stage end-to-end and validated the auto-promote short-circuit.

### Changed

- `pipelines/roles/executor.md` — added a "Pre-edit fact-forcing gate" section. Before the first edit/write to any file in the run, the executor must produce a fact block (importers/callers, public API affected, data schema touched, manifest goal quoted verbatim) either inline in `implementation-report.md` or in `.agent-runs/<run-id>/notes/pre-edit-<filename>.md`. The drift-detector and critic stages check for the block and treat its absence as a finding on any touched file.
- `pipelines/roles/verifier.md` — added §0 "Criteria count line" requirement. The verifier must emit `**Criteria: T total, M MET, P PARTIAL, N NOT MET, A NOT APPLICABLE**` as a parseable line so `auto_promote.py` can read the verdict count without scanning the full report.
- `pipelines/roles/manager.md` — added "Auto-promote awareness (v0.5)" section. When `manager-decision.md` already exists with `**Decision: PROMOTE**` as the first line (auto-promote preset), the manager runs in validate-and-append mode instead of re-deciding. Inputs list extended with drift-report.md, critic-report.md, auto-promote-report.md, and judge-log.yaml/judge-metrics.yaml when present. PROMOTE criteria extended: critic blocker/critical = 0, drift blocker = 0, judge judged_block + human_blocked = 0.
- `pipelines/action-classification.yaml` — five new patterns under `high_risk`: `npm install --global` and `npm install -g`, `sudo`, `pip install` (non-editable, non-user), `git commit` with BREAKING in the message. Each tightens action-time defense against the failure modes operators most commonly cite.
- `pipelines/feature.yaml` — three new stages between `verify` and `manager`: `drift-detect`, `critique`, `auto-promote`. Manager stage gets `auto_promote_aware: true` flag.
- `pipelines/bugfix.yaml` — same three new stages and the manager flag.
- `pipelines/module-release.yaml` — three new phases between `phase4-verify` and `phase5-manager`: `phase4b-drift-detect`, `phase4c-critique`, `phase4d-auto-promote`. `phase5-manager` gets `auto_promote_aware: true`.
- `commands/run-pipeline.md` — Phase A2 now invokes `check_manifest_schema.py` before any stage runs. Handler 2 (`role: pipeline`) handles `optional_artifact: true` for the auto-promote stage. New **Handler 4** for `role: manager` with `auto_promote_aware: true`: checks for the preset, short-circuits the human gate when present, falls through to standard Handler 3 + Handler 1 when absent.
- `scripts/run_all.py` — `check_manifest_schema` added to `CHECKS` list. Runs first so a fuzzy manifest fails the policy stage even if it slipped past Phase A2.

### Why each piece exists

- **Critic stage.** v0.4's judge catches per-action scope violations in real time, but doesn't read the assembled output. The verifier reads the assembled output, but in the same model family as the executor — correlated blind spots are exactly the class of failure neither catches. The critic runs in a fresh context with a deliberately adversarial role contract.
- **Drift-detector stage.** Drift between manifest contract and durable artifacts is invisible to per-action and per-criterion verification. It only surfaces when you compare the manifest's promises to the assembled final state.
- **Pre-edit fact-forcing in executor.** Asking an LLM "are you sure?" is useless. Demanding concrete artifacts (importer list, schema, instruction quote) forces investigation that catches blast-radius surprises before they hit the verifier.
- **Expanded judge classification.** Global npm installs leak project-level promises into system-level state; sudo escalations sidestep manifest scope; non-editable pip installs in shared environments produce non-reversible side effects; BREAKING-marked commits are semver-major signals deserving explicit confirmation.
- **Machine-checkable auto-promote.** The manager gate becomes auto-firing when all six structural conditions hold. Humans get the time back without losing the gate — when any condition fails, the human gate is still there.
- **Strict manifest schema validation.** Every drift cascade investigated in prior projects traced back to a fuzzy manifest. The schema check makes the fuzzy state fail-fast.

### Stacking with v0.2, v0.3, v0.4

- v0.2 module-release pipeline: catches execution-cascade failures (pre-existing CI bugs, tag-move dances, halt-and-ask loops). Pre-executor.
- v0.3 dual-AI audit-handoff: catches drift failures via cross-family separation of duties. Post-executor, separate session.
- v0.4 judge layer: catches unauthorized actions in real time. During executor.
- **v0.5 hardened single-AI**: catches the drift class without needing a second AI, at the cost of accepting some correlated blind spots. During verify -> drift-detect -> critique -> auto-promote.

Use v0.3 when you have two model families available. Use v0.5 when you want single-AI operation. The two stack — projects can run both, with v0.3's cross-family audit firing on a sample of v0.5 runs.

### Known limitations

- **Correlated single-model-family blind spots.** Critic and verifier are both same-model-family. If both agents share a wrong assumption that fits the manifest, both sign off and the auto-promote fires green. Dual-AI is the only structural defense against this. Mitigation: periodic sample audit by a different model family on a weekly cadence or after every Nth run. The v0.3 `/audit-init` discipline still applies.
- **Auto-promote depends on parseable count lines.** The verifier, critic, and drift-detector role files explicitly require the count-line format. If a role file is customized in a way that drops or malforms the line, auto_promote.py treats the run as NOT_ELIGIBLE and falls back to the human gate.
- **The judge layer still fires only on the executor stage.** Even with v0.5 active, the judge does not intercept critic, drift-detector, or verifier actions. Those roles are read-only by contract.
- **Schema validation cannot verify manifest correctness, only structure.** A confident-wrong manifest that satisfies every schema rule still produces wrong work. The manifest gate (human) remains the only place the manifest's content is reviewed.

## [0.4.0] — 2026-05-11

The judge layer. Real-time action-level supervision inside the executor stage. Built from Nate Jones, "LLM-as-Judge" (May 2026). The Lindy case study — an agent that sent 14 unauthorized emails because operator-trained-reflex APPROVE clicking defeated manual confirmation — showed that prompts don't hold across long context, and per-action confirmation alone breeds the cookie-banner effect. The architectural fix is a second agent (the judge) whose sole loyalty is the manifest, evaluated in context isolation from the executor's reasoning chain.

### Added

- `pipelines/roles/judge.md` — role file for the judge subagent. Returns exactly one of four verdicts: `allow`, `block`, `revise`, `escalate`. Output is a single YAML block, no prose. Hard rules forbid helping the executor, negotiating, inferring authorization, summarizing, deferring to executor confidence, approving by precedent, or modifying anything outside the verdict file. Inputs are deliberately scoped: manifest, matched action policy, prior judge decisions for the run, and the structured action proposal — but **not** the executor's reasoning chain. Context isolation is the mechanism.
- `pipelines/action-classification.yaml` — opt-in classification rules. Four risk classes (`read_only`, `reversible_write`, `external_facing`, `high_risk`) with first-match-wins evaluation top-to-bottom within each class. Class priority `high_risk` → `external_facing` → `reversible_write` → `read_only`. Default class for unmatched actions: `reversible_write`. Ships with the common dangerous and external-facing patterns: `rm -rf`, `git push --force`, `git push main`, `DROP TABLE`, `npm publish`, `gh pr create`, `curl -X POST`, `docker push`, `kubectl apply`, credential-touching `export *KEY=`, etc.
- `commands/run-pipeline.md` — **Handler 3a** for the executor stage when `.pipelines/action-classification.yaml` exists. Wraps the executor in a classify → judge → execute inner loop. Routes by class: `read_only` and `reversible_write` execute immediately + log; `external_facing` requires judge ALLOW; `high_risk` requires judge ALLOW plus human confirm. Verdict routing: `allow` executes, `block` halts the pipeline, `revise` returns a concrete revision instruction (max 3 cycles per action_id; auto-escalate after), `escalate` pauses for a specific human question. Handler 3 (the v0.3 executor handler) is preserved unchanged and is selected when `action-classification.yaml` is absent — the layer is opt-in by file presence.
- `judge-log.yaml` artifact — chronological per-action record written to the run directory when the judge layer is active. Captures tool, arguments, class, disposition (`auto_allow` / `judged_allow` / `judged_revise` / `judged_block` / `judged_escalate` / `human_confirmed` / `human_blocked`), judge verdict, judge reason, revision instruction, and timestamp.
- `judge-metrics.yaml` artifact — aggregate counts plus `escalation_rate`, `judge_invocations`, `revision_cycles`. Written alongside `judge-log.yaml` at executor-stage end. The escalation rate is the operator's tuning signal — see USER-MANUAL.md §"The judge layer (v0.4)".
- `judge-decisions/<action_id>.yaml` directory — per-action verdict files written by the judge subagent. Read by the next judge invocation as `prior_judge_decisions` so re-proposals of blocked actions are detected without depending on conversation memory.
- ARCHITECTURE.md §7 — full design rationale, the classify → judge → execute inner-loop diagram, the context-isolation diagram, the relationship-to-other-gates table, the four-verdicts spec, and the opt-in-by-file-presence model.
- README.md §"v0.4: Judge layer" — quickstart overview with the four classes, the four verdicts, and the artifacts produced. One-line summary: "Pipeline (v0.2) catches execution-cascade failures. Audit-handoff (v0.3) catches drift failures. Judge layer (v0.4) catches unauthorized actions in real time."
- USER-MANUAL.md §"The judge layer (v0.4)" — operator-facing guidance. Enabling and disabling, customizing rules per project, reading `judge-log.yaml` and `judge-metrics.yaml`, escalation-rate tuning (too-low vs too-high vs healthy range 0.02–0.10), adding project-specific high-risk patterns, and what to do when the judge ESCALATEs and you aren't sure (don't reflex-APPROVE — fix the manifest ambiguity).

### Why each new piece exists

- **Context isolation prevents single-model-family correlated judgment.** The judge cannot be persuaded by the same chain of inferences that produced the over-broad action because it never sees them. The manifest and the action proposal are the inputs; the executor's reasoning chain is deliberately withheld.
- **Four verdicts, not two, prevent BLOCK fatigue.** ALLOW / BLOCK alone forces the judge into binary calls on actions where a small revision (push to feature branch, not main) would make the action correct. `revise` and `escalate` give the judge ways to be useful without halting the pipeline on every borderline call.
- **High_risk + human confirm even after judge ALLOW is belt-and-suspenders.** A judge ALLOW on `rm -rf` or `git push --force` is still a moment a human should see. The judge's ALLOW raises confidence that the action is authorized; the human confirm is the final check that no inferred-authorization slipped through.
- **Opt-in by file presence keeps the layer composable.** Projects that don't need real-time action supervision (small repos, no external services, mature contributor base) can run without the file and get v0.3 behavior. Projects that need it add one YAML file. There is no separate `/enable-judge` command and no manifest field to remember.
- **Metrics in `judge-metrics.yaml`, not just logs, give the operator a tuning loop.** Without an aggregate, operators can't tell whether they're at 0% escalation (rules too loose) or 30% (cookie-banner fatigue forming). The `escalation_rate` is computed every run; reviewing it after the first 5–10 runs typically converges the rules to a healthy range.

### Stacking with v0.2 and v0.3

- Pipeline (v0.2) catches execution-cascade failures: pre-existing CI bugs, tag-move dances, halt-and-ask loops. Pre-executor.
- Audit-handoff (v0.3) catches drift failures: wrong endpoint, stale CHANGELOG, status-word abuse. Post-executor.
- **Judge layer (v0.4) catches unauthorized actions in real time.** **During** the executor stage, at the action boundary, before the action lands. The other two run before and after the executor; the judge runs **during**.

The three layers address three different failure classes and can be enabled independently. Many projects will run all three.

### Known limitations

- **Single-model-family blind spots may still correlate.** The judge is a subagent of the same model family as the executor. Some classes of failure (e.g., a particular phrasing that biases both agents identically) can persist. The architectural defense (context isolation) reduces this risk; it does not eliminate it.
- **The judge is slower than no-judge.** Every `external_facing` and `high_risk` action incurs a subagent spawn. For executor stages dominated by `read_only` and `reversible_write` actions this is negligible; for stages with many external operations (e.g., heavy `gh` API or `curl` use) it adds real wallclock time.
- **Rules drift.** The shipped `action-classification.yaml` is generic. Projects with their own dangerous commands (`make deploy-prod`, custom CLI tools) will need to add project-specific rules; until they do, those actions fall into the default class (`reversible_write`) and execute without judge review.
- **The judge cannot see future state.** It evaluates one action at a time against the current manifest. A sequence of individually-authorized actions that compose into an unauthorized outcome (e.g., creating three files that together expose a secret) is not caught by the judge — it is caught by the policy stage and the verifier.
- **Auto-escalation after 3 revision cycles is an upper bound, not a target.** If revision_cycles is consistently high across runs, that usually indicates a manifest clarity problem, not a judge problem.

## [0.3.0] — 2026-05-11

The dual-AI audit-handoff discipline. Built from the CivicCast `process/shared-audit-knowledge` PR (commit `bfc5a2a`) which formalized a pattern that had been proven across multiple sprints: an implementing AI runs a hostile 5-lens self-audit before push, a verifying AI runs a documented 10-section protocol after push, and both share an in-repo doc so neither re-derives the rules from scratch each session.

### Added

- `/audit-init` slash command. Scaffolds the three-artifact dual-AI audit infrastructure for a project: out-of-repo `<PROJECT>_AUDIT_GATE.md` and `<PROJECT>_AUDIT_PROTOCOL.md`, in-repo `<project>/docs/process/5-lens-self-audit.md` (lands via PR), plus per-agent wiring (Claude memory feedback file on the Claude side, runtime-equivalent project-context file on the second AI's side).
- `pipelines/roles/cross-agent-auditor.md` — role file for the verifying agent. Mandatory 10-section output (Verdict / Claim Verification Matrix / Durable Artifact Reads / Substantive Content Checks / Drift Matrix / Working Tree & Remote State / Unreported Catches / Open Caveats / Paste-Ready Directive / Recommended Next Action). Status-word rules. Runtime confidence separation. Failure handling.
- `pipelines/roles/implementer-pre-push.md` — role file for the implementing agent. Five lenses (Engineering / UX / Tests / Docs / QA). Artifact-state checklist. Post-push SHA-propagation step. Proof-anchor vs release-target distinction. Report format with mandatory 5-lens block.
- `pipelines/templates/audit-gate-template.md` — short gate template with `<PROJECT_NAME>`, `<IMPLEMENTER_AGENT>`, `<AUDITOR_AGENT>`, `<AUDIT_PROTOCOL_PATH>` placeholders.
- `pipelines/templates/audit-protocol-template.md` — long protocol template with 22 sections; section 22 (Known Drift Patterns) is the project's catalog that accumulates over time.
- `pipelines/templates/5-lens-self-audit-template.md` — in-repo shared doc template with generic artifact-state checklist; project-specific items accumulate as the auditor surfaces new drift patterns.
- `docs/audit-handoff-handbook.md` — operator reference. When to use, how the two halves interact, role-agent matrix, stacking with the pipeline, honest expectations of what the discipline reduces vs. what it doesn't.

### Why each new piece exists

- **Dual-AI separation of duties.** A single AI auditing its own work catches less drift than two AIs with separate context. The implementer reads its own diff as the agent that produced it; the auditor reads cold against a documented protocol. Second-perspective catches what first-perspective missed — the same property that makes human code review work.
- **5-lens self-audit before push.** A chat-promise ("I'll keep this in mind") is not a behavior change. The behavior change is the durable artifact: the hostile self-audit on the actual diff, with results printed in the report. Forces the implementing agent to rebut its own diff before pushing.
- **10-section verification output.** Sparse audits ("looks good to me") generate no useful directives for the next implementing turn. The 10-section structure forces the auditor to produce a paste-ready directive every turn, even when cleanup is complete (then it's the next-phase directive).
- **In-repo shared doc.** Both agents read it. When the auditor finds drift, the auditor's directive references the relevant section. New drift patterns get added as artifact-state checklist items — the discipline strengthens over time.
- **Out-of-repo gate and protocol.** They govern the auditor's behavior BEFORE entering the repo. They can be updated without dragging a PR through project review (when standards tighten mid-sprint).

### Role-agent symmetry

The discipline is symmetric. Any AI can play either role; the plugin runs in Claude Code, the second AI can be any tool that exposes a standing-instructions surface (project-context file, skill registration, custom-instruction field, etc.). `/audit-init` asks for role assignment and wires the per-agent pointers accordingly. Single-agent fallback is supported but loses the structural benefit.

### Stacking with v0.2

- The pipeline (v0.2) catches execution-cascade failures: pre-existing CI infrastructure bugs, tag-move dances, halt-and-ask loops.
- The audit-handoff discipline (v0.3) catches drift failures: wrong endpoint, stale CHANGELOG, "Closed" without evidence, status-word abuse, durable docs drifting in parallel.

The two stack. Pipeline's Phase 1 is where the implementer's 5-lens fires. Pipeline's Phase 4 is where the auditor's 10-section output fires. Human gates remain unchanged.

### Known limitations

- The discipline does not prevent wrong-direction product decisions (audit verifies execution, not strategy).
- It does not prevent cascading CI infrastructure bugs (that's what the pipeline's Phase 0 is for).
- Single-agent runs collapse to self-audit-only — the structural benefit comes from independent context.
- The drift-pattern catalog (section 22 of the protocol) starts empty for new projects. The first few audit cycles will surface patterns that establish the project's specific drift profile.

## [0.2.0] — 2026-05-11

The `module-release` pipeline. Built from the CivicSuite civicrecords-ai v1.5.0 sprint that burned ~8 hours on cascading discovery of three pre-existing latent `release.yml` bugs. Validated end-to-end against the CivicSuite D2/B3 staff_key_gate sprint, which shipped CivicCore v1.1.0 with **zero tag moves** on the first push — the pipeline's design target.

### Added

- `pipelines/module-release.yaml` — 4-phase pipeline: Phase 0 preflight → Phase 1 product → Phase 2 local rehearsal → Phase 3 remote release + umbrella → Phase 4 verifier → Phase 5 manager. Human gates at Phase 0 / Phase 2 / Phase 5.
- `pipelines/roles/preflight-auditor.md` — Phase 0 role. Audits the module's release workflow and supporting CI before any product code is touched. Check 1–7 sequence (YAML parse, workflow run health, scripts exist, local verify on fresh state, cross-platform reality, diagnostic instrumentation, audit-punchlist correlation). Bugs found are bundled into ONE PR.
- `pipelines/roles/local-rehearsal.md` — Phase 2 role. Mirrors the CI environment and runs the release sequence locally on fresh state before the tag push. The release workflow becomes the execution mechanism, not the discovery mechanism.
- `pipelines/self-classification-rules.md` — pre-authorized classifications applied during Phase 1: LIVE-STATE / FROZEN-EVIDENCE / SHAPE-GUARD / OWN-MODULE-VERSION for grep hits; MECHANICAL-CI-BUG / CONTRACT-CHANGE / ENVIRONMENTAL / NOVEL for failures. Bundling discipline and a tag-move budget (target 0, ceiling 1 per sprint).
- `scripts/preflight_infrastructure.py` — Phase 0 runner. Six automated checks; non-zero exit blocks Phase 1 work.
- `docs/module-release-handbook.md` — operator reference with honest timing expectations (`~8h → ~2-3h` for infra-debt modules) and a "what this pipeline does NOT prevent" section (unknown unknowns, inter-module integration surprises, agent judgment errors).

### Why each new piece exists

- **Phase 0 prevents the cascade.** The civicrecords-ai sweep had three latent `release.yml` bugs that surfaced one at a time during Phase 3 (remote release). Each surface required a PR + merge + tag-move + 4-minute CI cycle. Phase 0 inverts this: find the bugs by reading workflow YAML, grepping referenced scripts, running `verify-release.sh` locally on fresh state, and cross-referencing the audit punchlist. Fix all of them in ONE bundled PR. Then product work begins.
- **Self-classification rules prevent halt-and-ask churn.** The civicrecords-ai chat had ~25% of its content as "agent halted, asked permission, human answered, agent continued" on routine cases (URL update, version-string update, frozen-doc skip, shape-guard skip). The rules pre-authorize the long tail; halt-and-ask is reserved for genuine novelty.
- **Phase 2 prevents the tag-move dance.** The civicrecords-ai v1.5.0 tag moved FOUR times during recovery. Phase 2 forces the agent to run the release sequence locally before pushing the tag; the workflow becomes the execution mechanism, not the discovery mechanism.

### Validation

End-to-end run against CivicSuite D2/B3 staff_key_gate sprint (2026-05-11):
- Phase 0 found one infrastructure bug, bundled fix shipped as CivicCore PR #55.
- Phase 1 product work shipped staff_key_gate helper as CivicCore PR #56.
- Phase 2 local rehearsal passed on fresh state; SHA captured matched final release.
- Phase 3 tag push: **zero tag moves**, release published first try.
- Six downstream module sweeps merged green; umbrella PR #123 merged through `release-lockstep-gate`.
- All 26 modules PASS on `verify-suite-state.py --remote-only`.

### Known limitations

- Designed for module-version-bump and dependency-migration sprints. Not a fit for pure feature work (use `feature.yaml`) or bug fixes that don't ship a release (use `bugfix.yaml`).
- The Phase 2 local rehearsal cannot fully simulate signed/notarized Windows installer builds without a local Windows VM, or macOS notarization without paid Apple credentials. Document the trust gaps in the rehearsal report.
- Pipeline timing wins are concentrated in modules with infrastructure debt. Low-debt modules see modest improvement (~30 min sprint stays ~30 min).

## [0.1.0-beta] — 2026-05-09

Initial public beta. The plugin has shipped real features in at least
one project (CivicCast Sprint 0.3); the slash-command edge cases will
surface in your codebase before they surface in the maintainer's.

### Added

- `/pipeline-init` slash command with three onboarding paths:
  PRD/spec document, existing repo (URL or local path), or description
  paragraph. Scaffolds `.pipelines/`, `scripts/policy/`, `CLAUDE.md`,
  and a `.gitignore` entry.
- `/new-run` slash command. Initializes
  `.agent-runs/<run-id>/manifest.yaml` from the template.
- `/run-pipeline` orchestrator slash command. Reads the pipeline YAML,
  walks stages in order, dispatches to one of three handlers
  (human-gate / pipeline-command / agent), writes append-only
  `run.log`, resumes from the right place on re-invocation.
- `feature` pipeline (8 stages: manifest → research → plan →
  test-write → execute → policy → verify → manager).
- `bugfix` pipeline (7 stages: manifest → research → plan →
  reproduce → patch → policy → verify → manager).
- Six role files: researcher, planner, test-writer, executor, verifier,
  manager. Each is the verbatim contract a fresh subagent receives.
- Three policy checks shipped:
  `check_allowed_paths.py`, `check_no_todos.py`,
  `check_adr_gate.py`, plus the `run_all.py` aggregator.
- `manifest-template.yaml` with inline field documentation: `id`,
  `type`, `branch`, `goal`, `allowed_paths`, `forbidden_paths`,
  `non_goals`, `expected_outputs`, `required_gates`, `risk`,
  `rollback_plan`, `definition_of_done`, `director_notes`.
- Documentation: `README.md`, `USER-MANUAL.md` (operator-facing),
  `ARCHITECTURE.md` (with Mermaid diagrams), `docs/index.html`
  (GitHub Pages landing page).

### Lessons baked into defaults

- **Halts apply to ALL repo state changes.** No "obviously safe"
  cleanup PRs while a gate is open.
- **The manager must cite verifier evidence verbatim.** The role file
  forbids encouragement and summarization — these were how bad runs
  promoted in prior projects.
- **Policy checks halt the pipeline on non-zero exit.** No "warning
  only" — that's how scope creep gets in.
- **The `run.log` is append-only.** Editing it to "fix" a stage hides
  the underlying bug. The orchestrator parses the log to determine
  resume point; resume is the only valid recovery.
- **Subagents have fresh context.** Each stage starts with the role
  file + on-disk artifacts. The orchestrator's conversation history is
  not shared.
- **Cleanroom CI is recommended in the orientation summary.** A
  Docker-based reproduction with a fresh dependency set catches
  "works on my machine" bugs that local pytest misses.

### Known limitations

- The orchestrator does not currently support nested pipelines (one
  pipeline invoking another). Out of scope for v0.1.
- The plugin does not enforce that you have committed your manifest
  before starting a run; you can if you want, but `.agent-runs/` is
  gitignored by default.
- The `bugfix` pipeline assumes the bug is reproducible; if it isn't,
  the `reproduce` stage will fail and you'll need to fall back to a
  `feature`-style flow.
- Policy checks are written in Python; if your project doesn't have
  Python available, the policy stage will fail. (Roadmap item: a
  shell-only fallback.)

### Roadmap (not committed — feedback wanted)

- v0.2: optional `cleanroom` stage that runs the test suite in a Docker
  container with a fresh dependency install.
- v0.2: project-specific check templates (e.g.,
  `check_no_console_log.py` for JS projects, `check_ffmpeg_wrapper.py`
  for media projects).
- v0.3: a `refactor` pipeline type for behavior-preserving changes
  (different verifier criteria — diff-mode tests).
- v0.3: a `--dry-run` flag on `/run-pipeline` that walks the stage
  list and prints what would happen without spawning agents.

[0.3.0]: https://github.com/scottconverse/agent-pipeline-claude/releases/tag/v0.3.0
[0.2.0]: https://github.com/scottconverse/agent-pipeline-claude/releases/tag/v0.2.0
[0.1.0-beta]: https://github.com/scottconverse/agent-pipeline-claude/releases/tag/v0.1.0-beta
