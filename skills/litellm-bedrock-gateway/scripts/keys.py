"""Manage participants' LiteLLM virtual keys.

Run from the deployment folder after `source gateway.env`:

  python scripts/keys.py create alice bob carol --budget 20 --days 7
  python scripts/keys.py create dana --budget 5 --days 2 --models claude-haiku-4-5-20251001
  python scripts/keys.py list
  python scripts/keys.py update alice --budget 30 --days 3   # new total budget; expiry from now
  python scripts/keys.py block alice                         # or: unblock alice
  python scripts/keys.py delete alice
  python scripts/keys.py models                              # what the gateway serves

The organizer creates every key and sends it to its owner privately (a direct
message, not a shared channel). A new key's value is written only to
secrets/<name>.key (mode 600, git-ignored) and never printed. The admin
(master) key is read from Parameter Store at run time and never printed.

Talks to the stack's GatewayUrl, or to GATEWAY_URL if set (for example
http://localhost:4000 with scripts/tunnel.sh running).
"""

import argparse
import os
import pathlib
import sys

import boto3
import requests

SECRETS = pathlib.Path(__file__).resolve().parent.parent / "secrets"


def stack_output(stack, key):
    outputs = boto3.client("cloudformation").describe_stacks(StackName=stack)["Stacks"][0]["Outputs"]
    return next(o["OutputValue"] for o in outputs if o["OutputKey"] == key)


def master_key(stack):
    return boto3.client("ssm").get_parameter(
        Name=f"/{stack}/master-key", WithDecryption=True
    )["Parameter"]["Value"]


class Gateway:
    def __init__(self, url, stack):
        self.url = url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {master_key(stack)}"}

    def call(self, method, path, **kw):
        r = requests.request(method, self.url + path, headers=self.headers, timeout=30, **kw)
        if not r.ok:
            sys.exit(f"{method} {path}: HTTP {r.status_code}: {r.text[:300]}")
        return r.json()

    def keys(self):
        rows, page = [], 1
        while True:
            data = self.call("GET", "/key/list",
                             params={"return_full_object": "true", "size": 100, "page": page})
            rows += data.get("keys", [])
            if page >= (data.get("total_pages") or 1):
                return rows
            page += 1

    def token_for(self, name):
        for k in self.keys():
            if k.get("key_alias") == name:
                return k["token"]
        sys.exit(f"No key named {name!r}.")


def remove_local(name):
    """Delete a key file and any JupyterLab checkpoint copy of it."""
    (SECRETS / f"{name}.key").unlink(missing_ok=True)
    (SECRETS / ".ipynb_checkpoints" / f"{name}-checkpoint.key").unlink(missing_ok=True)


def create(gw, args):
    for name in args.names:
        if (SECRETS / f"{name}.key").exists():
            sys.exit(f"secrets/{name}.key already exists; delete that key first.")
    existing = {k.get("key_alias") for k in gw.keys()}
    clash = [n for n in args.names if n in existing]
    if clash:
        sys.exit(f"The gateway already has keys named {', '.join(clash)}.")
    SECRETS.mkdir(mode=0o700, exist_ok=True)
    for name in args.names:
        # user_id matters: LiteLLM lets a key read another key's details
        # (/key/info?key=, /v2/key/info) when neither key has a user_id.
        body = {"key_alias": name, "user_id": name, "max_budget": args.budget,
                "duration": f"{args.days}d", "metadata": {"note": args.note}}
        if args.budget_duration:
            body["budget_duration"] = args.budget_duration  # budget resets this often
        if args.models:
            body["models"] = args.models  # otherwise every model served
        key = gw.call("POST", "/key/generate", json=body)["key"]
        fd = os.open(SECRETS / f"{name}.key", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(key + "\n")
        print(f"created  {name}: ${args.budget:g}"
              f"{' per ' + args.budget_duration if args.budget_duration else ''}, "
              f"{args.days} days, models: {', '.join(args.models) if args.models else 'all'}"
              f" -> secrets/{name}.key")


def update(gw, args):
    body = {"key": gw.token_for(args.name)}
    if args.budget is not None:
        body["max_budget"] = args.budget
    if args.days is not None:
        body["duration"] = f"{args.days}d"
    if len(body) == 1:
        sys.exit("Nothing to change: give --budget and/or --days.")
    gw.call("POST", "/key/update", json=body)
    print(f"updated  {args.name}")


def show(gw, args):
    rows = gw.keys()
    if not rows:
        print("No keys.")
    for k in sorted(rows, key=lambda k: k.get("key_alias") or ""):
        print(f"{k.get('key_alias') or '-':20} spend ${k.get('spend') or 0:8.4f} of "
              f"${k.get('max_budget')}  expires {(k.get('expires') or 'never')[:16]}  "
              f"{'BLOCKED' if k.get('blocked') else 'active'}")


def models(gw, args):
    for m in gw.call("GET", "/v1/models")["data"]:
        print(m["id"])


def block(gw, args, blocked=True):
    gw.call("POST", "/key/block" if blocked else "/key/unblock", json={"key": gw.token_for(args.name)})
    print(f"{'blocked ' if blocked else 'unblocked'} {args.name}")


def delete(gw, args):
    gw.call("POST", "/key/delete", json={"keys": [gw.token_for(args.name)]})
    remove_local(args.name)
    print(f"deleted  {args.name}")


def main():
    stack = os.environ.get("GATEWAY_STACK")
    if not stack or "AWS_ROLE_ARN" in os.environ:
        sys.exit("Run `source gateway.env` in the deployment folder first.")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--url", default=os.environ.get("GATEWAY_URL"), help="default: the stack's GatewayUrl")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("create", help="one key per name")
    c.add_argument("names", nargs="+")
    c.add_argument("--budget", type=float, required=True, help="USD")
    c.add_argument("--days", type=int, required=True, help="expiry in days")
    c.add_argument("--budget-duration", help="reset the budget this often, e.g. 1d (default: never)")
    c.add_argument("--models", nargs="+", help="limit to these models (default: all served)")
    c.add_argument("--note", default="", help="free text stored with the key, e.g. the event")
    u = sub.add_parser("update")
    u.add_argument("name")
    u.add_argument("--budget", type=float, help="new total budget, USD")
    u.add_argument("--days", type=int, help="new expiry, days from now")
    sub.add_parser("list")
    sub.add_parser("models")
    for name in ("block", "unblock", "delete"):
        sub.add_parser(name).add_argument("name")
    args = ap.parse_args()

    gw = Gateway(args.url or stack_output(stack, "GatewayUrl"), stack)
    {
        "create": create,
        "update": update,
        "list": show,
        "models": models,
        "block": block,
        "unblock": lambda g, a: block(g, a, blocked=False),
        "delete": delete,
    }[args.cmd](gw, args)


if __name__ == "__main__":
    main()
