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

## Workshop sign-up and organizer without AWS (issue #25, 2026-09-28)

Task A of three from the clinics repo (`agent-coders-clinics`
`claude/notes/gateway-skill-tasks.md`): B is a sparse template repo
`nmfs-opensci/litellm-bedrock-gateway`, C the colleague's org-install
instructions. Eli's decisions:

- **The key service is always deployed**, closed until `workshop.py open`. No
  on/off setting.
- **Install repos are usually public, so no committed file holds the gateway
  URL.** Docs go in `docs/` and the hub script in `hub/`, both committed;
  the URL is in `secrets/gateway-url`. The hub script reads it from
  `<command>.url` copied beside it on the hub. (Eli's idea: "all in docs/ but
  the URL in secrets/".)
- **`CLAUDE_CODE_AUTO_MODE_SERVER=0`** goes in the hub script and in the
  participant quickstart. Provisional: Claude Code calls the variable
  temporary.
- The master key file is `secrets/master-key`, not `master.key`: participant
  keys are `secrets/<name>.key`, so a key named "master" would collide.
- Rotating the master key is not worked out (env files are written at first
  boot only); the skill says so rather than guessing.

Verified in `gwskill-test-delete-me` (Greenfield) and torn down; details in the
skill's `references/verify.md`.

## Organizer keys and named workshops (issue #27 → PR #28, merged 2026-09-28)

Order agreed with Eli: A (#25) → #27 → B (template repo) → C (colleague's
instructions). #27 had to come before C, because C tells the installer what to
send the organizer. B does not depend on #27.

Settled by running on LiteLLM 1.102.1 before building: a `proxy_admin` key
manages every key (including the master key's) and is refused at once when
blocked or deleted; it **cannot** log in to the Admin UI; it **can** create more
admins and call `/config/update`, and revoking it undoes neither. So the
master-key-rotation fallback was not needed.

Eli's decisions:

- **No Admin UI password for an organizer without AWS**: it is as unrevocable
  as the master key. The CLI covers what they need (Eli asked specifically that
  they can see who has keys in their workshop and revoke them).
- **Several workshops at once on one gateway** (Eli: "there could be multiple
  workshops going on"), built into #27 rather than a separate issue: named
  workshops, own code/cap/budget/expiry, keys `ws-<workshop>-<user>`. Every
  admin key can still touch every workshop; the tools filter. True per-organizer
  isolation (LiteLLM teams) was offered and not chosen.
- **Key service asks LiteLLM on every admin request**, no cache, so revocation
  is immediate.
- **Revoke = delete key and user, then list every admin**, flagging ones not
  made by `organizer create`. Config changes are documented as undetected.
- **`secrets/organizer-key`, else the SSM master key.** `secrets/master-key` is
  no longer read, so no doc tells anyone to put the master key in a file.

Looks odd but is deliberate:

- The key service is stored **gzipped and base64** in Parameter Store: with
  named workshops it passed the 8 KB limit of Advanced parameters. `refresh.sh`
  is written by user data, so a gateway built before this change cannot decode
  it and needs a rebuild. Only throwaway stacks existed then.
- Workshop names have **no hyphen**, so `ws-<workshop>-<user>` parses one way.
- `organizer` subcommands always use the SSM master key, never an organizer
  key, although an organizer key could technically create admins too.
- LiteLLM's built-in `default_user_id` is a `proxy_admin` (appears after an
  Admin UI login); `organizer list` labels it and it must never be revoked.

Still open: rotating the master key itself (now less urgent); whether
`CLAUDE_CODE_AUTO_MODE_SERVER` survives Claude Code updates.

Test stack pattern that worked on 2026-09-28: `init_deployment.sh` into the
scratchpad, a fresh venv (a moved venv breaks), `AWS_PROFILE=greenfield`,
`GATEWAY_STACK=gwskill-test-delete-me`, a distinct `GATEWAY_HUB_COMMAND`. The key
service answers before LiteLLM on first boot, so `instance.sh health` can fail
once with curl exit 52; retry. A fake hub participant is
`env -i HOME=<empty dir> PATH=~/.local/bin:/usr/bin:/bin JUPYTERHUB_USER=<name>
bash <shared>/<command>`, with the code on stdin.

To test "no AWS access" on the hub, unsetting the profile is not enough: the
hub node's instance role still answers through instance metadata. Also set
`AWS_EC2_METADATA_DISABLED=true AWS_CONFIG_FILE=/nonexistent
AWS_SHARED_CREDENTIALS_FILE=/nonexistent`, and confirm `aws sts
get-caller-identity` fails. A foreground `sleep` is blocked in this harness;
wait with an `until` loop on a real condition.

## Gateway setup vs. adding a workshop (issue #29 → PR #32, merged 2026-09-29)

One gateway serves many workshops, so the skill now sets up the gateway once
(steps 1–8) and adds workshops as a repeatable step 9
(`references/add-a-workshop.md`). Eli's decisions:

- **Per-workshop values are not in `gateway.env`.** `GATEWAY_WORKSHOP_BUDGET`,
  `_DAYS`, `_MAX` are gone; `workshop.py open` requires `--budget`, `--days`,
  `--max`, so no gateway-wide default can silently apply to the wrong workshop.
- **`GATEWAY_ORGANIZER` is gone.** One hub script serves every workshop, so the
  rendered docs and hub script say "your workshop organizer".
- **Hub settings (`GATEWAY_HUB_*`) are asked at gateway setup**, "so the
  installer is not tempted to use a workshop-specific name"; the skill suggests
  a generic command name (`claude-workshop`).
- **Adding a workshop**: ask its questions (with a rough cost sense), make an
  organizer key if they have no AWS, check the hub script and `.url` are
  current, write a record, and **do not open sign-up** (a code opened early can
  leak; the organizer opens it in the room).
- **The record** `docs/workshops/<name>.md` is written by `workshop.py plan`
  (not by hand) so the name is validated and the `open` command in it has the
  right flags. No code, key or URL; committed; it is how the organizer gets
  the settings.

Tested in a scratch deployment with a clean venv: render, `plan`, name and
flag checks. **Not tested**: `open`/`status` on a live gateway (request body
unchanged), or the step driven by an agent. Old deployment folders keep their
copied scripts; their `GATEWAY_WORKSHOP_*`/`GATEWAY_ORGANIZER` lines are
ignored by the new ones.

## Task B, the install template repo (built; see litellm-gateway-template.md)

Eli, 2026-09-28: next is editing `~/litellm-gateway-template`
(`nmfs-opensci/litellm-gateway-template`). Since built; current state in
[litellm-gateway-template.md](litellm-gateway-template.md). The paragraph below
is the original plan. The plan in the
clinics repo calls it `nmfs-opensci/litellm-bedrock-gateway`; the real name is
`litellm-gateway-template`. It should be the sparse per-install repo an
installer copies: `gateway.env`, `models.yaml`, `.gitignore`, and committed
`docs/` and `hub/` after rendering, with scripts from the skill's
`init_deployment.sh`, and no URL or secret in any committed file.

## Key batches and three roles (issue #33, 2026-09-29)

Eli's decisions, from a hub-admin point of view (Eli is a hub admin without
AWS access to the org account that hosts the real gateway):

- **Three roles**: installer (AWS), key issuer (install-repo clone + revocable
  issuer key, often no AWS; e.g. Eli), organizer (hub account only: no repo,
  no admin key). "Organizer key" was renamed "issuer key"; the old
  `organizer` subcommand, `org-` prefix and `secrets/organizer-key` keep
  working because the template repo and the clinics install already use them.
- **Sign-up stays.** Eli first proposed dropping it for pre-issued keys, then
  kept it: it suits the common case where the issuer runs the workshop. Batches
  are additive; the hub script takes a code or an `sk-` key at one prompt.
- **Organizers cannot stop keys; they ask the issuer** (Eli chose this over a
  key-service `/workshop/stop` endpoint). Self-delete was tested and rejected:
  see `references/workshop-signup.md`, "Key batches".
- Batch files go to organizers by Slack DM or into their hub home; they get
  copies of `docs/workshop-organizer.md` and `docs/hub-quickstart.md`, since
  they have no repo.
- Eli believed keys only work on the hub; they don't (the gateway is public,
  the URL is readable by every hub user). Budget and expiry are the real limit.

Follow-up outside this repo: `litellm-gateway-template/AGENTS.md` names
`secrets/organizer-key` and "organizer's copy"; still works, but should say
issuer. Existing installs keep stale `docs/organizer*.md` after re-rendering
(render never deletes); remove them by hand.
