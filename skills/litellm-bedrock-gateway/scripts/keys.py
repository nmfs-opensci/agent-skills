"""Manage participants' LiteLLM virtual keys.

Run from the deployment folder after `source gateway.env`:

  python scripts/keys.py create alice bob carol --budget 20 --days 7
  python scripts/keys.py create dana --budget 5 --days 2 --models claude-haiku-4-5-20251001
  python scripts/keys.py list
  python scripts/keys.py update alice --budget 30 --days 3   # new total budget; expiry from now
  python scripts/keys.py block alice                         # or: unblock alice
  python scripts/keys.py delete alice
  python scripts/keys.py models                              # what the gateway serves
  python scripts/keys.py batch --workshop whale --count 15 --budget 20 --days 7

Installer only (uses the master key from Parameter Store, so needs AWS):

  python scripts/keys.py issuer create maria    # admin key -> secrets/iss-maria.key
  python scripts/keys.py issuer list            # every admin user and its keys
  python scripts/keys.py issuer revoke maria    # delete maria's keys, then list admins

A key issuer creates every key and sends it to its owner privately (a direct
message, not a shared channel). A new key's value is written only to
secrets/<name>.key (mode 600, git-ignored) and never printed. `batch` makes
keys ws-<workshop>-01, -02, ... for a workshop organizer to hand out, and
writes them all to one file, secrets/<workshop>-keys.txt; running it again for
the same workshop continues the numbering and adds to that file. Admin keys are
never printed either.

Where the gateway is, first found of: --url, GATEWAY_URL (for example
http://localhost:4000 with scripts/tunnel.sh running), secrets/gateway-url
(written by deploy.sh), the stack's GatewayUrl output. The admin key is
secrets/issuer-key if that file exists (an issuer key made with `issuer
create`; secrets/organizer-key, its earlier name, also works), otherwise the
master key from Parameter Store. With secrets/gateway-url and an issuer key in
place no AWS access is needed: that is how a key issuer without AWS runs the
gateway (docs/issuer-no-aws.md). `organizer` is an older name for `issuer`.
"""

import argparse
import os
import pathlib
import re
import sys

import requests

SECRETS = pathlib.Path(__file__).resolve().parent.parent / "secrets"
URL_FILE = SECRETS / "gateway-url"
ISSUER_FILES = (SECRETS / "issuer-key", SECRETS / "organizer-key")  # the second: its earlier name
ISSUER_PREFIX = "iss-"  # issuer users and keys: iss-<name>, never clashing with a participant
OLD_PREFIX = "org-"  # the same, made before issuer keys were renamed from organizer keys
WORKSHOP_RE = re.compile(r"^[a-z0-9]{1,20}$")  # as the key service checks it
BUILTIN_ADMIN = "default_user_id"  # LiteLLM's own admin user (master key, Admin UI login)


def aws_client(service):
    """boto3 client, only for those with AWS access."""
    if "AWS_ROLE_ARN" in os.environ:
        sys.exit("A role from the environment would win over AWS_PROFILE: run `source gateway.env` first.")
    import boto3
    return boto3.client(service)


def stack_output(stack, key):
    outputs = aws_client("cloudformation").describe_stacks(StackName=stack)["Stacks"][0]["Outputs"]
    return next(o["OutputValue"] for o in outputs if o["OutputKey"] == key)


def gateway_url(stack, url=None):
    url = url or os.environ.get("GATEWAY_URL")
    if not url and URL_FILE.exists():
        url = URL_FILE.read_text().strip()
    return (url or stack_output(stack, "GatewayUrl")).rstrip("/")


def master_key(stack):
    return aws_client("ssm").get_parameter(
        Name=f"/{stack}/master-key", WithDecryption=True
    )["Parameter"]["Value"]


def admin_key(stack):
    """An issuer's own key if secrets/issuer-key (or organizer-key) exists, else the master key (AWS)."""
    for f in ISSUER_FILES:
        if f.exists():
            return f.read_text().strip()
    return master_key(stack)


