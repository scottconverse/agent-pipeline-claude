# Q&A — Frequently asked questions

The questions that recur often enough to warrant durable answers. If your question is here, the answer is here too. If it isn't, ask — the answer might land in this thread later.

## Setup and onboarding

### Q: How is this different from just writing a CLAUDE.md and asking Claude Code to follow it?

CLAUDE.md captures conventions; the pipeline enforces them. A passing CLAUDE.md instruction lives in the prompt; a passing pipeline gate lives in `run.log` with a timestamp and an artifact. The difference shows up after the third session, when "I told the agent to do X" turns into "did the agent actually do X" and you can't tell without re-reading the whole conversation. The pipeline writes durable artifacts at every stage so the answer to that question is `grep` in a directory, not memory of a chat.

### Q: Do I have to use all the gates? Three approvals per run feels heavy.

Yes for any non-trivial work. The gates exist because every project this was tested on had at least one stage where the agent silently picked an architectural decision that should have been a human call. The cost is three short approvals per run; the benefit is the third one catching what the first two missed. If you find yourself rubber-stamping all three, the manifest probably wasn't specific enough — that's a manifest-template problem, not a gate problem.

### Q: What if my project doesn't have ADRs?

`check_adr_gate.py` exits 0 vacuously (no `docs/adr/` directory means no gate to enforce). The pipeline doesn't require ADRs; the gate exists for projects that have them. You can add ADRs incrementally — the first one you write is when the gate becomes load-bearing.

### Q: Can I add a new pipeline type?

Yes. Drop a `.pipelines/<your-type>.yaml` file in your project's pipeline directory; the orchestrator picks it up automatically. The role names must match existing roles in `.pipelines/roles/` or you add new role files. The default `feature.yaml` and `bugfix.yaml` are starting points; a `refactor.yaml` that swaps `test-writer` for a `behavior-snapshot` role is a common addition.

## Running a pipeline

### Q: How do I resume after a halt?

Re-invoke the same `/run-pipeline <type> <run-id>` command. The orchestrator reads `run.log`, finds the first stage without a `COMPLETE` entry, and resumes from there. `FAILED` and `BLOCKED` count as incomplete, so they re-run. The log is the source of truth — never edit it.

### Q: The verifier marked a criterion NOT MET but I think it's fine. Can I override?

No. The manager hard rule forbids PROMOTE on any NOT MET criterion. The only exception is PARTIAL with explicit director-decisions deferral, and that requires both halves cited verbatim. If you genuinely disagree with the verifier, the fix is to amend the manifest (clearer `expected_outputs`, clearer `definition_of_done`) and re-run — not to override the verdict. The whole point of the verifier is that it cannot be talked out of NOT MET.

### Q: My executor's tests pass locally but CI fails. Why?

Almost always: stale local venv. The executor role file requires verification against a fresh dependency set (`pip install -e ".[dev]"` or equivalent) before claiming COMPLETE. If you have a Docker cleanroom CI stage, this gap disappears — that's the recommended addition for any project where dep-install fragility could surface.

### Q: How do I know if the v0.4 judge layer is active for a run?

The presence of `.pipelines/action-classification.yaml` in your project at run start. If it exists, the orchestrator uses Handler 3a (classify → judge → execute) for the executor stage, and the run directory will contain `judge-log.yaml` and `judge-metrics.yaml` at the end. If the file doesn't exist, the executor stage runs unchanged from v0.3, and no judge artifacts are produced.

## Customization

### Q: How do I add a project-specific policy check?

Drop a `check_<name>.py` script in your project's `scripts/policy/` directory and add an entry to the `CHECKS` list in `run_all.py`. Each check exits 0 on pass, non-zero on fail, and prints to stdout. The plugin's generic checks are the template; CivicCast's `check_ffmpeg_wrapper.py` (a project-specific check that enforces ffmpeg calls go through a wrapper module) is an example of the pattern.

### Q: How do I customize the judge classification rules?

Edit `.pipelines/action-classification.yaml` directly in your project. Rules within each class are first-match-wins; classes are evaluated in priority order (`high_risk` → `external_facing` → `reversible_write` → `read_only`). To make a specific command high-risk that the generic rules don't catch (e.g. `make deploy-prod`), add it under `high_risk` with a `pattern` and a `note`. To make a specific endpoint-touching `curl` more strictly classified, add a more specific rule **above** the generic `curl -X POST` entry.

### Q: My escalation rate is 0.40. What's wrong?

The rules are too tight, or the manifest is too loose. Either way, the cookie-banner effect is forming. Look at `judge-log.yaml` and group the `judged_escalate` and `human_blocked` entries by pattern — if the same kind of action keeps escalating, that pattern should probably be in a less-strict class. If the escalations are scattered across many different action types, the manifest is probably ambiguous about what's authorized and the judge defaults to low confidence. Tighten the manifest, not the rules.

### Q: My escalation rate is 0.00. Is that good?

Probably not. If the judge layer is active but no action is ever escalating, the rules are too permissive — every action is sliding into `read_only` or `reversible_write` and the judge never gets to intervene. Walk back through `judge-log.yaml` and ask whether any of the auto-allowed actions should have been judged. Common miss: project-specific dangerous commands that look reversible to the generic rules but aren't.

## Conceptual

### Q: Why is the manifest required to be one paragraph for `definition_of_done`?

A definition of done that doesn't fit in one paragraph is two manifests. Splitting it into two runs is cheaper than carrying the ambiguity through every downstream stage. If you find yourself wanting to write three paragraphs, that's a signal — make it two runs.

### Q: Why three human gates, not two or four?

Two means autonomous-mode-by-stealth — there's no plan gate, so the executor and verifier run on whatever the researcher inferred. Four means rubber-stamping — humans stop reading carefully when the same APPROVE button appears too often. Three is the empirical sweet spot from multiple projects; deviation from three is a real decision and belongs in your project's `docs/adr/`.

### Q: Why is the manager not allowed to encourage?

Because encouragement and summarization are how bad runs get promoted. A manager that says "looks great overall, just two small issues" is a manager that has stopped reading the verifier and started reading the room. The role file forbids it explicitly: every PROMOTE must cite verifier evidence verbatim. The wording isn't accidentally curt — it's the architectural defense against soft-promotion.

### Q: What's the difference between `block` and `revise` in the v0.4 judge?

`block` means "this action shouldn't happen at all" — the executor's proposal is fundamentally outside scope and there's no reformulation that makes it fit. `revise` means "the action's intent is fine, the form is wrong" — push to a feature branch, not main; draft, don't send; archive, don't delete. The pipeline halts on `block`; it returns control to the executor with a concrete revision instruction on `revise`. Max 3 revise cycles per action before auto-escalation.

---

**Add a question:** Reply to this thread, or open a new Q&A discussion. Questions that recur three or more times get pulled into this seed post so the next operator finds the answer in one place.
