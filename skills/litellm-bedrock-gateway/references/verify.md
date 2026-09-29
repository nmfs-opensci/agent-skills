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
`GATEWAY_ADMIN_UI` says; the workshop key service answers and its admin
route refuses no key and a participant key; every served model answers a tool-use request in both
the OpenAI format (OpenCode, Copilot CLI) and the Anthropic format (Claude
Code); and, after LiteLLM's ~1 minute write delay, each model's calls were
recorded at more than $0. Cost: a few cents.

A model that fails here fails for participants. A $0 spend means its budget
does nothing: set its price in `models.yaml` (`models.md`).

## 2. A real coding tool

Use the commands in `docs/participant-quickstart.md` exactly as written, in a
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

## What was verified for workshop sign-up (2026-09-28)

In a throwaway stack in us-east-2, deployed from scratch with the scripts as
shipped: `check_gateway.py --other --spend` passed all 41 checks, including
that the key service answers and refuses its admin route without the master
key. With AWS credentials disabled and only `secrets/gateway-url` and
`secrets/master-key`, `workshop.py` opened sign-up and `keys.py` listed keys.
The rendered hub script, run from a shared folder in an empty home with
`CLAUDE_CODE_USE_BEDROCK` and a bogus `ANTHROPIC_API_KEY` set, signed up
(`ws-<user>`, with a `user_id`) and the real Claude Code read a file through
the gateway; its spend showed on that key and in `--budget`. A repeat sign-up
got 409. A second `deploy.sh` refreshed the instance: the key service restarted
with the stored code and kept its sign-up state. Teardown left nothing behind.
Tested locally against a stub: wrong code, the key cap, and a missing `.url`
file. Not tested: an interactive first start on a real hub account.

## What was verified for organizer keys and named workshops (2026-09-28)

In a throwaway stack in us-east-2, rebuilt from scratch with the scripts as
shipped (issue #27). Probes first: a `proxy_admin` key listed, created,
updated, blocked, unblocked and deleted keys, including the master key's; it
could not log in to the Admin UI, add models, or regenerate keys; it could
create more admins and call `/config/update`; blocked or deleted, it got 401
at once. Then the scripts: `keys.py organizer create` made two organizers.
Each, in its own folder with every AWS credential source disabled (instance
metadata included), opened its own workshop; a second workshop with an open
workshop's code got 409, a bad name 400. Sign-up: codes case-insensitive, the
cap held per workshop, a repeat got 409, a wrong code and an admin call with a
bogus or participant key each took ~1.2 s to refuse, and the same person got a
key in each of two workshops. The rendered hub script signed a participant up
(`ws-orca-gina`, message naming the workshop) and the real Claude Code answered
through the gateway; `workshop.py status --workshop orca` showed its spend.
An organizer blocked and deleted keys. `organizer revoke` stopped that
organizer's key at once (key service 404, LiteLLM 401) while the other's kept
working, and listed an admin the other had made directly, flagged.
`check_gateway.py --other --spend` passed 42 of 42. `instance.sh refresh`
decoded the gzipped key service and kept both workshops' state. Teardown
left nothing behind (stack, parameters, Elastic IP).

## What was verified for key batches and issuer keys (2026-09-29)

In a throwaway stack in us-east-2, deployed from scratch with the scripts as
shipped (issue #33). `keys.py issuer create` (and its alias `organizer
create`) made `iss-` admins; `issuer list` showed a hand-made `org-` admin as
made by the script, and `issuer revoke` removed it by its short name. In an
issuer's folder with every AWS credential source disabled, only
`secrets/gateway-url` and `secrets/issuer-key`: `keys.py batch` made three
keys, then two more numbered on (`ws-whale-04`, `-05`), all in one mode-600
file and none on the terminal; a bad name was refused; `workshop.py status`
listed the batch-only workshop; `plan --batch` wrote its record; the old name
`secrets/organizer-key` still worked. The rendered hub script, from a shared
folder in empty homes with `CLAUDE_CODE_USE_BEDROCK` and a bogus
`ANTHROPIC_API_KEY` set: a wrong pasted key was refused and not saved; a batch
key pasted with spaces around it was trimmed, saved mode 600, and the real
Claude Code answered through the gateway ($0.04 recorded on the key). After
the issuer blocked one key and deleted another, the organizer's `--status`
showed both as not accepted and the rest with spend. Sign-up with a code still
worked on the same workshop, and batch keys, the blocked one included, counted
against its cap. No key value appeared in any output. Not tested: an
interactive first start on a real hub account, a batch file sent over Slack.
