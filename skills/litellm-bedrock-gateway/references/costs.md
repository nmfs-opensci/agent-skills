# What it costs

**Provisional.** Measured in September 2026 from a few hours of individual use,
not from a workshop. Prices change: re-check with the Pricing API
(`models.md`) before quoting them.

## The server

About **$0.57 a day** while running (t4g.small, public IPv4, 20 GB disk) and
about **$5 a month** stopped (disk $1.60 plus the Elastic IP $3.60, which is
charged while the instance is stopped). Teardown stops all of it.

## Tokens: why a coding agent is not a chat

A coding agent resends its system prompt, tool definitions and the conversation
on every request. Claude Code sends about **34–53k tokens** before the user has
typed anything (more with many skills, MCP servers or a large `CLAUDE.md`; a
fresh install is nearer 30k). So:

- **Session start is a prompt-cache write** of that whole prefix: about
  **$0.13–0.22 on Sonnet 4.6**, about $0.26 on Opus 4.6.
- **Each later request mostly reads the cache**: about **$0.02 per Sonnet
  request**. One user prompt can make many requests.
- **The cache lives 5 minutes.** A longer pause pays the session start again.
- `/compact` does not help: the bulk is the fixed prefix, not the conversation.
- **Haiku 4.5 is about a third of Sonnet's price**; the open models are cheaper
  again per token but have no prompt caching through the gateway, so once a
  session is under way cached Haiku can cost about the same per request.

Measured: an interactive Claude Code session, "init and a few starter files",
cost $0.85 (29 requests, mostly Sonnet). Estimate for sustained Sonnet use:
**$3–8 per person-hour**.

## Advice for organizers

- Make a cheap model the default (the reference deployment chose Haiku 4.5) and
  let people switch up for hard problems.
- Size budgets to the session, not to "a few prompts": $2 is a few dozen turns
  of real work. The reference deployment settled on **$20 per person for a
  week**, without a daily allowance; whether that is enough is being measured.
- `--budget-duration 1d` gives a daily allowance if one person burning a week's
  budget on day one is a concern.
- Tell participants that pausing for more than five minutes costs a new session
  start, and that a lean setup (few MCP servers, a short `CLAUDE.md`) is cheaper.
- A flat-rate subscription (Claude Pro or Max) is not comparable: it is not
  metered per token, and the gateway's cost is Bedrock's on-demand price.
- Set an AWS Budget alarm on the account as a backstop; `inspect_account.py`
  reports whether one exists.
