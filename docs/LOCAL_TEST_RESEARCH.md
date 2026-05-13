# Local-LLM test-harness research

Investigation log from 2026-05-12. The motivating directive: prefer local
LLM execution over Anthropic-API spend whenever possible, including for
the cleanroom-smoke test that drives `claude -p` against a real model.

This doc exists so the next person (or future-self) doesn't repeat the
90 minutes of exploration that produced its conclusion.

## TL;DR

**Tier A (route `claude -p` through a local-model proxy):** technically
possible for trivial single-turn requests. Hits three walls on
multi-turn tool-use flows like cleanroom-smoke. Not test-ready at
2026-05-12. Revisit when the walls below are removed.

**Tier C (unit-test the deterministic scaffold step directly):** ✔
shipped in v1.1.2 as `tests/test_scaffold_pipeline.py`. $0,
sub-second, covers the same load-bearing assertions cleanroom-smoke
makes about the produced `.pipelines/` tree.

**Cleanroom-smoke remains opt-in for API-key holders** as the
gold-standard end-to-end proof.

## What worked

Single-turn Anthropic-shape request → `claude-code-router` (npm
package `@musistudio/claude-code-router`) → Ollama OpenAI-compatible
endpoint → response back in Anthropic shape: ✔ verified end-to-end.

Built-in `Bash` tool through the same stack with `gpt-oss:20b`: ✔
model emitted a valid `tool_use` block, claude CLI executed the Bash
call, the model received the tool result and reported correctly.

Working `~/.claude-code-router/config.json` for the trivial path:

```json
{
  "LOG": true,
  "HOST": "127.0.0.1",
  "PORT": 3456,
  "APIKEY": "local-dev",
  "Providers": [
    {
      "name": "ollama",
      "api_base_url": "http://localhost:11434/v1/chat/completions",
      "api_key": "ollama",
      "models": ["gpt-oss:20b"],
      "transformer": { "use": ["cleancache"] }
    }
  ],
  "Router": {
    "default": "ollama,gpt-oss:20b",
    "background": "ollama,gpt-oss:20b",
    "think": "ollama,gpt-oss:20b",
    "longContext": "ollama,gpt-oss:20b"
  }
}
```

Invocation:

```bash
ccr start
ANTHROPIC_BASE_URL=http://127.0.0.1:3456 \
ANTHROPIC_API_KEY=local-dev \
claude -p --model haiku 'Use the Bash tool to run: echo OK'
```

## Three walls hit when scaling to cleanroom-smoke

### Wall 1 — `thinking` field rejection

Claude haiku 4.5 always sends an extended-thinking parameter in the
request. `claude-code-router`'s OpenAI transformer forwards it. Ollama
validates it against the target model's capabilities. `qwen3-coder:30b`
rejects with `400 "qwen3-coder:30b" does not support thinking`. Tried
`--bare`, `--model claude-haiku-3-5`, multiple transformer combos
(`cleancache`, `tooluse`, per-model `use: []`) — none stripped the
field at the proxy layer.

**Workaround:** route to a model that accepts the field gracefully.
`gpt-oss:20b` does. `qwen3-coder:30b` does not. This narrows model
choice; the OpenAI-trained open-weights line is the safe pick.

### Wall 2 — small models loop instead of emitting `tool_use`

First test inadvertently routed `--model haiku` to the `background`
tier (configured as `gemma4:e4b`, 4B). Model emitted
`reasoning: " tool"` chunks in an infinite loop without ever producing
a structured tool call. 32 minutes wall, 0 progress before the
subprocess timeout fired across multiple reader-thread joins.

**Workaround:** route every tier (`default`, `background`, `think`,
`longContext`) to the same tool-use-capable model. Don't rely on
ccr's tier-aware routing when tool fidelity matters.

### Wall 3 — `ERR_STREAM_PREMATURE_CLOSE` on multi-turn flows

Even with `gpt-oss:20b` doing the heavy lifting and routing fixed,
the full cleanroom-smoke flow (two-turn `claude -p`: invoke the
`pipeline-init` Skill, then `APPROVE`) produces repeated
`ERR_STREAM_PREMATURE_CLOSE` errors at the ccr layer. Within a single
test run the ccr log accumulated 25 stream-close errors before the
test was halted. Claude CLI drops the SSE stream and ccr can't keep
the response transformer alive across multi-turn tool-use loops.

This is the real blocker. Fixing it means patching ccr's streaming
response forwarder — real engineering work, brittle against ongoing
`claude` CLI evolution.

## Conditions under which to revisit Tier A

1. `claude-code-router` (or a successor) ships SSE forwarding that
   survives multi-turn tool-use flows without dropping streams.
2. An Anthropic-compatible local inference server (a `vllm`-style
   process that natively speaks `/v1/messages` and `tool_use`)
   becomes available — eliminates the translation layer entirely.
3. Claude CLI grows native OpenAI-compatible provider support (today
   the help text only advertises Bedrock/Vertex/Foundry alongside
   the direct Anthropic API).

Until at least one of those lands, the cost-floor for a real
end-to-end "drive Skill from a model" test is ~$0.05/run on Haiku.
`test_scaffold_pipeline.py` covers the *deterministic* part of that
test at $0; the model-judgment part stays in cleanroom-smoke as an
opt-in.

## Why this is OK

The failure class cleanroom-smoke was built to catch — "plugin loads
but skills no-op / scaffold to the wrong path" — splits into two
sub-classes:

1. **The scaffold operation itself is broken** (wrong file list,
   missed payload, broken copy). v1.1.2's
   `test_scaffold_pipeline.py` catches this at $0.
2. **The LLM/CLI fails to invoke the skill correctly** (skill
   markdown is unreadable, Skill-tool dispatch broken, claude CLI
   silently swallows the call). This still requires a real model;
   cleanroom-smoke remains the test that catches it for API-key
   holders. `claude plugin list ✔ enabled` + manual Cowork-app
   verification cover it for everyone else.

Splitting coverage along that boundary keeps day-to-day CI free
without losing the gold-standard verification path.
