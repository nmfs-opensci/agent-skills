# Running the gateway without AWS access

For an organizer of the gateway `{{STACK}}` who has no access to the AWS
account it runs in. You can open and close sign-up and create, block, delete
and watch keys. Everything that needs AWS stays with the installer.

## What the installer sends you, privately

- the **gateway URL** (starts with `https://`)
- the gateway's **master key** (starts with `sk-`)
- the **Admin UI password** (user `admin`)

The master key controls every key on the gateway. Keep it in the file below
and nowhere else: not in chat, email, a notebook or this repository.

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
   (umask 077; cat > secrets/master-key)
   ```

   Paste the master key, press Enter, then Ctrl-D. Then the URL the same way:

   ```bash
   cat > secrets/gateway-url
   ```

When both files exist, the scripts use them and do not need AWS.

## Every time

```bash
source gateway.env
```

Then the commands in `docs/organizer.md` work as usual, for example:

```bash
python scripts/workshop.py open --code whale-2026 --hours 4
python scripts/workshop.py status
python scripts/keys.py list
```

Admin UI: `<gateway URL>/ui`, user `admin`, the password from the installer.

## Ask the installer for

- starting the server before a workshop and stopping it after,
- adding or removing models,
- a new master key if this one may have leaked,
- the new URL if the gateway is rebuilt (an `sslip.io` URL changes),
- deleting everything at the end.
