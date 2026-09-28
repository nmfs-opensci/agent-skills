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
- `POST /workshop/key {"code", "user"}` refuses when closed, past its end time
  or at the key cap; waits ~1 s and refuses on a wrong code (it serves one
  request at a time, so guessing is slow and the count cannot race); checks the
  name looks like a GitHub username; refuses with 409 if `ws-<user>` exists. It
  **never returns a key that already exists**, so a known username gets nobody
  anything. Otherwise it creates `ws-<user>` (also its `user_id`,
  `security.md`) with the workshop budget and expiry.
- Issued keys are counted from LiteLLM itself (aliases starting `ws-`), so a
  restart loses nothing and deleting a key frees a slot.
- The organizer drives it with `scripts/workshop.py open|close|status`, which
  posts to `/workshop/admin` with the master key. Settings persist in
  `/opt/litellm/keyservice/state/`. Logs name the user and outcome, never a key
  or code.
- Its code lives in Parameter Store (`/<stack>/keyservice`, Advanced tier through
  Intelligent-Tiering, about $0.05 a month); `refresh.sh` installs and restarts
  it, like the LiteLLM config.

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
`secrets/master-key`. When both exist, `keys.py`, `workshop.py` and
`check_gateway.py` use them and never call AWS (`docs/organizer-no-aws.md`,
tested with AWS credentials disabled). The Admin UI password comes the same way.

What stays with the installer: start and stop, `deploy.sh` (models, settings),
a new master key, rebuild and teardown. The master key controls every key on the
gateway: send it once, privately. **Rotating it has not been worked out** for
this template: the instance writes its env files at first boot only, and
`make_secrets.py` never overwrites. Until it has, a leaked master key means
blocking what was misused and, at worst, a rebuild.
