"""Open, close or check workshop sign-up on the gateway's key service.

Run from the deployment folder after `source gateway.env`:

  python scripts/workshop.py open --code whale-2026 --hours 4
  python scripts/workshop.py open --code whale-2026 --hours 3 --budget 10 --days 2 --max 30
  python scripts/workshop.py status
  python scripts/workshop.py close

Participants run the hub script (hub/<GATEWAY_HUB_COMMAND>) and type the code.
Each gets a key named ws-<hub username> with --budget dollars that expires
after --days; at most --max keys are out at once. Defaults come from
GATEWAY_WORKSHOP_BUDGET, _DAYS and _MAX in gateway.env. Delete a key with
`python scripts/keys.py delete ws-<name>` to let that person sign up again.

Finds the gateway and master key the way keys.py does, so it works without AWS
when secrets/gateway-url and secrets/master-key exist. Prints no key values.
"""

import argparse
import datetime as dt
import os
import sys

import requests

from keys import gateway_url, master_key


def env_number(name, default, kind):
    try:
        return kind(os.environ.get(name) or default)
    except ValueError:
        sys.exit(f"{name} in gateway.env is not a number")


def main():
    stack = os.environ.get("GATEWAY_STACK") or sys.exit("Run `source gateway.env` in the deployment folder first.")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--url", help="default: as keys.py finds it")
    sub = p.add_subparsers(dest="cmd", required=True)
    o = sub.add_parser("open")
    o.add_argument("--code", required=True, help="said in the room; not case-sensitive")
    o.add_argument("--hours", type=float, default=4, help="sign-up closes after this (default 4)")
    o.add_argument("--max", type=int, default=env_number("GATEWAY_WORKSHOP_MAX", 20, int),
                   help="most workshop keys at once")
    o.add_argument("--budget", type=float, default=env_number("GATEWAY_WORKSHOP_BUDGET", 20, float),
                   help="USD per key")
    o.add_argument("--days", type=int, default=env_number("GATEWAY_WORKSHOP_DAYS", 7, int),
                   help="keys expire after this many days")
    sub.add_parser("close")
    sub.add_parser("status")
    args = p.parse_args()

    admin = gateway_url(stack, args.url) + "/workshop/admin"
    headers = {"Authorization": f"Bearer {master_key(stack)}"}

    if args.cmd == "open":
        until = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=args.hours)
        body = {"code": args.code, "max_keys": args.max, "open_until": until.isoformat(timespec="minutes"),
                "budget": args.budget, "days": args.days}
    elif args.cmd == "close":
        body = {"code": ""}
    if args.cmd in ("open", "close"):
        r = requests.post(admin, json=body, headers=headers, timeout=30)
        if not r.ok:
            sys.exit(f"HTTP {r.status_code}: {r.text[:300]}")

    r = requests.get(admin, headers=headers, timeout=30)
    if not r.ok:
        sys.exit(f"HTTP {r.status_code}: {r.text[:300]} (is the key service running? scripts/instance.sh health)")
    s = r.json()
    ended = s["open_until"] and dt.datetime.fromisoformat(s["open_until"]) < dt.datetime.now(dt.timezone.utc)
    state = "CLOSED" if not s["code"] else f"ENDED at {s['open_until']}" if ended else f"OPEN until {s['open_until']}"
    print(f"Sign-up {state}. Keys: ${s['budget']:g} each, {s['days']} days, "
          f"{len(s['issued'])} of {s['max_keys']} issued.")
    for alias in s["issued"]:
        print("  " + alias)


if __name__ == "__main__":
    main()
