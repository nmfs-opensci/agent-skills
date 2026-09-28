"""Workshop key service: trade a workshop code and a hub username for a LiteLLM key.

Runs beside LiteLLM on the gateway (standard library only); Caddy sends
/workshop/* here. deploy.sh stores this file in Parameter Store and the
instance's refresh.sh installs it. Participants (through the hub script):

  POST /workshop/key    {"code": "...", "user": "<hub username>"}

The code picks the workshop: several can be open at once, each with its own
code, key cap, budget and expiry. It creates key alias ws-<workshop>-<user>
(also its user_id, and metadata.workshop) with that workshop's budget and
expiry. It never returns a key that already exists, so a public username is not
enough to get someone's key. Organizers open and close workshops
(scripts/workshop.py) with an admin key: the master key, or a key whose LiteLLM
user has the proxy_admin role, checked with LiteLLM on every request so a
revoked key stops working at once:

  GET  /workshop/admin    every workshop's settings and issued count (no codes)
  POST /workshop/admin    {"workshop", "code", "max_keys", "open_until", "budget", "days"}
                          (an empty code closes that workshop)

Settings live in STATE_FILE, so a restart keeps them. One request at a time,
which keeps the key count exact and makes guessing the code slow. Logs name
the user and outcome, never a key or code.
"""

import datetime as dt
import hmac
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

LITELLM = os.environ.get("LITELLM_URL", "http://litellm:4000").rstrip("/")
MASTER = os.environ["LITELLM_MASTER_KEY"]
STATE_FILE = os.environ.get("STATE_FILE", "/state/workshop.json")
PREFIX = "ws-"
USER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{0,38}$")  # GitHub username rules
# No hyphen, so ws-<workshop>-<user> can be read back unambiguously.
WORKSHOP_RE = re.compile(r"^[a-z0-9]{1,20}$")
CLOSED = {"code": "", "max_keys": 0, "open_until": "", "budget": 20.0, "days": 7, "opened_by": ""}


def load_state():
    """{"workshops": {name: settings}}. A state file from before named workshops is ignored."""
    try:
        with open(STATE_FILE) as f:
            workshops = json.load(f).get("workshops", {})
    except FileNotFoundError:
        workshops = {}
    return {"workshops": {n: {**CLOSED, **w} for n, w in workshops.items()}}


