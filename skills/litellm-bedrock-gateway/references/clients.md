# Connecting coding tools

The gateway answers the Anthropic Messages API (`/v1/messages`), the OpenAI Chat
Completions API (`/v1/chat/completions`) and the OpenAI Responses API
(`/v1/responses`). `build/participant-quickstart.md`, generated from
`assets/participant-quickstart.md` and `models.yaml`, holds the tested setup for
three tools. Keep one quickstart for all tools, with a shared first step that
sets `GATEWAY_KEY` and `GATEWAY_URL`, so every later block pastes unedited.

## Claude Code (tested)

- `ANTHROPIC_BASE_URL` = gateway URL; `ANTHROPIC_AUTH_TOKEN` = the LiteLLM key.
- `ANTHROPIC_MODEL` plus `ANTHROPIC_DEFAULT_{OPUS,SONNET,HAIKU}_MODEL`, each set
  to a served name. The **haiku tier must be set**: background calls use it and
  fail otherwise.
- Clear `CLAUDE_CODE_USE_BEDROCK`, `CLAUDE_CODE_USE_VERTEX` and
  `ANTHROPIC_API_KEY`: any of them sends Claude Code around the gateway, and the
  symptom is a key with no spend.
- No Claude login is needed.

## OpenCode (tested)

- A provider in `~/.config/opencode/opencode.json` using
  `@ai-sdk/openai-compatible`, `baseURL` = gateway `/v1`, `apiKey` =
  `{env:GATEWAY_KEY}` (the file holds no key).
- OpenCode knows only the models listed in the provider's `models` map
  ("Model not found" otherwise): `render.py` fills it from `models.yaml`.
- Set `small_model` too, or OpenCode falls back to its own hosted models.
- `opencode run` hangs in a non-interactive shell unless stdin is closed.

## GitHub Copilot CLI (tested)

- `COPILOT_PROVIDER_TYPE=openai`, `COPILOT_PROVIDER_BASE_URL` = gateway `/v1`,
  `COPILOT_PROVIDER_API_KEY` = the key, `COPILOT_MODEL` = a served name.
- **No GitHub login or Copilot subscription is needed** with these variables
  (checked from an empty home directory with no token).

## Prompt caching for OpenAI-style tools

Claude Code marks its own prompt-cache breakpoints. OpenCode and Copilot CLI
speak the OpenAI format and do not, so without help every request pays full
price for the same ~15–35k tokens of instructions. `cache: true` in
`models.yaml` makes LiteLLM add markers on the system message and the latest
message. LiteLLM stands down when the client already sets markers, so Claude
Code is unaffected. Measured on Haiku with Copilot CLI: the first request of a
session writes the cache (~17k tokens, about $0.025), later requests read it
(about $0.002, down from $0.02). Two Copilot sessions seconds apart did not share
a cache, so each session pays one write.

## Other tools

Anything that speaks one of the three APIs should work, but only the three above
have been tested. Test a new tool with the file-reading task in `verify.md`
before recommending it. Aider was tried in the reference deployment and dropped
before it was tested; if revisited, `--model openai/<served name>` with
`OPENAI_API_BASE` and `OPENAI_API_KEY` is the expected shape.

## Troubleshooting participants

| Symptom | Cause |
|---|---|
| 401 / authentication error | key missing or incomplete in this terminal |
| 429 "Budget has been exceeded" | the key's budget is used up (`keys.py update`) |
| key expired or blocked | `keys.py list` shows which |
| connection refused / timeout | the instance is stopped (`instance.sh start`) |
| tool works but the key shows no spend | the tool bypassed the gateway: an old setting such as `CLAUDE_CODE_USE_BEDROCK` |
| an open model answers without reading files | it skipped the tool; ask it to "use the read tool", or switch model |
