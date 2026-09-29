# Workshops on a JupyterHub: sign-up, key batches, and key issuers without AWS

**Status: Experimental.** Sign-up was built and used for one group on one 2i2c
JupyterHub (September 2026), then ported into this skill and tested in a
throwaway stack. Key batches (issue #33) have been tested only as noted under
"Key batches".

## Three roles

| Role | Has | Does |
| --- | --- | --- |
| **Installer** | AWS access | deploys, starts and stops, tears down; makes and revokes issuer keys |
| **Key issuer** | a clone of the install repo and a revocable issuer key; often no AWS | makes keys and batches, blocks and deletes them, watches spend, opens sign-up |
| **Organizer** | a hub account; no repo, no admin key | hands out a batch of keys, checks its spend from the hub, asks the issuer to stop a key |

One person may hold several roles. An organizer who is also a key issuer
usually uses sign-up; one who is not gets a batch.

## Two ways a workshop gets keys

- **Sign-up** (below): the key issuer opens the workshop in the room and says
  a code; each participant's key is made when they type it. No `sk-` string is
  handed out.
- **A batch** ("Key batches"): the key issuer makes N keys ahead of time and
  sends them to the organizer, who gives one to each participant.

Participants run the same hub command either way and type what they were
given; anything starting with `sk-` is taken as a key. Participants off the
hub get keys the usual way (`keys-and-monitoring.md`).

## Sign-up: what it does

- **Key service** (`assets/keyservice.py`): Python standard library only, in a
  pinned `python` container on the gateway's Docker network, no published port.
  Caddy sends `/workshop/*` to it; everything else goes to LiteLLM. It is
  deployed on every gateway and stays **closed** until a key issuer opens it.
- **Several named workshops** can be open at once, each with its own code, key
  cap, budget, expiry and end time. Names are lowercase letters and digits (no
  hyphen, so `ws-<workshop>-<user>` reads back one way). Two open workshops
  cannot share a code (409).
- `POST /workshop/key {"code", "user"}`: the code picks the workshop. It
  refuses when nothing is open, when that workshop has ended or is at its cap;
  waits ~1 s and refuses on a wrong code (it serves one request at a time, so
  guessing is slow and the count cannot race); checks the name looks like a
  GitHub username; refuses with 409 if `ws-<workshop>-<user>` exists. It
  **never returns a key that already exists**, so a known username gets nobody
  anything. Otherwise it creates `ws-<workshop>-<user>` (also its `user_id`,
  `security.md`; `metadata.workshop` = the name) with that workshop's budget
  and expiry. The same person can join two workshops and gets two keys.
- Issued keys are counted from LiteLLM itself (by `metadata.workshop`), so a
  restart loses nothing and deleting a key frees a slot.
- Key issuers drive it with `scripts/workshop.py open|close|status --workshop
  <name>`. `open` takes the workshop's `--budget`, `--days` and `--max` every
  time (there are no gateway-wide defaults: they are per workshop); the
  command with the right values is in `docs/workshops/<name>.md`, written by
  `workshop.py plan` when the workshop was added (`add-a-workshop.md`).
  `open`, `close` and `status` post to `/workshop/admin` with an **admin key**: the master
  key, or a key whose LiteLLM user has the `proxy_admin` role (an issuer
  key). The service asks LiteLLM (`GET /user/info` with the presented key) on
  every admin request, with no cache and a 5 s timeout, so a revoked key is
  refused at once; a refused key waits ~1 s, like a wrong code. Any admin key
  sees and changes every workshop; `opened_by` records who last opened one.
  Settings persist in `/opt/litellm/keyservice/state/`. Logs name the user,
  workshop and outcome, never a key or code. A state file from before named
  workshops (one flat workshop) is ignored.
- Its code lives in Parameter Store (`/<stack>/keyservice`), gzipped and
  base64-encoded because Advanced parameters stop at 8 KB (about $0.05 a month
  through Intelligent-Tiering); `refresh.sh` decodes, installs and restarts it,
  like the LiteLLM config.

## Key batches

For a workshop whose organizer is not a key issuer (issue #33). The key issuer
runs `keys.py batch --workshop <name> --count N --budget B --days D`:

- It makes `ws-<name>-01`, `-02`, ... (two digits, more past 99), each with
  `user_id` = its alias (`security.md`) and `metadata.workshop` = the name, so
  `workshop.py status --workshop <name>` lists them, and on a workshop that
  also uses sign-up they count against its cap. Running it again continues the
  numbering.
- The keys go only into `secrets/<name>-keys.txt` (mode 600, appended to, one
  `<alias> <key>` per line under a `#` line giving the budget and expiry),
  never to the terminal. The issuer sends that file to the organizer privately
  (a direct message, or into the organizer's hub home).
- **Expiry counts from when the batch is made**, not from first use: LiteLLM
  sets `expires` at creation. Make the batch close to the workshop.
- The organizer checks spend from the hub with `<command> --status <file>`: the
  hub script calls `/key/info` with each key in the file, which a key may do
  for itself only. No admin key and no repo. Stopping a key stays with the
  issuer (`keys.py block`).

**Why the organizer cannot stop keys themselves** (tested 2026-09-29 on a
throwaway stack, LiteLLM 1.102.1): a
key made as `keys.py` makes them, whose `user_id` has no LiteLLM user behind
it (role `unknown`), gets 401 on `/key/delete`, `/key/block` and `/key/update`,
for itself as for any other key. Giving each key an `internal_user` owner lets
it delete itself (200), but that key can then `/key/generate` more keys for its
user with no budget and no expiry (a budget above the user's `max_budget` was
refused, nothing else). Rejected. An organizer who must stop keys in the room
gets an issuer key instead.

A key, from a batch or not, works from anywhere that has the gateway URL; the
hub is only where the script is. Per-key budget and expiry are what limit a
leaked key until the issuer blocks it.

## The hub script

`render.py` writes `hub/<GATEWAY_HUB_COMMAND>` from `assets/hub-signup.sh`. The
command name also names the key folder (`~/.config/<command>/`), so **a test
gateway and a production gateway must use different names**, or one gateway's
key would be sent to the other. The installer or a hub admin copies it into a
shared folder participants can read but not change, with the URL beside it:

```bash
cp hub/<command> <admin dir>/
cp secrets/gateway-url <admin dir>/<command>.url
```

The URL sits in that `.url` file, not in the script, because install repos are
often public (see "Keeping the URL out of the repository").

Things learned on a real hub, all handled by the script. Keep them when
changing it:

- **Claude Code may not be in the hub image**: the script installs it on first
  run.
- **New accounts may have no startup files**, and `~/.local/bin` is not on
  `PATH`. The script adds it to the login file and `.bashrc`, and to its own
  `PATH` (without that it reinstalled Claude Code on every run).
- **Hub terminals are login shells** (`bash -l`): they read `~/.profile` (or
  `.bash_profile`), not `.bashrc`.
- **The hub may set `XDG_CONFIG_HOME` to a shared system path**
  (`/etc/xdg/userconfig` on the reference hub), so the script uses
  `~/.config` directly.
- **Some participants have their own Claude account.** The script runs Claude
  Code with its own `CLAUDE_CONFIG_DIR`, sets variables only for that process,
  and never touches `~/.claude`. `claude` stays theirs.
- It clears `CLAUDE_CODE_USE_BEDROCK`, `CLAUDE_CODE_USE_VERTEX`,
  `ANTHROPIC_API_KEY` and `AWS_BEARER_TOKEN_BEDROCK`, which would route around
  the gateway.
- It sets `CLAUDE_CODE_AUTO_MODE_SERVER=0`. Without it Claude Code asks
  Anthropic's server whether auto mode is available, a gateway session is not
  eligible (server-side review on Bedrock needs newer models), and a notice
  holds the first checked action until Enter. **Provisional**: Claude Code's
  docs call the variable temporary; recheck after updates. The participant
  quickstart sets it too.
- On a 2i2c hub, `~/shared` is read-only for users and `~/shared-readwrite` is
  the same folder, writable by admins. Not `~/shared-public`, which on 2i2c
  hubs is normally writable by everyone. Other hubs differ: set
  `GATEWAY_HUB_DIR` and `GATEWAY_HUB_ADMIN_DIR`.

Not tested: a participant's first interactive start answering Claude Code's
onboarding questions (the hub quickstart describes them from memory).

## Keeping the URL out of the repository

`render.py` writes each install's docs into `docs/` and the hub script into
`hub/`, meant to be committed to the install's repository. None of them
contains the gateway URL: `deploy.sh` writes it to `secrets/gateway-url`
(git-ignored), and people get it privately with their key. A URL alone gives no
access, but a published one invites scanning, code guessing, Admin UI login
attempts and tying up the one-at-a-time key service during a workshop.

## A key issuer without AWS

The installer may be the only person with access to the AWS account. A key
issuer (called an organizer before #33) then works from a clone of the
install's repository with two files the installer sends privately:
`secrets/gateway-url` and `secrets/issuer-key` (`secrets/organizer-key`, the
earlier name, still works). When both exist, `keys.py`, `workshop.py` and
`check_gateway.py` use them and never call AWS (`docs/issuer-no-aws.md`;
tested with every AWS credential source disabled, instance metadata included).

**The key issuer gets their own revocable key, never the master key**
(nmfs-opensci/agent-skills#27). `keys.py issuer create <name>` (installer,
master key from Parameter Store) makes a LiteLLM user `iss-<name>` with the
`proxy_admin` role and a key for it, written to `secrets/iss-<name>.key`; an
optional `--days` gives it an expiry. `keys.py issuer revoke <name>` deletes
that user's keys and the user; the key stops working at once. Tested on
LiteLLM 1.102.1: a `proxy_admin` key lists, creates, updates, blocks, unblocks
and deletes keys, including keys the master key made.

What an issuer key **cannot** do, tested on 1.102.1:

- log in to the Admin UI (`/login` accepts only `admin` and the UI password).
  The issuer does without the UI: `workshop.py status --workshop <name>` and
  `keys.py list` show who has a key, spend, budget, expiry and blocked state.
  The UI password is not sent, because it cannot be revoked either.
- add models through the API (`/model/new` needs `STORE_MODEL_IN_DB`, which
  this template does not set), or regenerate keys (Enterprise only).

What it **can** do beyond keys, and revocation does not undo:

- create more `proxy_admin` users and keys. `issuer revoke` therefore ends
  by listing every admin user and its keys (`issuer list`), flagging any not
  made by `issuer create` (or `organizer create`, its earlier name); delete
  those with the master key.
- change proxy-wide settings through `/config/update` (for example logging
  callbacks), which persist in the database. Nothing here detects that. If an
  issuer key was misused, treat the gateway as the master key's would be:
  rebuild.

This is still strictly better than sending the master key, which has all the
same powers and cannot be revoked.

What stays with the installer: start and stop, `deploy.sh` (models, settings),
issuer keys, the Admin UI, rebuild and teardown. **Rotating the master key
itself has not been worked out**: the instance writes its env files at first
boot only, and `make_secrets.py` never overwrites. With issuers on their own
keys it no longer leaves the installer, so this is less urgent.

Keys made before the rename keep working: `org-<name>` users are listed as
made by the script, `issuer revoke <name>` finds `org-<name>` when there is no
`iss-<name>`, and `keys.py organizer ...` is an alias of `keys.py issuer ...`.
