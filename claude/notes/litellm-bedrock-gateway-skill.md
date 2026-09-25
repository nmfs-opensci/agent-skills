# litellm-bedrock-gateway skill: decisions and status

Built 2026-09-25 for issue #22, merged as PR #24 (squash). Adapted from the
working gateway in `nmfs-opensci/agent-coders-clinics` (clinics issue #1, which
was this repo's #20 before being transferred there).

## Decisions (Eli, 2026-09-25)

- **The skill ships its own copy** of the template and scripts, and is now the
  **source of truth**. The clinics repo should keep only its deployment-specific
  files (its own `gateway.env` / `models.yaml`-style settings), not a second copy
  of the scripts.
- **One model list, never three.** `models.yaml` feeds the IAM statement,
  LiteLLM's `model_list` and the participant quickstart, through `render.py`.
- **Organizers always create keys and send them privately.** Eli: "create key on
  machine that will use it" makes no sense; it is gone.
- **Admin UI exposure is the installer's choice** (`GATEWAY_ADMIN_UI=public|tunnel`).
- **Cover the other tools**: Claude Code, OpenCode, Copilot CLI (Aider dropped).
- **Build now**, with costs and the large-event runbook marked Provisional,
  rather than waiting for clinics issue #4 (real-work cost test). When #4
  reports, fold its numbers into `references/costs.md` and `operate.md`.
- Status Experimental; the classic/org-account path is Provisional until a real
  install outside the "new experience" account.

## Design choices that look odd but are deliberate

- **LiteLLM config and Caddyfile live in SSM Parameter Store**, not user data.
  User data runs once; `refresh.sh` on the instance re-reads the parameters and
  `deploy.sh` runs it over SSM. This is what removed config drift on the
  instance, and a model change never replaces the instance.
- **No Caddy block on `/key/info?key=`**, although Eli first agreed to one.
  Testing showed the leak (one key reading another's alias, spend and budget)
  happens only when **neither key has a `user_id`**, and also goes through
  `POST /v2/key/info`. The Caddy rule missed that route and broke the Admin UI,
  which calls `/key/info?key=` itself. The fix is `user_id` = name on every key
  (`keys.py`), checked by `check_gateway.py`. Tested on LiteLLM 1.102.1 only.
- **`render.py` refuses `global.` inference profiles**: their IAM shape differs
  and was never tested.
- Claude models use LiteLLM's own prices (it knows the cache rates); open models
  must carry prices in `models.yaml` or spend records $0.

## Testing

Everything was run in the throwaway stack `gwskill-test-delete-me` (Greenfield,
us-east-2), then torn down. `verify.md` lists what passed. **Not tested**: an
install in a classic/org account, changing `GATEWAY_DOMAIN` after the first
deploy, load beyond a handful of users. The evals have not been run.

Test pattern that worked: `scripts/init_deployment.sh <scratch dir>`, a venv
from `scripts/requirements.txt` only, `AWS_PROFILE=greenfield` and a distinct
`GATEWAY_STACK` in its `gateway.env`. Never test on `litellm-smoke`, the live
clinics gateway. `pkill -f session-manager-plugin` kills the calling shell (the
pattern matches its own command line); use `pkill -x session-manager`.

## Follow-ups outside this repo

- `agent-coders-clinics#8`: models listed in two places in its template, plus 12
  cleanup items from the review, and a correction on the key-isolation fix. The
  **live gateway's keys have no `user_id`**, so they can read each other's details
  if someone has a hash. That's low risk, since participants can't list hashes.
