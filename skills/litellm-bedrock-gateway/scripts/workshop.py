"""Plan a workshop, and open, close or check its sign-up on the gateway's key service.

Run from the deployment folder after `source gateway.env`:

  python scripts/workshop.py plan --workshop whale --organizer jane-blow --dates "14-15 Oct 2026" \
      --people 25 --budget 20 --days 7 --hours 4
  python scripts/workshop.py open --workshop whale --code whale-2026 --hours 4 --budget 20 --days 7 --max 25
  python scripts/workshop.py status                     # every workshop, one line each
  python scripts/workshop.py status --workshop whale    # who has a key, with spend
  python scripts/workshop.py close --workshop whale

`plan` writes docs/workshops/<name>.md, a committed record of the workshop's
settings with the exact `open` command to run on the day (without the code,
which is chosen then, and without the gateway URL). It contacts nothing.

Several workshops can be open at once on one gateway; each has its own name
(lowercase letters and digits), code, key cap, budget and expiry, and the code
a participant types decides which workshop they join. Participants run the hub
script (hub/<GATEWAY_HUB_COMMAND>) and type the code. Each gets a key named
ws-<workshop>-<hub username> with --budget dollars that expires after --days;
at most --max keys per workshop. These are per workshop, so `open` has no
defaults for them. Block or delete one key with keys.py
(`python scripts/keys.py delete ws-whale-alice`); deleting lets that person
sign up again.

Finds the gateway and admin key the way keys.py does, so it works without AWS
when secrets/gateway-url and secrets/organizer-key exist. Any admin key can open,
close and see every workshop. Prints no key values.
"""

import argparse
import datetime as dt
import os
import pathlib
import re
import sys

import requests

from keys import Gateway, admin_key, gateway_url, print_keys


NAME = re.compile(r"^[a-z0-9]{1,20}$")  # as the key service checks it


def open_command(name, hours, budget, days, max_keys, code="<code>"):
    return (f"python scripts/workshop.py open --workshop {name} --code {code} --hours {hours:g} "
            f"--budget {budget:g} --days {days} --max {max_keys}")


