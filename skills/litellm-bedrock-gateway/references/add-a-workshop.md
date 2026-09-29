# Adding a workshop

**Status: Experimental.** The steps use tools tested on a throwaway gateway
(`workshop.py`, `keys.py issuer`, the hub script); `keys.py batch` and the hub
script's key and `--status` paths as noted in `workshop-signup.md`. This
sequence as a whole has not been run for a real workshop yet.

One gateway serves many workshops, so the installer sets it up once and adds
workshops later, often weeks apart and with different organizers. Run this
after the gateway is deployed and verified, every time someone says something
like "Set up a workshop named orca with organizer jane-blow".

Nothing here is billed beyond what participants spend. Nothing opens sign-up
or makes keys: that happens close to the workshop (step 5).

## 1. Ask about this workshop

- **Name**: 1–20 lowercase letters and digits, no hyphen (`orca`, `whale2026`).
  It names the keys, `ws-<workshop>-<hub username>`, and must differ from any
  other workshop on this gateway (`workshop.py status` lists them).
- **Organizer**: who runs it.
- **Sign-up or a batch** (`workshop-signup.md`, "Three roles"). Will someone
  who can issue keys (AWS access or an issuer key) be in the room? Then
  sign-up with a code works. If the organizer has only a hub account, a
  **key issuer** makes a batch of keys and sends it to them: ask who that is
  (often a hub admin, not the installer).
- **Who issues the keys**, and whether they have AWS access to this gateway's
  account.
- **Dates**, and **how many people**.
- **Budget per person** and **how many days keys last**. Give a sense of scale
  from `costs.md` (Provisional): about $3–8 per person-hour of sustained Sonnet
  use, less with a cheap default model; the reference deployment settled on $20
  per person for a week.
- For sign-up, **how long it stays open** once opened (hours; default 4).
  For a batch, when it will be made: keys expire `--days` after they are made.

Do not ask about the hub script's name or folder: those are per gateway, set at
setup (`gateway.env`), and shared by every workshop.

## 2. A key issuer without AWS gets their own key

If whoever issues this workshop's keys (the organizer, for sign-up; the key
issuer, for a batch) has no AWS access and no issuer key yet (`python
scripts/keys.py issuer list`), the installer makes one:

```bash
python scripts/keys.py issuer create jane-blow
```

It is written to `secrets/iss-jane-blow.key` and never printed. Tell the
installer to send it, **privately**, with the gateway URL from
`secrets/gateway-url`, and to point them at `docs/issuer-no-aws.md`. Never the
master key or the Admin UI password (`workshop-signup.md`). Someone who
already has an issuer key for this gateway reuses it. An organizer who only
hands out a batch needs no key of this kind.

## 3. The hub script is in place

Sign-up and a batch both need the hub script and the URL beside it in the
hub's shared folder (participants paste a batch key into it, and the organizer
checks the batch with it). They are copied once per hub, but must be copied
again after the script changes or the gateway URL changes (an `sslip.io` URL changes on rebuild). If
the installer is on the hub, check that
`$GATEWAY_HUB_ADMIN_DIR/$GATEWAY_HUB_COMMAND.url` matches
`secrets/gateway-url` without printing either (`cmp -s`). Otherwise, give
the copy commands from `docs/key-issuer.md` to whoever administers the hub.

## 4. Write the record

```bash
python scripts/workshop.py plan --workshop orca --organizer jane-blow \
  --dates "14-15 Oct 2026" --people 25 --budget 20 --days 7 --hours 4
python scripts/workshop.py plan --workshop seal --organizer sam --issuer eli \
  --dates "3 Nov 2026" --people 15 --budget 20 --days 7 --batch
```

Add `--issuer` when someone other than the organizer opens sign-up or makes
the batch, `--batch` for a batch, and `--max` if the number of keys should
differ from the number of people. It writes `docs/workshops/<name>.md`: the
settings, and the exact `open` command (with `<code>` in place of the code) or
`keys.py batch` command. It holds no code, key or URL, so commit it with the
install repository.

## 5. Do not open sign-up or make the batch yet

Leave sign-up closed. A code opened days early can leak, and an open workshop
hands keys to anyone who has it. On the day, whoever opens sign-up picks a code
and runs the `open` command from the record, in the room.

Make a batch close to the workshop, not now: its keys start expiring when they
are made. The key issuer runs the `keys.py batch` command from the record and
sends `secrets/<name>-keys.txt` to the organizer privately (a direct message,
or into their hub home folder), with a copy of `docs/workshop-organizer.md`
and `docs/hub-quickstart.md`: the organizer has no copy of the repository.