class Gateway:
    def __init__(self, url, key):
        self.url = url
        self.headers = {"Authorization": f"Bearer {key}"}

    def call(self, method, path, **kw):
        r = requests.request(method, self.url + path, headers=self.headers, timeout=30, **kw)
        if not r.ok:
            sys.exit(f"{method} {path}: HTTP {r.status_code}: {r.text[:300]}")
        return r.json()

    def keys(self, **filters):
        rows, page = [], 1
        while True:
            data = self.call("GET", "/key/list", params={
                "return_full_object": "true", "size": 100, "page": page, **filters})
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


def batch(gw, args):
    """Keys ws-<workshop>-NN for an organizer to hand out, all in secrets/<workshop>-keys.txt."""
    name = args.workshop.strip().lower()
    if not WORKSHOP_RE.match(name):
        sys.exit("Workshop names are 1-20 lowercase letters and digits (no hyphen).")
    if args.count < 1:
        sys.exit("--count must be at least 1.")
    prefix = f"ws-{name}-"
    taken = [int(a[len(prefix):]) for a in (k.get("key_alias") or "" for k in gw.keys())
             if a.startswith(prefix) and a[len(prefix):].isdigit()]
    first = max(taken, default=0) + 1
    width = max(2, len(str(first + args.count - 1)))
    SECRETS.mkdir(mode=0o700, exist_ok=True)
    path = SECRETS / f"{name}-keys.txt"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    with os.fdopen(fd, "a") as f:
        expires = None
        for i in range(first, first + args.count):
            alias = f"{prefix}{i:0{width}d}"
            # user_id matters: see create(). metadata.workshop groups the keys in
            # `workshop.py status` and counts them against a sign-up cap.
            key = gw.call("POST", "/key/generate", json={
                "key_alias": alias, "user_id": alias, "max_budget": args.budget,
                "duration": f"{args.days}d",
                "metadata": {"purpose": "workshop", "workshop": name, "batch": True}})
            if expires is None:
                expires = (key.get("expires") or "never")[:10]
                f.write(f"# Workshop {name}: ${args.budget:g} per key, expires {expires}. "
                        "One key per person; keep this file private.\n")
            f.write(f"{alias} {key['key']}\n")
            f.flush()  # a failure part-way keeps every key already made
    last = f"{prefix}{first + args.count - 1:0{width}d}"
    print(f"created  {prefix}{first:0{width}d} .. {last}: ${args.budget:g} each, "
          f"expire {expires} -> secrets/{name}-keys.txt\n"
          f"Send that file privately (a direct message, or copy it into the organizer's hub home).")


def print_keys(rows):
    if not rows:
        print("No keys.")
    for k in sorted(rows, key=lambda k: k.get("key_alias") or ""):
        print(f"{k.get('key_alias') or '-':20} spend ${k.get('spend') or 0:8.4f} of "
              f"${k.get('max_budget')}  expires {(k.get('expires') or 'never')[:16]}  "
              f"{'BLOCKED' if k.get('blocked') else 'active'}")


def show(gw, args):
    print_keys(gw.keys())


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