def plan(args):
    """Write docs/workshops/<name>.md. Contacts nothing."""
    path = pathlib.Path("docs/workshops") / f"{args.workshop}.md"
    if path.exists() and not args.force:
        sys.exit(f"{path} exists; add --force to replace it.")
    aws = "yes" if args.organizer_aws else "no: runs it with an organizer key (docs/organizer-no-aws.md)"
    text = f"""# Workshop `{args.workshop}`

Written by `scripts/workshop.py plan` for the gateway `{os.environ["GATEWAY_STACK"]}`.
It holds no code, key or URL: the code is chosen on the day and said in the
room, and the gateway URL goes to people privately.

| | |
| --- | --- |
| Organizer | {args.organizer} |
| Organizer has AWS access | {aws} |
| Dates | {args.dates} |
| People | {args.people} (at most {args.max} keys) |
| Budget per key | ${args.budget:g} |
| Keys last | {args.days} days from sign-up |
| Sign-up stays open | {args.hours:g} hours from `open` |

## On the day

Participants on the hub follow `docs/hub-quickstart.md`. Choose a code (not
used by another open workshop), then:

```bash
source gateway.env
{open_command(args.workshop, args.hours, args.budget, args.days, args.max)}
python scripts/workshop.py status --workshop {args.workshop}   # who has a key, spend
python scripts/workshop.py close --workshop {args.workshop}
```

Keys are named `ws-{args.workshop}-<hub username>`. More in `docs/organizer.md`.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    print(f"Wrote {path}. Commit it; it holds no secret.")


def describe(name, w, now):
    ended = w["open_until"] and dt.datetime.fromisoformat(w["open_until"]) < now
    state = ("OPEN until " + w["open_until"] if w["open"] else
             f"ENDED at {w['open_until']}" if ended and w["opened_by"] else "CLOSED")
    return (f"{name}: sign-up {state}. Keys: ${w['budget']:g} each, {w['days']} days, "
            f"{len(w['issued'])} of {w['max_keys']} issued"
            f"{'; opened by ' + w['opened_by'] if w['opened_by'] else ''}.")


def main():
    stack = os.environ.get("GATEWAY_STACK") or sys.exit("Run `source gateway.env` in the deployment folder first.")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--url", help="default: as keys.py finds it")
    sub = p.add_subparsers(dest="cmd", required=True)

    def settings(parser):
        parser.add_argument("--workshop", required=True, help="its name: lowercase letters and digits")
        parser.add_argument("--hours", type=float, default=4, help="sign-up closes after this (default 4)")
        parser.add_argument("--budget", type=float, required=True, help="USD per key")
        parser.add_argument("--days", type=int, required=True, help="keys expire after this many days")

    o = sub.add_parser("open")
    settings(o)
    o.add_argument("--code", required=True, help="said in the room; not case-sensitive")
    o.add_argument("--max", type=int, required=True, help="most keys for this workshop")
    pl = sub.add_parser("plan", help="write docs/workshops/<name>.md; contacts nothing")
    settings(pl)
    pl.add_argument("--organizer", required=True, help="who runs it, as people know them")
    pl.add_argument("--organizer-aws", action="store_true", help="the organizer has AWS access")
    pl.add_argument("--dates", required=True, help='when it runs, as text: "14-15 Oct 2026"')
    pl.add_argument("--people", type=int, required=True, help="how many are expected")
    pl.add_argument("--max", type=int, help="most keys (default: --people)")
    pl.add_argument("--force", action="store_true", help="replace an existing record")
    sub.add_parser("close").add_argument("--workshop", required=True)
    sub.add_parser("status").add_argument("--workshop", help="list this workshop's keys")
    args = p.parse_args()
    if args.workshop is not None:
        args.workshop = args.workshop.strip().lower()
        if not NAME.match(args.workshop):
            sys.exit("Workshop names are 1-20 lowercase letters and digits (no hyphen).")
    if args.cmd == "plan":
        args.max = args.max or args.people
        return plan(args)

    url, key = gateway_url(stack, args.url), admin_key(stack)
    admin, headers = url + "/workshop/admin", {"Authorization": f"Bearer {key}"}
    name = (args.workshop or "").strip().lower()

    if args.cmd == "open":
        until = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=args.hours)
        body = {"workshop": name, "code": args.code, "max_keys": args.max,
                "open_until": until.isoformat(timespec="minutes"), "budget": args.budget, "days": args.days}
    elif args.cmd == "close":
        body = {"workshop": name, "code": ""}
    if args.cmd in ("open", "close"):
        r = requests.post(admin, json=body, headers=headers, timeout=30)
        if not r.ok:
            sys.exit(f"HTTP {r.status_code}: {r.text[:300]}")

    r = requests.get(admin, headers=headers, timeout=30)
    if r.status_code == 404:
        sys.exit("HTTP 404: the key service refused this key (not an admin key, or revoked), "
                 "or it is not running (scripts/instance.sh health).")
    if not r.ok:
        sys.exit(f"HTTP {r.status_code}: {r.text[:300]} (is the key service running? scripts/instance.sh health)")
    workshops, now = r.json()["workshops"], dt.datetime.now(dt.timezone.utc)
    if not name:
        if not workshops:
            print("No workshops yet.")
        for n, w in workshops.items():
            print(describe(n, w, now))
        return
    if name not in workshops:
        sys.exit(f"No workshop named {name!r}. Known: {', '.join(workshops) or 'none'}.")
    print(describe(name, workshops[name], now))
    rows = [k for k in Gateway(url, key).keys() if (k.get("metadata") or {}).get("workshop") == name]
    print_keys(rows)


if __name__ == "__main__":
    main()
