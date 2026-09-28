# Workshop sign-up on a JupyterHub, and organizers without AWS

**Status: Experimental.** Built and used for one group on one 2i2c JupyterHub
(September 2026), then ported into this skill and tested in a throwaway stack.

## What it does

On the hub, a participant runs one command and types a code said in the room;
Claude Code starts through the gateway with that person's own key. No `sk-`
string is handed out or pasted. Participants off the hub still get keys the
usual way (`keys-and-monitoring.md`).

- **Key service** (`assets/keyservice.py`): Python standard library only, in a
  pinned `python` container on the gateway's Docker network, no published port.
  Caddy sends `/workshop/*` to it; everything else goes to LiteLLM. It is
  deployed on every gateway and stays **closed** until the organizer opens it.
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
- Organizers drive it with `scripts/workshop.py open|close|status --workshop
  <name>`, which posts to `/workshop/admin` with an **admin key**: the master
  key, or a key whose LiteLLM user has the `proxy_admin` role (an organizer
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

## The hub script

`render.py` writes `hub/<GATEWAY_HUB_COMMAND>` from `assets/hub-signup.sh`. The
command name also names the key folder (`~/.config/<command>/`), so **a test
gateway and a production gateway must use different names**, or one gateway's
key would be sent to the other. The organizer copies it into a shared folder
participants can read but not change, with the URL beside it:

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

## An organizer without AWS

The installer may be the only person with access to the AWS account. The
organizer then runs the event from a clone of the install's repository with two
files the installer sends privately: `secrets/gateway-url` and
`secrets/organizer-key`. When both exist, `keys.py`, `workshop.py` and
`check_gateway.py` use them and never call AWS (`docs/organizer-no-aws.md`;
tested with every AWS credential source disabled, instance metadata included).

**The organizer gets their own revocable key, never the master key**
(nmfs-opensci/agent-skills#27). `keys.py organizer create <name>` (installer,
master key from Parameter Store) makes a LiteLLM user `org-<name>` with the
`proxy_admin` role and a key for it, written to `secrets/org-<name>.key`; an
optional `--days` gives it an expiry. `keys.py organizer revoke <name>` deletes
that user's keys and the user; the key stops working at once. Tested on
LiteLLM 1.102.1: a `proxy_admin` key lists, creates, updates, blocks, unblocks
and deletes keys, including keys the master key made.

What an organizer key **cannot** do, tested on 1.102.1:

- log in to the Admin UI (`/login` accepts only `admin` and the UI password).
  The organizer does without the UI: `workshop.py status --workshop <name>` and
  `keys.py list` show who has a key, spend, budget, expiry and blocked state.
  The UI password is not sent, because it cannot be revoked either.
- add models through the API (`/model/new` needs `STORE_MODEL_IN_DB`, which
  this template does not set), or regenerate keys (Enterprise only).

What it **can** do beyond keys, and revocation does not undo:

- create more `proxy_admin` users and keys. `organizer revoke` therefore ends
  by listing every admin user and its keys (`organizer list`), flagging any not
  made by `organizer create`; delete those with the master key.
- change proxy-wide settings through `/config/update` (for example logging
  callbacks), which persist in the database. Nothing here detects that. If an
  organizer key was misused, treat the gateway as the master key's would be:
  rebuild.

This is still strictly better than sending the master key, which has all the
same powers and cannot be revoked.

What stays with the installer: start and stop, `deploy.sh` (models, settings),
organizer keys, the Admin UI, rebuild and teardown. **Rotating the master key
itself has not been worked out**: the instance writes its env files at first
boot only, and `make_secrets.py` never overwrites. With organizers on their own
keys it no longer leaves the installer, so this is less urgent.
