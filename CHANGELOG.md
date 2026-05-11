# Changelog

All notable changes to `agentic-pipeline` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project follows [Semantic Versioning](https://semver.org/) once it
leaves beta. While in `0.1.x-beta`, breaking changes to slash-command
arguments, manifest fields, or role-file contracts may land in any
release; the `CHANGELOG` will call them out.

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

[0.2.0]: https://github.com/scottconverse/agentic-pipeline/releases/tag/v0.2.0
[0.1.0-beta]: https://github.com/scottconverse/agentic-pipeline/releases/tag/v0.1.0-beta
