# Running the gateway without AWS access

For an organizer of the gateway `{{STACK}}` who has no access to the AWS
account it runs in. You can open and close workshop sign-up and create, block,
delete and watch keys. Everything that needs AWS stays with the installer.

## What the installer sends you, privately

- the **gateway URL** (starts with `https://`)
- your own **organizer key** (starts with `sk-`), made for you with
  `keys.py organizer create`

The organizer key can manage every key and every workshop on the gateway, not
only yours. Keep it in the file below and nowhere else: not in chat, email, a
notebook or this repository. If it may have leaked, tell the installer, who
revokes it and makes you a new one; nothing else has to change.

You do not get the Admin UI password or the gateway's master key: neither can
be revoked. The commands below show everything the UI would.

## Once: set up

1. Clone this repository and, in its folder, make the Python environment:

   ```bash
   python3 -m venv .venv
   .venv/bin/pip install -r scripts/requirements.txt
   ```

2. Save the two values in `secrets/` (never committed to git). In a terminal,
   in this folder:

   ```bash
   mkdir -p secrets && chmod 700 secrets
   (umask 077; cat > secrets/organizer-key)
   ```

   Paste the organizer key, press Enter, then Ctrl-D. Then the URL the same way:

   ```bash
   cat > secrets/gateway-url
   ```

When both files exist, the scripts use them and do not need AWS.

## Every time

```bash
source gateway.env
```

Then the commands in `docs/organizer.md` work as usual. Give your workshop a
name of lowercase letters and digits; other organizers may run workshops on the
same gateway at the same time, each with its own name and code:

```bash
python scripts/workshop.py open --workshop whale --code whale-2026 --hours 4
python scripts/workshop.py status --workshop whale   # who has a key, and spend
python scripts/keys.py block ws-whale-someone        # or delete
python scripts/workshop.py close --workshop whale
```

## Ask the installer for

- starting the server before a workshop and stopping it after,
- adding or removing models,
- a new organizer key if yours may have leaked,
- the new URL if the gateway is rebuilt (an `sslip.io` URL changes),
- deleting everything at the end.
