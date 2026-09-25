# Using coding tools through the gateway

This gateway lets you use AI coding tools with Claude and open coding models on
Amazon Bedrock, without an AWS account or an AI subscription. It has been tested
with Claude Code, OpenCode and GitHub Copilot CLI.

## 1. Basics (everyone)

You need two things from the organizer:

- the **gateway URL**: `{{GATEWAY_URL}}`
- a **personal key** (starts with `sk-`), sent to you privately. Keep it to
  yourself: it has its own spending limit and expiry date, and use is recorded
  against it.

In a terminal, run these two lines, pasting your key in place of
`sk-your-key-here`:

```bash
export GATEWAY_KEY=sk-your-key-here
export GATEWAY_URL={{GATEWAY_URL}}
```

The commands below use these two settings. They last only for this terminal:
in a new terminal, run both lines again.

## 2. Pick your coding tool

You only need the section for the tool you use:

- [Claude Code](#claude-code): Anthropic's coding tool, built for Claude.
- [OpenCode](#opencode): open source, works with Claude and open models.
- [GitHub Copilot CLI](#github-copilot-cli): GitHub's coding tool; no GitHub
  account or Copilot subscription needed with the gateway.

## Claude Code

**Install** (skip if you have it), on macOS, Linux or WSL:

```bash
curl -fsSL https://claude.ai/install.sh | bash
```

Other options (Homebrew, Windows) are at
<https://code.claude.com/docs/en/setup>. You do not need to log in to Claude.

**Connect** to the gateway, in the terminal where you set `GATEWAY_KEY`:

```bash
export ANTHROPIC_BASE_URL=$GATEWAY_URL
export ANTHROPIC_AUTH_TOKEN=$GATEWAY_KEY
{{CLAUDE_CODE_EXPORTS}}
```

If you normally use Claude Code another way (Bedrock, Vertex, or an Anthropic
API key), also clear those settings in this terminal so they do not override
the gateway:

```bash
unset CLAUDE_CODE_USE_BEDROCK CLAUDE_CODE_USE_VERTEX ANTHROPIC_API_KEY
```

**Start** with `claude`. Type `/status` inside Claude Code: it should show the
gateway URL. `/model` switches models, for example `/model {{DEFAULT_MODEL}}`.
`/usage` shows what this session has used.

## OpenCode

**Install** (skip if you have it). With Node.js:

```bash
npm install -g opencode-ai
```

Other options (Homebrew, install script, Windows) are at
<https://opencode.ai/docs/>. You do not need an OpenCode account.

**Connect** to the gateway by writing OpenCode's settings file. This replaces
any `~/.config/opencode/opencode.json` you already have, so if you have one,
save a copy first.

```bash
mkdir -p ~/.config/opencode
cat > ~/.config/opencode/opencode.json <<EOF
{
  "\$schema": "https://opencode.ai/config.json",
  "model": "gateway/{{DEFAULT_MODEL}}",
  "small_model": "gateway/{{DEFAULT_MODEL}}",
  "provider": {
    "gateway": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Workshop gateway",
      "options": {
        "baseURL": "$GATEWAY_URL/v1",
        "apiKey": "{env:GATEWAY_KEY}"
      },
      "models": {{OPENCODE_MODELS}}
    }
  }
}
EOF
```

The file holds the gateway URL but not your key: OpenCode reads the key from
`GATEWAY_KEY`, so set it in each new terminal before starting OpenCode.

**Start** with `opencode`. `/models` switches models; the gateway's are listed
under "Workshop gateway".

## GitHub Copilot CLI

**Install** (skip if you have it), on macOS or Linux:

```bash
curl -fsSL https://gh.io/copilot-install | bash
```

Other options (Homebrew, npm, Windows) are at
<https://docs.github.com/copilot/how-tos/copilot-cli>. With the gateway you do
not need to log in to GitHub.

**Connect** to the gateway, in the terminal where you set `GATEWAY_KEY`:

```bash
export COPILOT_PROVIDER_TYPE=openai
export COPILOT_PROVIDER_BASE_URL=$GATEWAY_URL/v1
export COPILOT_PROVIDER_API_KEY=$GATEWAY_KEY
export COPILOT_MODEL={{DEFAULT_MODEL}}
```

**Start** with `copilot`. To use another model, quit, change `COPILOT_MODEL`
to any name from the [model table](#4-models), and start again.

## 3. How much budget is left

Run this in a terminal where `GATEWAY_URL` and `GATEWAY_KEY` are set:

```bash
curl -s $GATEWAY_URL/key/info -H "Authorization: Bearer $GATEWAY_KEY" |
  python3 -c "import sys, json; i = json.load(sys.stdin)['info']
print(f\"Spent \${i['spend']:.2f} of \${i['max_budget']:.2f}; expires {i['expires'][:10]}\")"
```

Spending shows up about a minute after each request.

## 4. Models

The default is **{{DEFAULT_LABEL}}**. For harder problems switch to a stronger
model, and back again.

| Name | Model | Cost, relative to the default |
|---|---|---|
{{MODEL_TABLE}}

Costs compare the price of input tokens, which is most of what a coding tool
sends. The gateway caches the repeated part of each request for Claude models
but not for the open models, so once a session is under way a Claude model can
cost less per request than this table suggests.

Open models use a coding tool's file-reading and editing tools less reliably
than Claude. If one answers without looking at your files, ask it explicitly,
for example "use the read tool on notes.txt".

### Why requests cost what they do

Every request resends the coding tool's instructions and your conversation,
about 15,000–60,000 tokens. On Claude the gateway caches the repeated part for
five minutes, so the first request of a session costs the most and later ones
much less. A pause of more than five minutes pays that first cost again.

## 5. Troubleshooting

- **Budget exceeded**: your key has used its spending limit. Ask the organizer.
- **Key expired / blocked**: the key's time is up or it was switched off.
- **Authentication error**: `GATEWAY_KEY` is wrong or incomplete; set it again.
- **Connection refused / timeout**: the gateway server is stopped. Ask the
  organizer.
- **No spend on your key after using a tool**: the tool bypassed the gateway,
  usually because an older setting (such as `CLAUDE_CODE_USE_BEDROCK`) is still
  set. For Claude Code, `/status` should show the gateway URL.
