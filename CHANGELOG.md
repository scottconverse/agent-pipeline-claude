# Changelog

All notable changes to `agentic-pipeline` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project follows [Semantic Versioning](https://semver.org/) once it
leaves beta. While in `0.1.x-beta`, breaking changes to slash-command
arguments, manifest fields, or role-file contracts may land in any
release; the `CHANGELOG` will call them out.

## [0.3.0] — 2026-05-11

The dual-AI audit-handoff discipline. Built from the CivicCast `process/shared-audit-knowledge` PR (commit `bfc5a2a`) which formalized a pattern that had been proven across multiple sprints: an implementing AI runs a hostile 5-lens self-audit before push, a verifying AI runs a documented 10-section protocol after push, and both share an in-repo doc so neither re-derives the rules from scratch each session.

### Added

- `/audit-init` slash command. Scaffolds the three-artifact dual-AI audit infrastructure for a project: out-of-repo `<PROJECT>_AUDIT_GATE.md` and `<PROJECT>_AUDIT_PROTOCOL.md`, in-repo `<project>/docs/process/5-lens-self-audit.md` (lands via PR), plus per-agent wiring (Claude memory file / Codex skill addition).
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

The discipline is symmetric. Any agent can play either role. CivicCast uses Claude=implementer / Codex=auditor; CivicSuite uses Codex=implementer / Claude=auditor. `/audit-init` asks for role assignment and wires the per-agent pointers accordingly. Single-agent fallback is supported but loses the structural benefit.

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

[0.3.0]: https://github.com/scottconverse/agentic-pipeline/releases/tag/v0.3.0
[0.2.0]: https://github.com/scottconverse/agentic-pipeline/releases/tag/v0.2.0
[0.1.0-beta]: https://github.com/scottconverse/agentic-pipeline/releases/tag/v0.1.0-beta
