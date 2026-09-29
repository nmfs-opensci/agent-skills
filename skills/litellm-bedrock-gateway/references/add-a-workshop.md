# Adding a workshop

**Status: Experimental.** The steps use tools tested on a throwaway gateway
(`workshop.py`, `keys.py organizer`, the hub script); this sequence as a whole
has not been run for a real workshop yet.

One gateway serves many workshops, so the installer sets it up once and adds
workshops later, often weeks apart and with different organizers. Run this
after the gateway is deployed and verified, every time someone says something
like "Set up a workshop named orca with organizer jane-blow".

Nothing here is billed beyond what participants spend, and nothing opens
sign-up: the organizer does that in the room.

## 1. Ask about this workshop

- **Name**: 1–20 lowercase letters and digits, no hyphen (`orca`, `whale2026`).
  It names the keys, `ws-<workshop>-<hub username>`, and must differ from any
  other workshop on this gateway (`workshop.py status` lists them).
- **Organizer**: who runs it, and **whether they have AWS access** to this
  gateway's account.
- **Dates**, and **how many people**.
- **Budget per person** and **how many days keys last**. Give a sense of scale
  from `costs.md` (Provisional): about $3–8 per person-hour of sustained Sonnet
  use, less with a cheap default model; the reference deployment settled on $20
  per person for a week.
- **How long sign-up stays open** once opened (hours; default 4).

Do not ask about the hub script's name or folder: those are per gateway, set at
setup (`gateway.env`), and shared by every workshop.

## 2. An organizer without AWS gets their own key

If the organizer has no AWS access and has no organizer key yet (`python
scripts/keys.py organizer list`), the installer makes one:

```bash
python scripts/keys.py organizer create jane-blow
```

It is written to `secrets/org-jane-blow.key` and never printed. Tell the
installer to send the organizer, **privately**, that key and the gateway URL
from `secrets/gateway-url`, and to point them at `docs/organizer-no-aws.md`.
Never the master key or the Admin UI password (`workshop-signup.md`). An
organizer who already has a key for this gateway reuses it.

## 3. The hub script is in place

Sign-up needs the hub script and the URL beside it in the hub's shared folder.
They are copied once per hub, but must be copied again after the script
changes or the gateway URL changes (an `sslip.io` URL changes on rebuild). If
the installer is on the hub, check that
`$GATEWAY_HUB_ADMIN_DIR/$GATEWAY_HUB_COMMAND.url` matches
`secrets/gateway-url` without printing either (`cmp -s`). Otherwise, give
the copy commands from `docs/organizer.md` to whoever administers the hub.

## 4. Write the record

```bash
python scripts/workshop.py plan --workshop orca --organizer jane-blow \
  --dates "14-15 Oct 2026" --people 25 --budget 20 --days 7 --hours 4
```

Add `--organizer-aws` if the organizer has AWS access, and `--max` if the key
cap should differ from the number of people. It writes
`docs/workshops/orca.md`: the settings, and the exact `open` command with
`<code>` in place of the code. It holds no code, key or URL, so commit it with
the install repository; the organizer gets it with the repository.

## 5. Do not open sign-up

Leave sign-up closed. A code opened days early can leak, and an open workshop
hands keys to anyone who has it. On the day, the organizer picks a code and
runs the `open` command from the record, in the room.
