"""Workshop key service: trade a workshop code and a hub username for a LiteLLM key.

Runs beside LiteLLM on the gateway (standard library only); Caddy sends
/workshop/* here. deploy.sh stores this file in Parameter Store and the
instance's refresh.sh installs it. Participants (through the hub script):

  POST /workshop/key    {"code": "...", "user": "<hub username>"}

creates key alias ws-<user> (also its user_id) with the workshop budget and expiry. It never
returns a key that already exists, so a public username is not enough to get
someone's key. The organizer opens and closes sign-up with the master key
(scripts/workshop.py):

  GET|POST /workshop/admin    {"code", "max_keys", "open_until", "budget", "days"}

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
CLOSED = {"code": "", "max_keys": 0, "open_until": "", "budget": 20.0, "days": 7}


def load_state():
    try:
        with open(STATE_FILE) as f:
            return {**CLOSED, **json.load(f)}
    except FileNotFoundError:
        return dict(CLOSED)


def save_state(state):
    tmp = STATE_FILE + ".tmp"
    with open(os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w") as f:
        json.dump(state, f)
    os.replace(tmp, STATE_FILE)


def litellm(method, path, body=None):
    req = urllib.request.Request(
        LITELLM + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {MASTER}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def workshop_aliases():
    aliases, page = set(), 1
    while True:
        data = litellm("GET", f"/key/list?return_full_object=true&size=100&page={page}")
        aliases |= {k.get("key_alias") or "" for k in data.get("keys", [])}
        if page >= (data.get("total_pages") or 1):
            return {a for a in aliases if a.startswith(PREFIX)}
        page += 1


def closed_reason(state, now):
    if not state["code"]:
        return "Workshop sign-up is closed."
    if state["open_until"] and now > dt.datetime.fromisoformat(state["open_until"]):
        return "Workshop sign-up has ended."
    return None


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

    def is_admin(self):
        auth = self.headers.get("Authorization", "")
        return hmac.compare_digest(auth.encode(), f"Bearer {MASTER}".encode())

    def do_GET(self):
        if self.path == "/workshop/health":
            return self.reply(200, ok=True)
        if self.path == "/workshop/admin" and self.is_admin():
            return self.reply(200, **load_state(), issued=sorted(workshop_aliases()))
        self.reply(404, error="Not found.")

    def do_POST(self):
        try:
            body = self.body()
        except ValueError:
            return self.reply(400, error="Bad request.")
        if self.path == "/workshop/admin" and self.is_admin():
            state = {**load_state(), **{k: body[k] for k in CLOSED if k in body}}
            save_state(state)
            log("admin: settings changed")
            return self.reply(200, ok=True)
        if self.path == "/workshop/key":
            try:
                return self.issue(body)
            except (OSError, ValueError, KeyError) as e:  # LiteLLM unreachable or refused
                log(f"error creating key: {type(e).__name__}")
                return self.reply(502, error="The gateway could not create a key. Ask the organizer.")
        self.reply(404, error="Not found.")

    def issue(self, body):
        state, now = load_state(), dt.datetime.now(dt.timezone.utc)
        user = str(body.get("user", "")).strip().lower()
        if reason := closed_reason(state, now):
            return self.reply(403, error=reason)
        if not hmac.compare_digest(str(body.get("code", "")).strip().lower().encode(),
                                   state["code"].strip().lower().encode()):
            time.sleep(1)
            log(f"wrong code for {user[:40]!r}")
            return self.reply(403, error="That workshop code is not right.")
        if not USER_RE.match(user):
            return self.reply(400, error="That does not look like a hub username.")
        alias = PREFIX + user
        issued = workshop_aliases()
        if alias in issued:
            log(f"{user}: already issued")
            return self.reply(409, error=f"A key for {user} was already issued. "
                                         "If you lost it, ask the organizer.")
        if len(issued) >= int(state["max_keys"]):
            log(f"{user}: cap reached")
            return self.reply(403, error="All workshop keys are handed out. Ask the organizer.")
        key = litellm("POST", "/key/generate", {
            "key_alias": alias,
            # Without a user_id LiteLLM lets a key read other keys' details.
            "user_id": alias,
            "max_budget": float(state["budget"]),
            "duration": f"{int(state['days'])}d",
            "metadata": {"purpose": "workshop", "hub_user": user},
        })
        log(f"{user}: key issued ({len(issued) + 1} of {state['max_keys']})")
        self.reply(200, key=key["key"], budget=float(state["budget"]), expires=key.get("expires"))

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
