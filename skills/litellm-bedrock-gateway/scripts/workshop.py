"""Open, close or check workshop sign-up on the gateway's key service.

Run from the deployment folder after `source gateway.env`:

  python scripts/workshop.py open --workshop whale --code whale-2026 --hours 4
  python scripts/workshop.py open --workshop whale --code whale-2026 --hours 3 --budget 10 --days 2 --max 30
  python scripts/workshop.py status                     # every workshop, one line each
  python scripts/workshop.py status --workshop whale    # who has a key, with spend
  python scripts/workshop.py close --workshop whale

Several workshops can be open at once on one gateway; each has its own name
(lowercase letters and digits), code, key cap, budget and expiry, and the code
a participant types decides which workshop they join. Participants run the hub
script (hub/<GATEWAY_HUB_COMMAND>) and type the code. Each gets a key named
ws-<workshop>-<hub username> with --budget dollars that expires after --days;
at most --max keys per workshop. Defaults come from GATEWAY_WORKSHOP_BUDGET,
_DAYS and _MAX in gateway.env. Block or delete one with keys.py
(`python scripts/keys.py delete ws-whale-alice`); deleting lets that person
sign up again.

Finds the gateway and admin key the way keys.py does, so it works without AWS
when secrets/gateway-url and secrets/organizer-key exist. Any admin key can open,
close and see every workshop. Prints no key values.
"""

import argparse
import datetime as dt
import os
import sys

import requests

from keys import Gateway, admin_key, gateway_url, print_keys


def env_number(name, default, kind):
    try:
        return kind(os.environ.get(name) or default)
    except ValueError:
        sys.exit(f"{name} in gateway.env is not a number")


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
    o = sub.add_parser("open")
    o.add_argument("--workshop", required=True, help="its name: lowercase letters and digits")
    o.add_argument("--code", required=True, help="said in the room; not case-sensitive")
    o.add_argument("--hours", type=float, default=4, help="sign-up closes after this (default 4)")
    o.add_argument("--max", type=int, default=env_number("GATEWAY_WORKSHOP_MAX", 20, int),
                   help="most keys for this workshop")
    o.add_argument("--budget", type=float, default=env_number("GATEWAY_WORKSHOP_BUDGET", 20, float),
                   help="USD per key")
    o.add_argument("--days", type=int, default=env_number("GATEWAY_WORKSHOP_DAYS", 7, int),
                   help="keys expire after this many days")
    sub.add_parser("close").add_argument("--workshop", required=True)
    sub.add_parser("status").add_argument("--workshop", help="list this workshop's keys")
    args = p.parse_args()

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
