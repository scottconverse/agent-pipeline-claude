# Show and tell — what have you built with agent-pipeline-claude?

This thread is for case studies. Real runs, real artifacts, real receipts. If you've used the plugin on a project — small or large — share what happened, what worked, and what didn't.

## What I'd like to see in a case study

Not a marketing testimonial. A specific run with concrete artifacts. The pattern that's useful for everyone else reading:

- **What project, what task.** One sentence each.
- **Which pipeline type** (`feature`, `bugfix`, `module-release`, or a custom one you wrote).
- **The manifest** — at least the `goal`, `allowed_paths`, `definition_of_done` fields. (Redact anything sensitive.)
- **How long it took.** Wall-clock from `/new-run` to `manager: PROMOTE` (or the halt point if it didn't promote).
- **Where it halted or surprised you.** The gate that caught something, the verifier finding that mattered, the manifest amendment that was needed.
- **What you'd do differently next time.** Manifest fields you'd tighten, role files you'd customize, pipeline types you'd add.
- **One artifact attached or linked.** Even a screenshot of `manager-decision.md` makes the story concrete.

## Why this thread exists

The plugin's defaults are baked from a small number of projects' failure receipts. The next round of defaults comes from the next round of receipts. Case studies are how that loop closes — your "the manifest was wrong" surfaces a pattern that becomes the next `manifest-template.yaml` improvement.

## Seed examples — what other operators have shipped

These are example summaries from projects that shipped with the plugin. Use them as the shape for your own posts.

### CivicCast — v0.2.0 streaming origin (`module-release`)

**Project:** CivicCast — open-source civic broadcast platform.
**Pipeline:** `module-release`.
**Task:** Ship `civiccast` v0.2.0 (HLS packager + CDN adapter).
**Manifest goal:** "Persist asset metadata in PostgreSQL via Pydantic models and a reversible Alembic migration, replacing the in-memory store with a database-backed implementation."
**Wall-clock:** ~6 hours across multiple sessions.
**What caught:** Phase 0 preflight found one infrastructure bug in `release.yml` (workflow referenced a script that didn't exist). Bundled fix as a separate PR; product work landed on top cleanly. Phase 2 local rehearsal caught a `psycopg[binary]` import that worked locally because of a stale venv but failed on a fresh dep install.
**Tag moves:** Zero. (The project had four tag moves on the previous release without the pipeline.)
**Next time:** Director-decisions stage added explicitly — researcher surfaced two architecture questions that should have been recorded in writing before the planner ran, but weren't in the default `feature.yaml`.

### CivicSuite — civicrecords-ai v1.5.0 sweep (`module-release`)

**Project:** CivicSuite — multi-module FOIA / open-records suite.
**Pipeline:** `module-release`.
**Task:** Sweep `civicrecords-ai` from `civiccore 0.22.1` to `civiccore 1.0.0`.
**Wall-clock:** ~3 hours.
**What caught:** Self-classification rules (LIVE-STATE / FROZEN-EVIDENCE / SHAPE-GUARD / OWN-MODULE-VERSION) eliminated ~25% of the prior sweep's halt-and-ask churn. The verifier caught two stale CHANGELOG entries that the executor would have shipped.
**Tag moves:** Zero. (The same module had four tag moves in the pre-pipeline recovery sweep.)
**Next time:** Project-specific `check_civiccore_version.py` policy check added — caught a pin-version drift that the generic checks didn't notice.

### AgentSuiteLocal — v1.0.0 release prep (custom pipeline)

**Project:** AgentSuiteLocal — local-only agent management suite.
**Pipeline:** Custom `release-prep.yaml` (extends `feature` with a pre-tag verification stage).
**Task:** v1.0.0 release prep across three sprints (Sprint A, Sprint B, sprint-end re-audit).
**Wall-clock:** Multi-week, across many runs.
**What caught:** The audit-team skill called from the verifier role surfaced a V4 root-cause issue that careful-coding had missed at altitude 1. The mid-rung overflow rule (Blocker stops rung, Critical only if it fits) prevented sprint scope creep when a Critical surfaced in week 2.
**Next time:** v0.4 judge layer adopted retroactively for v1.1 work — `npm publish` and `git push --force` now ride the high_risk path with explicit human confirm even when the judge ALLOWs.

---

## How to post

Reply to this thread or start a new Show and tell discussion. If you have an artifact (a `manager-decision.md`, a `verifier-report.md`, a `judge-log.yaml`) you can share, attach it — the plugin's defaults improve fastest when we can see the actual evidence.

The bar isn't "this was a flawless run." The bar is "this is a specific story another operator can learn from." Halts and surprises are more useful posts than smooth runs.
