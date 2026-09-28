# Keys, budgets and watching spend

## Keys

Organizers create every key and send it to its owner **privately**: a direct
message, never a shared channel, email list or document. Keys are per person;
use is recorded against each one, so a shared key hides who spent what and lets
one person exhaust another's budget.

```bash
python scripts/keys.py create alice bob carol --budget 20 --days 7 --note "June clinic"
python scripts/keys.py create dana --budget 5 --days 2 --models claude-haiku-4-5-20251001
python scripts/keys.py create erin --budget 3 --days 5 --budget-duration 1d   # $3 a day
```

- `--budget` (USD) and `--days` (expiry) are required: decide them per event
  with the organizer (`costs.md`).
- `--models` limits a key to named models; without it the key may use every
  served model, including any added later.
- `--budget-duration` resets the budget on a schedule (a daily allowance).
- Each key's value is written only to `secrets/<name>.key` (mode 600,
  git-ignored) and never printed. The organizer copies it from there into the
  private message. If the file is opened in JupyterLab, JupyterLab keeps a copy
  under `secrets/.ipynb_checkpoints/`; `keys.py delete` and `teardown.sh` remove
  those too.
- Every key gets `user_id` = its name. This is a security setting, not
  bookkeeping: LiteLLM lets a key read another key's details when neither has a
  `user_id` (`security.md`).

Send participants `docs/participant-quickstart.md` (written by `render.py`)
and, in the same private message, the gateway URL from `secrets/gateway-url`.

On a JupyterHub, participants can get their own keys instead:
`workshop.py open` and the hub script (`workshop-signup.md`). Those keys are
named `ws-<workshop>-<hub username>`; `workshop.py status --workshop <name>`
lists one workshop's, and `keys.py` lists, blocks and deletes them like any
other. Deleting one lets that person sign up again.

An organizer without AWS access runs every command here from
`secrets/gateway-url` and their own organizer key in `secrets/organizer-key`,
made by the installer with `keys.py organizer create` (`workshop-signup.md`).

## Changing, pausing, removing

```bash
python scripts/keys.py update alice --budget 30        # new total budget
python scripts/keys.py update alice --days 3           # expires 3 days from now
python scripts/keys.py block alice                     # refuse requests, keep the key
python scripts/keys.py unblock alice
python scripts/keys.py delete alice                    # gone, with its local file
```

## Watching spend

```bash
python scripts/keys.py list
```

prints each key's spend, budget, expiry and whether it is blocked. The Admin UI
(`/ui`, or through the tunnel) shows the same with per-model and per-day
breakdowns.

- **Spend appears about a minute late**: LiteLLM writes it to Postgres in
  batches.
- **A budget is checked before each request**, so one request can overshoot a
  small budget slightly. Exceeding returns HTTP 429 "Budget has been exceeded".
- For per-request detail (tokens, cache reads), `GET /spend/logs` with an
  admin key and no date parameters returns rows; with dates it returns daily
  totals only.

## What participants can see

A participant checks their own balance with `GET /key/info` and their key
(the curl line is in the quickstart). Claude Code's `/usage` matched LiteLLM's
recorded spend in testing.
