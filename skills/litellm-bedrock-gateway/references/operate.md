# Running it, scaling it, finishing

## Day to day

```bash
scripts/instance.sh status | stop | start | health | refresh
```

- **Stop between sessions** to pay about $5 a month instead of $0.57 a day.
  Keys, budgets and spend live on the instance's disk and survive; the Elastic IP
  keeps the URL. After `start`, the gateway answered again in about 30 seconds in
  testing.
- `health` asks LiteLLM on the instance whether it is ready (over SSM).
- `refresh` reloads the config from Parameter Store; `deploy.sh` runs it for you.

## A larger event (Provisional)

Not yet measured: one t4g.small has served a handful of people at once, never
twenty. Before a large event:

- **Quotas are the likelier limit than the server.** Compare each model's
  tokens-per-minute quota (`inspect_account.py`) with the load: every active
  Claude Code user sends 30–50k tokens per request, several requests a minute.
  Twenty people at once can need millions of tokens per minute. Request
  increases days ahead.
- **Load-test with the real tool**: several people (or scripted sessions)
  running Claude Code at once while watching `instance.sh health` and response
  times.
- **If the instance struggles**, set `InstanceType` to a larger arm64 type
  (`t4g.medium`, `t4g.large`) with `--parameter-overrides` and redeploy; a type
  change restarts the instance.
- **A bigger architecture** (ECS with a load balancer and a managed database)
  was considered and rejected for this scale: about $50–80 a month idle, and no
  evidence yet that a single instance is inadequate. Revisit only with such
  evidence.
- **Keys in bulk**: `keys.py create` takes many names at once. Send each key
  privately, with `build/participant-quickstart.md`.

## Finishing

1. Save what you want to keep: `python scripts/keys.py list > usage.txt`, or
   export from the Admin UI.
2. `scripts/teardown.sh` (type the stack name to confirm). It deletes the stack
   (network, instance, disk, role, Elastic IP), the Parameter Store entries, and
   `secrets/` and `build/`. All keys and spend history are gone.
3. Check nothing is left: `aws cloudformation list-stacks`, and no parameters
   under `/<stack>/`.

A rebuilt stack gets a new Elastic IP, so an `sslip.io` URL changes; a domain
name only needs its A record updated.
