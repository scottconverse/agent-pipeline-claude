---
name: grant-autonomous
description: Create, revoke, extend, or delete an autonomous-mode grant. The grant authorizes the agent-pipeline-claude pipeline to auto-approve specific human gates (manifest / plan / manager-PROMOTE) under explicit time-bounded, action-bounded conditions. Chat-driven — the user describes what they want; the skill writes the grant file at `.agent-workflows/autonomous-grants/<name>.md` and updates the ledger. Invoked as /agent-pipeline-claude:grant-autonomous.
---

# Grant-autonomous

Follow the canonical workflow in `references/grant-autonomous.md`. That document is the single source of truth for the grant document shape, the chat-command parsing rules, the ledger format, the revoke/extend/delete procedures, and the safety hard rules.

Tool mapping for Claude Code:

- Use **Read** to inspect existing grant files and the ledger.
- Use **Write** for creating new grant files.
- Use **Edit** for revoke / extend / modify operations on existing grant files.
- Use **Bash** for `git status` if confirming working-tree state before grant creation.

`$ARGUMENTS` is the user's natural-language request after the slash command. The procedure parses the intent: create / revoke / extend / delete / status. The user does NOT write the YAML themselves — they describe what they want and Claude writes the file.

Hard rules:

- **Never create a grant without explicit user confirmation in chat.** Parse the intent, show a one-line summary (expires, gates, forbidden, rationale), wait for "yes" / "confirm" / "go" before writing.
- **Always include Forbidden-actions.** Even if the user doesn't mention them, the default forbidden set (admin-merge, tag push, release publish, force push, any high_risk action class) is always present.
- **Granted-by is always "Scott Converse" (or the configured project owner).** This is Scott's grant; the file records the human authorizer's name.
- **Expires-at is required and bounded.** Maximum 24 hours from Granted-at unless the user explicitly says "for the next week" or similar — and even then, ask for confirmation.
- **Always update the ledger.** Every grant action (create / revoke / extend / delete) appends a row to `.agent-workflows/autonomous-grants/ledger.md`.
- **Never delete a grant — rename to `.archived` instead.** Preserves audit trail.
- **Revoke is irreversible within the grant's original time window.** Once Revoked: true, the grant can be re-enabled only by creating a new grant.
