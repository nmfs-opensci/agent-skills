---
name: litellm-bedrock-gateway
description: Set up, verify, run, and tear down a LiteLLM gateway on AWS that lets workshop or clinic participants use coding agents (Claude Code, OpenCode, GitHub Copilot CLI) with Amazon Bedrock models through personal virtual keys with their own budgets and expiry dates, without handing out AWS credentials. Use when asked to give a group access to Claude or other Bedrock models from coding tools, to deploy or update LiteLLM in front of Bedrock, to get an AWS account ready for Bedrock (Anthropic use-case form, Marketplace subscription, quotas, payment method), to diagnose why Bedrock refuses a model, to create, limit, block, or monitor participants' keys, to estimate what a coding-agent workshop will cost, or to stop or remove the gateway afterwards.
---

# LiteLLM gateway to Amazon Bedrock

The pattern is **coding tool → LiteLLM proxy → Amazon Bedrock**. Each participant
gets a LiteLLM virtual key with its own budget, expiry and usage record. The only
AWS credential is an IAM role on the server, limited to the models served. One
CloudFormation stack builds it: a single EC2 instance running LiteLLM, Postgres
and Caddy (HTTPS) in Docker. It costs about $0.57 a day running and about $5 a
month stopped, and one command removes it.

**Status: Experimental.** One deployment has been built and tested with this
template, in an AWS "new experience" account turned into an Organization
(September 2026). The ordinary case, a classic or organization account where
the installer has an IAM role or IAM Identity Center access, has not been
installed yet: treat those steps as **Provisional** and tell the user so. Costs
and the large-workshop runbook are Provisional too; they come from a few hours
of use, not from a real workshop. Model IDs, prices and versions change: check
`references/version-matrix.md` and verify in the account rather than trusting
this text.

## What this skill ships

Everything needed lives in the skill, so an installer never depends on another
repository:

- `assets/models.yaml` — **the one list of served models.** `scripts/render.py`
  generates from it the instance role's IAM statement, LiteLLM's `model_list`
  and the participants' model table. Never maintain a second list.
- `assets/gateway-template.yaml` — the CloudFormation source (rendered, never
  deployed directly).
- `assets/participant-quickstart.md` — participant instructions, filled in by
  `render.py`.
- `scripts/` — `init_deployment.sh`, `inspect_account.py`, `check_bedrock.py`,
  `deploy.sh`, `keys.py`, `check_gateway.py`, `instance.sh`, `tunnel.sh`,
  `teardown.sh`.

Start every install with `scripts/init_deployment.sh <folder>`, which copies
these into a **deployment folder** holding that gateway's `gateway.env` and
`models.yaml`. All commands then run from that folder after
`source gateway.env`. The copy is deliberate: a running gateway must not change
because the skill changed.

## The order of work

Each step gates the next. Stop and ask before anything that creates billed
resources.

1. **Ask the installer**: which AWS account, and what kind (classic,
   organization member, or "new experience"); Region; domain name or
   `sslip.io`; whether the Admin UI is public or only through the tunnel;
   which models; how many people, for how long, and the budget per person.
2. **Sign in without long-lived keys** — `references/aws-access.md`. Clear any
   credentials the environment injects (JupyterHub roles, Bedrock API keys)
   before anything else, or every later command silently uses the wrong
   account. For "new experience" accounts see
   `references/new-experience-accounts.md`.
3. **Inspect, read-only** — `python scripts/inspect_account.py`. Identity,
   Organization and SCPs, whether the models in `models.yaml` exist in this
   Region, token quotas, existing resources, budgets.
4. **Make Bedrock answer** — `references/bedrock-readiness.md` and
   `python scripts/check_bedrock.py`. The per-account checklist (payment
   method, Anthropic use-case form, Marketplace subscription, verification
   hold, quotas) cost two days the first time. Do not deploy until every model
   passes.
5. **Choose models** — `references/models.md`. Edit `models.yaml` only.
6. **Deploy** — `references/deploy.md`. Show the installer the resources and
   costs first; `scripts/deploy.sh` after they agree.
7. **Verify by running** — `references/verify.md`. `check_gateway.py` over
   HTTPS, then a real coding tool with a test key, then spend recorded on the
   key. Report what ran, not what should work.
8. **Hand out keys and watch spend** — `references/keys-and-monitoring.md` and
   `references/clients.md`. Organizers create every key and send it privately.
9. **Operate and finish** — `references/operate.md`: scaling, stopping between
   sessions, teardown.

Costs to tell organizers before they choose budgets: `references/costs.md`.
Security choices and the reasons behind them: `references/security.md`.

## Non-negotiables

- **No AWS credentials for participants, and none written to disk by you.**
  Sign in with `aws login`, IAM Identity Center or an assumed role. Never
  create IAM access keys, and never make a long-term Bedrock API key (it
  silently creates an IAM user).
- **Never print a secret.** The master key, database password, salt key, UI
  password and participant keys stay in Parameter Store or in
  `secrets/<name>.key` (mode 600, git-ignored). Check health through
  `scripts/instance.sh health`, not by reading container logs, which can
  contain the database URL.
- **Organizers create every key and send it privately** (a direct message,
  never a shared channel or list). Keys are per person: never share one.
- **One list of models.** Change `models.yaml`, then `scripts/deploy.sh`. It
  updates the IAM role and reloads the running instance; never edit the config
  on the instance by hand.
- **Every served model needs a price LiteLLM knows**, or its spend records as
  $0 and budgets do nothing. `check_gateway.py --spend` catches this.
- **Verify model IDs in the account.** They are not guessable and differ by
  Region.
- **Ask before creating anything billed**, and before deleting anything.
  Teardown destroys every key and all spend history.
- **Never test against a gateway people are using.** Deploy a separately named
  stack (its own `GATEWAY_STACK`) and tear it down afterwards.

## Known traps

- **Claude works on day one and fails later.** A new account can answer Claude
  before the Anthropic use-case form is enforced. Re-run `check_bedrock.py`
  shortly before the event.
- **If a non-Anthropic model fails too, the problem is the account** (payment
  method, a hold, verification), not the Anthropic form.
- **The server role cannot finish the Marketplace subscription.** Make one call
  per Claude model as an administrator first (`check_bedrock.py` does).
- **Claude Code needs its haiku tier mapped** to a served model, or its
  background calls fail. `render.py` requires it.
- **Old settings route tools around the gateway**, most often
  `CLAUDE_CODE_USE_BEDROCK` or `ANTHROPIC_API_KEY`. The sign is a key with no
  spend after use.
- **Spend appears about a minute late**, and a budget is checked before each
  request, so one request can overshoot a small budget slightly.
- **The `sslip.io` URL changes if the stack is rebuilt** (new Elastic IP). Use a
  domain name for anything long-lived.
