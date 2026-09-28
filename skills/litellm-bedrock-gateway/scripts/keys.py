"""Manage participants' LiteLLM virtual keys.

Run from the deployment folder after `source gateway.env`:

  python scripts/keys.py create alice bob carol --budget 20 --days 7
  python scripts/keys.py create dana --budget 5 --days 2 --models claude-haiku-4-5-20251001
  python scripts/keys.py list
  python scripts/keys.py update alice --budget 30 --days 3   # new total budget; expiry from now
  python scripts/keys.py block alice                         # or: unblock alice
  python scripts/keys.py delete alice
  python scripts/keys.py models                              # what the gateway serves

Installer only (uses the master key from Parameter Store, so needs AWS):

  python scripts/keys.py organizer create maria    # admin key -> secrets/org-maria.key
  python scripts/keys.py organizer list            # every admin user and its keys
  python scripts/keys.py organizer revoke maria    # delete maria's keys, then list admins

The organizer creates every key and sends it to its owner privately (a direct
message, not a shared channel). A new key's value is written only to
secrets/<name>.key (mode 600, git-ignored) and never printed. Admin keys are
never printed either.

Where the gateway is, first found of: --url, GATEWAY_URL (for example
http://localhost:4000 with scripts/tunnel.sh running), secrets/gateway-url
(written by deploy.sh), the stack's GatewayUrl output. The admin key is
secrets/organizer-key if that file exists (an organizer key made with
`organizer create`), otherwise the master key from Parameter Store. With
secrets/gateway-url and secrets/organizer-key in place no AWS access is needed:
that is how an organizer without AWS runs the gateway (docs/organizer-no-aws.md).
"""

import argparse
import os
import pathlib
import sys

import requests

SECRETS = pathlib.Path(__file__).resolve().parent.parent / "secrets"
URL_FILE = SECRETS / "gateway-url"
ORGANIZER_FILE = SECRETS / "organizer-key"
ORG_PREFIX = "org-"  # organizer users and keys: org-<name>, never clashing with a participant
BUILTIN_ADMIN = "default_user_id"  # LiteLLM's own admin user (master key, Admin UI login)


def aws_client(service):
    """boto3 client, only for organizers with AWS access."""
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
    """An organizer's own key if secrets/organizer-key exists, else the master key (AWS)."""
    if ORGANIZER_FILE.exists():
        return ORGANIZER_FILE.read_text().strip()
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


def organizer_create(gw, args):
    user = ORG_PREFIX + args.name
    path = SECRETS / f"{user}.key"
    if path.exists():
        sys.exit(f"secrets/{user}.key already exists; revoke that organizer first.")
    if any(k.get("key_alias") == user for k in gw.keys()):
        sys.exit(f"The gateway already has a key named {user}.")
    # The role belongs to the user; every key of that user is an admin key.
    gw.call("POST", "/user/new", json={"user_id": user, "user_role": "proxy_admin",
                                       "auto_create_key": False})
    body = {"key_alias": user, "user_id": user, "metadata": {"purpose": "organizer"}}
    if args.days:
        body["duration"] = f"{args.days}d"
    key = gw.call("POST", "/key/generate", json=body)["key"]
    SECRETS.mkdir(mode=0o700, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(key + "\n")
    print(f"created  organizer {user}{f', expires in {args.days} days' if args.days else ''}"
          f" -> secrets/{user}.key\n"
          f"Send it privately with the gateway URL; they save it as secrets/organizer-key\n"
          f"(docs/organizer-no-aws.md). Revoke: python scripts/keys.py organizer revoke {args.name}")


def organizer_list(gw, args):
    users = gw.call("GET", "/user/list", params={"role": "proxy_admin", "page_size": 100}).get("users", [])
    print("Admin users (each of their keys can manage every key and workshop):")
    for u in sorted(users, key=lambda u: u["user_id"]):
        uid = u["user_id"]
        if uid == BUILTIN_ADMIN:
            print(f"  {uid:20} LiteLLM's built-in admin (master key, Admin UI login)")
            continue
        keys = gw.keys(user_id=uid)
        note = "" if uid.startswith(ORG_PREFIX) else "   <- not made by `organizer create`"
        print(f"  {uid:20} {len(keys)} key(s){note}")
        for k in keys:
            print(f"      {k.get('key_alias') or '-':20} expires {(k.get('expires') or 'never')[:16]}  "
                  f"{'BLOCKED' if k.get('blocked') else 'active'}")


def organizer_revoke(gw, args):
    user = ORG_PREFIX + args.name
    tokens = [k["token"] for k in gw.keys(user_id=user)]
    if tokens:
        gw.call("POST", "/key/delete", json={"keys": tokens})
    gw.call("POST", "/user/delete", json={"user_ids": [user]})
    remove_local(user)
    print(f"revoked  organizer {user}: {len(tokens)} key(s) deleted, user removed")
    # Revoking stops the key; it does not undo what the key did. Show every admin
    # left, in case this one made others. Changes to proxy settings are not shown.
    organizer_list(gw, args)


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
    o = sub.add_parser("organizer", help="installer only: admin keys for organizers without AWS")
    osub = o.add_subparsers(dest="org_cmd", required=True)
    oc = osub.add_parser("create")
    oc.add_argument("name", help="e.g. maria; the user and key are org-<name>")
    oc.add_argument("--days", type=int, help="expiry in days (default: none; revoke when done)")
    osub.add_parser("list")
    osub.add_parser("revoke").add_argument("name")
    args = ap.parse_args()

    url = gateway_url(stack, args.url)
    if args.cmd == "organizer":
        # Making and revoking admins takes the master key, never an organizer key.
        gw = Gateway(url, master_key(stack))
        return {"create": organizer_create, "list": organizer_list,
                "revoke": organizer_revoke}[args.org_cmd](gw, args)
    gw = Gateway(url, admin_key(stack))
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
