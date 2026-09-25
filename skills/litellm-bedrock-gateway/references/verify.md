# Verifying by running

"The stack deployed" and "the template looks right" are not verification. A
gateway is verified when a real coding tool has worked through it over HTTPS
with a participant-style key and the spend showed up on that key. Report what
each step printed.

## 1. From the outside, every model

```bash
python scripts/keys.py create gateway-check --budget 1 --days 1 --note verification
python scripts/keys.py create gateway-check-2 --budget 1 --days 1 --note verification
python scripts/check_gateway.py gateway-check --other gateway-check-2 --spend
```

It checks, over HTTPS: no key → 401; the key reads its own balance and has a
`user_id`; it cannot read the other key's details (403 on `/key/info?key=`,
empty on `/v2/key/info`); the Admin UI is reachable or blocked as
`GATEWAY_ADMIN_UI` says; every served model answers a tool-use request in both
the OpenAI format (OpenCode, Copilot CLI) and the Anthropic format (Claude
Code); and, after LiteLLM's ~1 minute write delay, each model's calls were
recorded at more than $0. Cost: a few cents.

A model that fails here fails for participants. A $0 spend means its budget
does nothing: set its price in `models.yaml` (`models.md`).

## 2. A real coding tool

Use the commands in `build/participant-quickstart.md` exactly as written, in a
fresh shell with no other AI settings (an empty `HOME` is the honest test). A
file-reading task shows that tool calls work end to end:

```bash
echo "the secret number is 4817" > notes.txt
claude -p "Read notes.txt and reply with only the secret number." --allowedTools Read
opencode run "Read notes.txt and reply with only the secret number." </dev/null
copilot -p "Read notes.txt and reply with only the secret number." --allow-all-tools
```

`opencode run` hangs in a non-interactive shell unless stdin is closed
(`</dev/null`). Claude Code's `/status` should show the gateway URL.

## 3. Spend on the key

About a minute later, `python scripts/keys.py list` should show the test key's
spend risen. If it did not, the tool went around the gateway (see the
troubleshooting list in `clients.md`).

## 4. A budget stops a key

Optional, but it is the feature the gateway exists for:

```bash
python scripts/keys.py create tiny --budget 0.0001 --days 1
```

After one request and the write delay, further requests return HTTP 429
"Budget has been exceeded".

## Clean up

Delete the test keys (`keys.py delete <name>`) before the event. When testing a
change to the template or scripts, do it in a separately named stack
(`GATEWAY_STACK` in a copy of the deployment folder), never on the gateway
people are using, and tear it down afterwards.

## What was verified for this skill (2026-09-25)

In a throwaway stack in us-east-2, with the scripts as shipped: deploy from
scratch; `check_gateway.py --spend` passed every check across 11 models (37 at
the time; the key-isolation checks were added afterwards and passed separately); Claude Code,
OpenCode and Copilot CLI each read a file through the gateway from an empty
`HOME` using the rendered quickstart; a model removed from `models.yaml`
disappeared from both the IAM role and the gateway after `deploy.sh` with no
manual step; `tunnel` mode blocked `/ui` and the login routes over HTTPS while
the UI worked through the tunnel; key isolation (below) held; a $0.0001 budget
returned 429; stop/start kept the URL, keys and spend; teardown left nothing
behind.
