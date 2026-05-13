---
name: run-autonomous
description: Run the agent-pipeline-claude pipeline under autonomous mode (the three human-approval gates auto-approve based on the LLM's own recommendation, logged to .agent-runs/<id>/autonomous-decisions.md). Requires a valid autonomous-mode grant; see /agent-pipeline-claude:grant-autonomous. Invoked as /agent-pipeline-claude:run-autonomous --grant <grant-path> "<task description>".
---

# Run-autonomous

Entry-point for autonomous pipeline runs. Validates the grant, drafts the manifest with `gate_policy: autonomous`, then invokes the normal `/agent-pipeline-claude:run` flow which honors the autonomous-mode hard rules in `skills/run/SKILL.md`.

## Argument shape

`$ARGUMENTS` is `--grant <path> "<task description>"`. The task description is the same shape `/agent-pipeline-claude:run` expects.

## Procedure

1. **Parse `--grant <path>`.** Reject if missing — autonomous mode is grant-required.

2. **Validate grant via `scripts/policy/check_autonomous_mode.py --grant <path>`.** If exit non-zero, halt and report. Common failures:
   - `NO_GRANT_FILE` — path doesn't exist
   - `GRANT_EXPIRED` — Expires-at is in the past
   - `GRANT_REVOKED` — Revoked: true
   - `GRANT_MALFORMED` — required headers missing

3. **Set manifest fields.** The manifest-drafter (invoked next) receives instructions to set `gate_policy: autonomous` and `autonomous_grant: <path>` in the manifest it produces.

4. **Invoke `/agent-pipeline-claude:run` with the task description.** The run skill's v1.2.1 hard rules kick in once the manifest carries `gate_policy: autonomous`. Three gates auto-approve; PRs are opened but NOT admin-merged.

5. **Each autonomous-decision logs to `.agent-runs/<run-id>/autonomous-decisions.md`.** Per the role files' autonomous-mode-awareness sections.

6. **`check_autonomous_compliance.py` runs post-execute** in the policy stage. Any wait-for-human chat patterns or forbidden actions emit `COMPLIANCE_DRIFT` findings.

7. **Run completes when:**
   - Manager-decision is PROMOTE → PR opened, awaiting human admin-merge. Run logs completion.
   - Manager-decision is BLOCK or REPLAN → halts for human regardless of mode.
   - Mid-run grant revocation → halts at next gate.
   - Compliance drift detected → manager-decision treats as Blocker, halts.

## Hard rules

- **No grant, no run.** Cannot bypass the grant check.
- **The run skill's v1.2.1 hard rules apply.** No admin-merge, no tag push, no release publish, no force push, no human_only_under_autonomous actions.
- **Grant is re-validated before EVERY gate.** Mid-run revocation halts the next gate. Mid-run expiration likewise.
- **All decisions log.** Every autonomous-approve writes to `.agent-runs/<run-id>/autonomous-decisions.md` with timestamp + rationale + grant citation.
- **If you see a `Reply APPROVE` chat message produced by any stage under autonomous mode, that's a `COMPLIANCE_DRIFT` event.** The post-run check will catch it; treat it as a Blocker finding.

## Status / abort

To check on a running autonomous run: `/agent-pipeline-claude:run status` (the regular run skill's status path; works for autonomous runs too).

To abort mid-run: `/agent-pipeline-claude:grant-autonomous` with "revoke autonomous" or "kill it." The grant gets revoked; the next gate halts.

To resume after a halt: `/agent-pipeline-claude:run resume <run-id>`. If the grant is still active, autonomous mode resumes. If expired/revoked, the run reverts to human mode for the remaining stages.
