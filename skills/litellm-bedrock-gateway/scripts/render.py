"""Render the deployable files from models.yaml, the one list of served models.

Run from the deployment folder after `source gateway.env`:

  python scripts/render.py                 # build/gateway.yaml, litellm-config.yaml, Caddyfile
  python scripts/render.py --url URL       # also build/participant-quickstart.md

Writes into build/:
  gateway.yaml              CloudFormation, with the instance role allowed exactly these models
  litellm-config.yaml       LiteLLM model_list (stored in Parameter Store by deploy.sh)
  Caddyfile                 HTTPS front end (stored in Parameter Store by deploy.sh)
  participant-quickstart.md with --url: setup for Claude Code, OpenCode, Copilot CLI

Reads GATEWAY_ADMIN_UI (public | tunnel) and AWS_REGION from the environment.
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
	respond @admin_ui "Admin UI is not published here" 403
"""
    return f"""# Generated by scripts/render.py. GATEWAY_HOST is set on the Caddy container.
{{$GATEWAY_HOST}} {{
{block_ui}
	reverse_proxy litellm:4000
}}
"""


def quickstart(spec, tiers, url):
    models = spec["models"]
    default = next(m for m in models if m["name"] == spec["default"])
    base = default["input_price"]
    rows = []
    for m in models:
        rel = m["input_price"] / base
        cost = "1×" if m is default else f"about {rel:.2g}×"
        label = m["label"] + (" (default)" if m is default else "")
        rows.append(f"| `{m['name']}` | {label} | {cost} |")
    exports = [f"export ANTHROPIC_MODEL={spec['default']}"]
    exports += [f"export ANTHROPIC_DEFAULT_{t.upper()}_MODEL={tiers[t]}" for t in TIERS if t in tiers]
    opencode = json.dumps({m["name"]: {} for m in models}, indent=2)
    opencode = "\n".join(("      " + line) if i else line for i, line in enumerate(opencode.splitlines()))
    text = (ROOT / "assets" / "participant-quickstart.md").read_text()
    for key, value in {
        "GATEWAY_URL": url.rstrip("/"),
        "DEFAULT_MODEL": spec["default"],
        "DEFAULT_LABEL": default["label"],
        "CLAUDE_CODE_EXPORTS": "\n".join(exports),
        "OPENCODE_MODELS": opencode,
        "MODEL_TABLE": "\n".join(rows),
    }.items():
        text = text.replace("{{" + key + "}}", value)
    if "{{" in text:
        fail("participant-quickstart.md has a placeholder render.py does not fill")
    return text


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--models", default=str(ROOT / "models.yaml"))
    ap.add_argument("--url", help="gateway URL; also writes build/participant-quickstart.md")
    args = ap.parse_args()
    spec, tiers = load(pathlib.Path(args.models))
    out = ROOT / "build"
    out.mkdir(exist_ok=True)
    files = {
        "gateway.yaml": template(spec["models"]),
        "litellm-config.yaml": litellm_config(spec),
        "Caddyfile": caddyfile(os.environ.get("GATEWAY_ADMIN_UI", "public")),
    }
    if args.url:
        files["participant-quickstart.md"] = quickstart(spec, tiers, args.url)
    for name, text in files.items():
        (out / name).write_text(text)
    print(f"render: {len(spec['models'])} models -> {', '.join('build/' + n for n in files)}")


if __name__ == "__main__":
    main()