def issuer_create(gw, args):
    user = ISSUER_PREFIX + args.name
    path = SECRETS / f"{user}.key"
    if path.exists():
        sys.exit(f"secrets/{user}.key already exists; revoke that issuer first.")
    if any(k.get("key_alias") == user for k in gw.keys()):
        sys.exit(f"The gateway already has a key named {user}.")
    # The role belongs to the user; every key of that user is an admin key.
    gw.call("POST", "/user/new", json={"user_id": user, "user_role": "proxy_admin",
                                       "auto_create_key": False})
    body = {"key_alias": user, "user_id": user, "metadata": {"purpose": "issuer"}}
    if args.days:
        body["duration"] = f"{args.days}d"
    key = gw.call("POST", "/key/generate", json=body)["key"]
    SECRETS.mkdir(mode=0o700, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(key + "\n")
    print(f"created  issuer {user}{f', expires in {args.days} days' if args.days else ''}"
          f" -> secrets/{user}.key\n"
          f"Send it privately with the gateway URL; they save it as secrets/issuer-key\n"
          f"(docs/issuer-no-aws.md). Revoke: python scripts/keys.py issuer revoke {args.name}")


def issuer_list(gw, args):
    users = gw.call("GET", "/user/list", params={"role": "proxy_admin", "page_size": 100}).get("users", [])
    print("Admin users (each of their keys can manage every key and workshop):")
    for u in sorted(users, key=lambda u: u["user_id"]):
        uid = u["user_id"]
        if uid == BUILTIN_ADMIN:
            print(f"  {uid:20} LiteLLM's built-in admin (master key, Admin UI login)")
            continue
        keys = gw.keys(user_id=uid)
        note = "" if uid.startswith((ISSUER_PREFIX, OLD_PREFIX)) else "   <- not made by `issuer create`"
        print(f"  {uid:20} {len(keys)} key(s){note}")
        for k in keys:
            print(f"      {k.get('key_alias') or '-':20} expires {(k.get('expires') or 'never')[:16]}  "
                  f"{'BLOCKED' if k.get('blocked') else 'active'}")


def issuer_revoke(gw, args):
    user = ISSUER_PREFIX + args.name
    tokens = [k["token"] for k in gw.keys(user_id=user)]
    if not tokens and gw.keys(user_id=OLD_PREFIX + args.name):  # made as an organizer key
        user = OLD_PREFIX + args.name
        tokens = [k["token"] for k in gw.keys(user_id=user)]
    if tokens:
        gw.call("POST", "/key/delete", json={"keys": tokens})
    gw.call("POST", "/user/delete", json={"user_ids": [user]})
    remove_local(user)
    print(f"revoked  issuer {user}: {len(tokens)} key(s) deleted, user removed")
    # Revoking stops the key; it does not undo what the key did. Show every admin
    # left, in case this one made others. Changes to proxy settings are not shown.
    issuer_list(gw, args)


def main():
    stack = os.environ.get("GATEWAY_STACK")
    if not stack:
        sys.exit("Run `source gateway.env` in the deployment folder first.")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--url", help="default: GATEWAY_URL, secrets/gateway-url, or the stack's GatewayUrl")
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
    b = sub.add_parser("batch", help="keys ws-<workshop>-01.. for an organizer to hand out")
    b.add_argument("--workshop", required=True, help="its name: lowercase letters and digits")
    b.add_argument("--count", type=int, required=True, help="how many keys")
    b.add_argument("--budget", type=float, required=True, help="USD per key")
    b.add_argument("--days", type=int, required=True, help="expiry in days, counted from now")
    o = sub.add_parser("issuer", aliases=["organizer"],
                       help="installer only: admin keys for key issuers without AWS")
    osub = o.add_subparsers(dest="org_cmd", required=True)
    oc = osub.add_parser("create")
    oc.add_argument("name", help="e.g. maria; the user and key are iss-<name>")
    oc.add_argument("--days", type=int, help="expiry in days (default: none; revoke when done)")
    osub.add_parser("list")
    osub.add_parser("revoke").add_argument("name")
    args = ap.parse_args()

    url = gateway_url(stack, args.url)
    if args.cmd in ("issuer", "organizer"):
        # Making and revoking admins takes the master key, never an issuer key.
        gw = Gateway(url, master_key(stack))
        return {"create": issuer_create, "list": issuer_list,
                "revoke": issuer_revoke}[args.org_cmd](gw, args)
    gw = Gateway(url, admin_key(stack))
    {
        "create": create,
        "update": update,
        "list": show,
        "models": models,
        "block": block,
        "unblock": lambda g, a: block(g, a, blocked=False),
        "delete": delete,
        "batch": batch,
    }[args.cmd](gw, args)


if __name__ == "__main__":
    main()
