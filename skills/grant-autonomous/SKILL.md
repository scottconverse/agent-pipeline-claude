---
name: grant-autonomous
description: (Deprecated in v1.3.0 — the grant system is gone.) v1.3.0 removed the grant-based autonomous mode entirely; gates fire as fast modal questions and auto-promote replaces the authorization-file mechanism.
---

# Deprecated in v1.3.0

This skill is a no-op. v1.2.1 introduced grant files at `.agent-workflows/autonomous-grants/<name>.md` to authorize autonomous-mode pipeline runs. The mechanism was over-engineered: it solved "LLM ignores conversational authorization" by adding a signed file, but the actual failure mode was the chat-APPROVE ceremony, not the lack of structural authorization.

The v1.3.0 fix is simpler: replace chat-APPROVE with `AskUserQuestion` (a modal one-click prompt) for the three human gates. No grant, no signature, no ceremony. When `auto_promote.py` reports all checks clean, the manager gate is skipped automatically — this is evidence-driven automation rather than authorization-driven.

## What to do instead

You do not need a grant for anything. Just run `/agent-pipeline-claude:run "<task description>"`. Modal gates handle the human checkpoints; auto-promote handles the hands-off case.

If you have grant files on disk, you can:
- Leave them — they are ignored.
- Archive them — `mv .agent-workflows/autonomous-grants/ .agent-workflows/autonomous-grants.archived-pre-v1.3.0/`.

## Will not be reactivated

The structural problem the grant system was supposed to solve (LLM interpretive judgment at gates) is solved better by modal `AskUserQuestion`. There is no roadmap to bring grants back.