def save_state(state):
    tmp = STATE_FILE + ".tmp"
    with open(os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w") as f:
        json.dump(state, f)
    os.replace(tmp, STATE_FILE)


def litellm(method, path, body=None, key=MASTER, timeout=30):
    req = urllib.request.Request(
        LITELLM + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def workshop_keys():
    """{workshop name: set of aliases} for every key sign-up has issued."""
    issued, page = {}, 1
    while True:
        data = litellm("GET", f"/key/list?return_full_object=true&size=100&page={page}")
        for k in data.get("keys", []):
            name = (k.get("metadata") or {}).get("workshop")
            if name and (k.get("key_alias") or "").startswith(PREFIX):
                issued.setdefault(name, set()).add(k["key_alias"])
        if page >= (data.get("total_pages") or 1):
            return issued
        page += 1


def is_open(w, now):
    return bool(w["code"]) and not (w["open_until"] and now > dt.datetime.fromisoformat(w["open_until"]))


def same_code(a, b):
    return hmac.compare_digest(a.strip().lower().encode(), b.strip().lower().encode())


class Handler(BaseHTTPRequestHandler):
    server_version = "keyservice"

    def reply(self, status, **body):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n > 4096:
            raise ValueError("request too large")
        return json.loads(self.rfile.read(n) or b"{}")

    def admin(self):
        """Who is asking, if an admin: "master", the proxy_admin user's id, or None.

        Asks LiteLLM every time (no cache), so a blocked or deleted organizer
        key is refused at once. Admin calls are rare; the short timeout keeps a
        slow answer from holding up sign-up, which is served one at a time.
        """
        auth = self.headers.get("Authorization", "")
        if hmac.compare_digest(auth.encode(), f"Bearer {MASTER}".encode()):
            return "master"
        key = auth.removeprefix("Bearer ").strip()
        if not key.startswith("sk-"):
            return None
        try:
            info = litellm("GET", "/user/info", key=key, timeout=5)
            if info.get("user_info", {}).get("user_role") == "proxy_admin":
                return info.get("user_id") or "admin"
        except (OSError, ValueError):  # refused (401: bad, blocked or expired key) or unreachable
            pass
        time.sleep(1)  # as for a wrong workshop code: makes guessing slow
        log("admin: key refused")
        return None

    def do_GET(self):
        if self.path == "/workshop/health":
            return self.reply(200, ok=True)
        if self.path == "/workshop/admin" and self.admin():
            now, issued = dt.datetime.now(dt.timezone.utc), workshop_keys()
            return self.reply(200, workshops={
                name: {**{k: v for k, v in w.items() if k != "code"},
                       "open": is_open(w, now), "issued": sorted(issued.get(name, ()))}
                for name, w in sorted(load_state()["workshops"].items())})
        self.reply(404, error="Not found.")

    def do_POST(self):
        try:
            body = self.body()
        except ValueError:
            return self.reply(400, error="Bad request.")
        if self.path == "/workshop/admin" and (who := self.admin()):
            return self.configure(body, who)
        if self.path == "/workshop/key":
            try:
                return self.issue(body)
            except (OSError, ValueError, KeyError) as e:  # LiteLLM unreachable or refused
                log(f"error creating key: {type(e).__name__}")
                return self.reply(502, error="The gateway could not create a key. Ask the organizer.")
        self.reply(404, error="Not found.")

    def configure(self, body, who):
        name = str(body.get("workshop", "")).strip().lower()
        if not WORKSHOP_RE.match(name):
            return self.reply(400, error="Workshop names are 1-20 lowercase letters and digits.")
        state, now = load_state(), dt.datetime.now(dt.timezone.utc)
        w = {**state["workshops"].get(name, CLOSED), **{k: body[k] for k in CLOSED if k in body}}
        if w["code"] and any(n != name and is_open(o, now) and same_code(o["code"], w["code"])
                             for n, o in state["workshops"].items()):
            return self.reply(409, error="Another open workshop uses that code; choose another.")
        if w["code"]:
            w["opened_by"] = who
        state["workshops"][name] = w
        save_state(state)
        log(f"admin {who}: workshop {name} {'opened or changed' if w['code'] else 'closed'}")
        return self.reply(200, ok=True)

    def issue(self, body):
        state, now = load_state(), dt.datetime.now(dt.timezone.utc)
        user = str(body.get("user", "")).strip().lower()
        code = str(body.get("code", ""))
        workshops = state["workshops"]
        if not any(is_open(w, now) for w in workshops.values()):
            return self.reply(403, error="Workshop sign-up is closed.")
        matches = [n for n, w in workshops.items() if w["code"] and same_code(code, w["code"])]
        live = [n for n in matches if is_open(workshops[n], now)]
        if not live:
            if matches:
                return self.reply(403, error="Sign-up for that workshop has ended.")
            time.sleep(1)
            log(f"wrong code for {user[:40]!r}")
            return self.reply(403, error="That workshop code is not right.")
        name, w = live[0], workshops[live[0]]
        if not USER_RE.match(user):
            return self.reply(400, error="That does not look like a hub username.")
        alias = f"{PREFIX}{name}-{user}"
        issued = workshop_keys().get(name, set())
        if alias in issued:
            log(f"{name}/{user}: already issued")
            return self.reply(409, error=f"A key for {user} was already issued. "
                                         "If you lost it, ask the organizer.")
        if len(issued) >= int(w["max_keys"]):
            log(f"{name}/{user}: cap reached")
            return self.reply(403, error="All workshop keys are handed out. Ask the organizer.")
        key = litellm("POST", "/key/generate", {
            "key_alias": alias,
            # Without a user_id LiteLLM lets a key read other keys' details.
            "user_id": alias,
            "max_budget": float(w["budget"]),
            "duration": f"{int(w['days'])}d",
            "metadata": {"purpose": "workshop", "workshop": name, "hub_user": user},
        })
        log(f"{name}/{user}: key issued ({len(issued) + 1} of {w['max_keys']})")
        self.reply(200, key=key["key"], workshop=name, budget=float(w["budget"]),
                   expires=key.get("expires"))

    def log_message(self, fmt, *args):  # keep the default access log out of the output
        pass


def log(msg):
    print(f"{dt.datetime.now(dt.timezone.utc):%Y-%m-%dT%H:%M:%SZ} {msg}", file=sys.stderr, flush=True)


class Server(HTTPServer):
    def handle_error(self, request, client_address):
        log(f"error: {sys.exc_info()[0].__name__}")  # no traceback: it could hold request data


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    log(f"keyservice listening on {port}")
    Server(("", port), Handler).serve_forever()
