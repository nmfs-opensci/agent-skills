# Issuing keys without AWS access

For a key issuer of the gateway `{{STACK}}` who has no access to the AWS
account it runs in: you make and stop keys, hand batches of keys to workshop
organizers, and can open and close workshop sign-up. Everything that needs AWS
stays with the installer.

## What the installer sends you, privately

- the **gateway URL** (starts with `https://`)
- your own **issuer key** (starts with `sk-`), made for you with
  `keys.py issuer create`

The issuer key can manage every key and every workshop on the gateway, not
only the ones you made. Keep it in the file below and nowhere else: not in
chat, email, a notebook or this repository. If it may have leaked, tell the
installer, who revokes it and makes you a new one; nothing else has to change.

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
   (umask 077; cat > secrets/issuer-key)
   ```

   Paste the issuer key, press Enter, then Ctrl-D. Then the URL the same way:

   ```bash
   cat > secrets/gateway-url
   ```

When both files exist, the scripts use them and do not need AWS. (An older
install may call the key file `secrets/organizer-key`; that name still works.)

## Every time

```bash
source gateway.env
```

Then the commands in `docs/key-issuer.md` work as usual. A workshop's name and
settings are in `docs/workshops/<name>.md`, with the exact command for it;
other issuers may run workshops on the same gateway at the same time, each
with its own name:

```bash
python scripts/keys.py batch --workshop whale --count 15 --budget 20 --days 7
python scripts/workshop.py status --workshop whale   # every key, with spend
python scripts/keys.py block ws-whale-07             # or delete
```

`batch` writes the keys to `secrets/whale-keys.txt`. Send that file to the
workshop's organizer privately (a direct message, or copy it into their hub
home folder), with a copy of `docs/workshop-organizer.md` (their page) and
`docs/hub-quickstart.md` (for participants): they have no copy of this
repository.

## Ask the installer for

- starting the server before a workshop and stopping it after,
- adding or removing models,
- a new issuer key if yours may have leaked,
- the new URL if the gateway is rebuilt (an `sslip.io` URL changes),
- deleting everything at the end.
