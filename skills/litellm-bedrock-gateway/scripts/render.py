"""Render the deployable files from models.yaml, the one list of served models.

Run from the deployment folder after `source gateway.env`:

  python scripts/render.py

Writes into build/ (git-ignored):
  gateway.yaml              CloudFormation, with the instance role allowed exactly these models
  litellm-config.yaml       LiteLLM model_list (stored in Parameter Store by deploy.sh)
  Caddyfile                 HTTPS front end (stored in Parameter Store by deploy.sh)

and this install's docs and hub script, meant to be committed:
  docs/participant-quickstart.md  setup for Claude Code, OpenCode, Copilot CLI
  docs/hub-quickstart.md          JupyterHub sign-up, for participants
  docs/organizer.md               keys, sign-up, spend
  docs/organizer-no-aws.md        running the gateway without AWS access
  hub/<GATEWAY_HUB_COMMAND>       the JupyterHub sign-up script

None of them holds the gateway URL, because install repos are often public:
the URL lives in secrets/gateway-url (written by deploy.sh), and the hub
script reads it from <command>.url beside it on the hub.

Reads AWS_REGION, GATEWAY_STACK, GATEWAY_ADMIN_UI (public | tunnel) and the
GATEWAY_HUB_* / GATEWAY_WORKSHOP_* / GATEWAY_ORGANIZER settings (gateway.env).
"""

import argparse
import json
import os
import pathlib
import re
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
MARKER = "# @@MODEL_RESOURCES@@"
NAME = re.compile(r"^[a-z0-9][a-z0-9.-]*$")
TIERS = ("opus", "sonnet", "haiku")
COMMAND = re.compile(r"^[a-z][a-z0-9-]{1,39}$")
DOCS = ("participant-quickstart.md", "hub-quickstart.md", "organizer.md", "organizer-no-aws.md")


def fail(msg):
    sys.exit(f"render: {msg}")


def load(path):
    spec = yaml.safe_load(path.read_text())
    models = spec.get("models") or fail(f"{path}: no models")
    region = spec.get("region") or fail(f"{path}: no region")
    env_region = os.environ.get("AWS_REGION")
    if env_region and env_region != region:
        fail(f"models.yaml is for {region} but AWS_REGION is {env_region}; "
             "IDs and prices are per Region, so re-verify them before changing Region")
    names, tiers = set(), {}
    for m in models:
        n = m.get("name") or fail("a model has no name")
        if not NAME.match(n):
            fail(f"{n!r}: names use lowercase letters, digits, '.' and '-'")
        if n in names:
            fail(f"{n}: listed twice")
        names.add(n)
        for k in ("bedrock_id", "api", "label"):
            m.get(k) or fail(f"{n}: missing {k}")
        if m["api"] not in ("invoke", "converse"):
            fail(f"{n}: api must be invoke or converse")
        profile = m.get("inference_profile")
        if profile == "global":
            fail(f"{n}: global inference profiles need a different IAM policy that has not "
                 "been tested with this template; use a geographic profile such as us")
        for k in ("input_price", "output_price"):
            if not isinstance(m.get(k), (int, float)):
                fail(f"{n}: {k} (USD per million tokens) is required")
        # LiteLLM's cost map knows Claude's cache rates; other models must be
        # priced here or their spend records as $0 and budgets do nothing.
        m.setdefault("price_source", "litellm" if m["api"] == "invoke" else "config")
        if m["price_source"] not in ("litellm", "config"):
            fail(f"{n}: price_source must be litellm or config")
        t = m.get("claude_code_tier")
        if t:
            if t not in TIERS:
                fail(f"{n}: claude_code_tier must be one of {TIERS}")
            if t in tiers:
                fail(f"claude_code_tier {t} is set on both {tiers[t]} and {n}")
            tiers[t] = n
    if spec.get("default") not in names:
        fail("default must be the name of a listed model")
    if tiers and "haiku" not in tiers:
        fail("Claude Code runs background tasks on its haiku tier: set claude_code_tier: haiku on one model")
    return spec, tiers


def bedrock_model(m):
    prefix = f"{m['inference_profile']}." if m.get("inference_profile") else ""
    return f"{prefix}{m['bedrock_id']}"


def iam_resources(models, indent):
    pad = " " * indent
    lines = []
    for m in models:
        if m.get("inference_profile"):
            lines.append(f"- !Sub arn:aws:bedrock:${{AWS::Region}}:${{AWS::AccountId}}:"
                         f"inference-profile/{bedrock_model(m)}")
            lines.append(f"- arn:aws:bedrock:*::foundation-model/{m['bedrock_id']}")
        else:
            lines.append(f"- !Sub arn:aws:bedrock:${{AWS::Region}}::foundation-model/{m['bedrock_id']}")
    return "\n".join(pad + line for line in lines)


def template(models):
    src = (ROOT / "assets" / "gateway-template.yaml").read_text()
    lines = src.splitlines()
    at = [i for i, line in enumerate(lines) if line.strip() == MARKER]
    if len(at) != 1:
        fail(f"expected one {MARKER} line in gateway-template.yaml")
    i = at[0]
    indent = len(lines[i]) - len(lines[i].lstrip())
    lines[i] = iam_resources(models, indent)
    return "\n".join(lines) + "\n"


def litellm_config(spec):
    entries = []
    for m in spec["models"]:
        p = {"model": ("bedrock/converse/" if m["api"] == "converse" else "bedrock/") + bedrock_model(m),
             "aws_region_name": spec["region"]}
        if m.get("cache"):
            # Cache markers for OpenAI-style clients; LiteLLM stands down when
            # the client sets its own (Claude Code does).
            p["cache_control_injection_points"] = [
                {"location": "message", "role": "system"},
                {"location": "message", "index": -1},
            ]
        if m["price_source"] == "config":
            p["input_cost_per_token"] = float(f"{m['input_price'] / 1e6:.6g}")
            p["output_cost_per_token"] = float(f"{m['output_price'] / 1e6:.6g}")
        entries.append({"model_name": m["name"], "litellm_params": p})
    config = {
        "model_list": entries,
        "general_settings": {
            "master_key": "os.environ/LITELLM_MASTER_KEY",
            "database_url": "os.environ/DATABASE_URL",
        },
        "litellm_settings": {"drop_params": True},
    }
    head = "# Generated by scripts/render.py from models.yaml. Do not edit here.\n"
    return head + yaml.safe_dump(config, sort_keys=False)


def caddyfile(admin_ui):
    if admin_ui not in ("public", "tunnel"):
        fail("GATEWAY_ADMIN_UI must be public or tunnel")
    block_ui = ""
    if admin_ui == "tunnel":
        block_ui = """
		# Admin UI and its login only through the SSM tunnel (scripts/tunnel.sh).
		@admin_ui path /ui /ui/* /login /v2/login /sso/* /fallback/login
		respond @admin_ui "Admin UI is not published here" 403"""
    # handle blocks are exclusive: /workshop/* goes to the key service, the rest
    # to LiteLLM. The Admin UI block sits inside the second, because Caddy runs
    # handle before a top-level respond.
    return f"""# Generated by scripts/render.py. GATEWAY_HOST is set on the Caddy container.
{{$GATEWAY_HOST}} {{
	handle /workshop/* {{
		reverse_proxy keyservice:8080
	}}
	handle {{{block_ui}
		reverse_proxy litellm:4000
	}}
}}
"""


def settings():
    """Install settings from gateway.env, with the workshop defaults."""
    env = os.environ.get
    s = {
        "stack": env("GATEWAY_STACK") or fail("GATEWAY_STACK is not set: source gateway.env first"),
        "command": env("GATEWAY_HUB_COMMAND") or "claude-workshop",
        "hub_dir": (env("GATEWAY_HUB_DIR") or "~/shared/workshop").rstrip("/"),
        "hub_admin_dir": (env("GATEWAY_HUB_ADMIN_DIR") or env("GATEWAY_HUB_DIR") or "~/shared/workshop").rstrip("/"),
        "organizer": env("GATEWAY_ORGANIZER") or "the organizer",
    }
    if not COMMAND.match(s["command"]):
        fail("GATEWAY_HUB_COMMAND: lowercase letters, digits and '-', starting with a letter")
    if s["command"] == "claude":
        fail("GATEWAY_HUB_COMMAND must not be claude: participants keep their own claude")
    for k, default, kind in (("budget", "20", float), ("days", "7", int), ("max", "20", int)):
        raw = env(f"GATEWAY_WORKSHOP_{k.upper()}") or default
        try:
            s[k] = kind(raw)
        except ValueError:
            fail(f"GATEWAY_WORKSHOP_{k.upper()}={raw!r} is not a number")
    return s


def fill(text, values, what):
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", str(value))
    if "{{" in text:
        fail(f"{what} has a placeholder render.py does not fill")
    return text


def claude_code_exports(spec, tiers):
    exports = [f"export ANTHROPIC_MODEL={spec['default']}"]
    exports += [f"export ANTHROPIC_DEFAULT_{t.upper()}_MODEL={tiers[t]}" for t in TIERS if t in tiers]
    return "\n".join(exports)


def docs(spec, tiers, s):
    """This install's docs and hub script, keyed by path in the deployment folder."""
    models = spec["models"]
    default = next(m for m in models if m["name"] == spec["default"])
    base = default["input_price"]
    rows = []
    for m in models:
        rel = m["input_price"] / base
        cost = "1×" if m is default else f"about {rel:.2g}×"
        label = m["label"] + (" (default)" if m is default else "")
        rows.append(f"| `{m['name']}` | {label} | {cost} |")
    opencode = json.dumps({m["name"]: {} for m in models}, indent=2)
    opencode = "\n".join(("      " + line) if i else line for i, line in enumerate(opencode.splitlines()))
    # A stronger model to suggest in the hub quickstart's /model example.
    stronger = tiers.get("sonnet") or next((m["name"] for m in models if m is not default), spec["default"])
    values = {
        "DEFAULT_MODEL": spec["default"],
        "DEFAULT_LABEL": default["label"],
        "STRONGER_MODEL": stronger,
        "CLAUDE_CODE_EXPORTS": claude_code_exports(spec, tiers),
        "OPENCODE_MODELS": opencode,
        "MODEL_TABLE": "\n".join(rows),
        "STACK": s["stack"],
        "HUB_COMMAND": s["command"],
        "HUB_DIR": s["hub_dir"],
        "HUB_ADMIN_DIR": s["hub_admin_dir"],
        "ORGANIZER": s["organizer"],
        "BUDGET": f"{s['budget']:g}",
        "DAYS": s["days"],
        "MAX_KEYS": s["max"],
    }
    out = {f"docs/{name}": fill((ROOT / "assets" / name).read_text(), values, name) for name in DOCS}
    out[f"hub/{s['command']}"] = fill((ROOT / "assets" / "hub-signup.sh").read_text(), values, "hub-signup.sh")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--models", default=str(ROOT / "models.yaml"))
    args = ap.parse_args()
    spec, tiers = load(pathlib.Path(args.models))
    if "haiku" not in tiers:
        fail("the hub script runs Claude Code: set claude_code_tier: haiku on one model")
    files = {
        "build/gateway.yaml": template(spec["models"]),
        "build/litellm-config.yaml": litellm_config(spec),
        "build/Caddyfile": caddyfile(os.environ.get("GATEWAY_ADMIN_UI", "public")),
        **docs(spec, tiers, settings()),
    }
    for name, text in files.items():
        path = ROOT / name
        path.parent.mkdir(exist_ok=True)
        path.write_text(text)
        if name.startswith("hub/"):
            path.chmod(0o755)
    print(f"render: {len(spec['models'])} models -> build/, docs/, hub/")


if __name__ == "__main__":
    main()
