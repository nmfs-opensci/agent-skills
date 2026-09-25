"""Verify a deployed gateway from the outside, the way participants reach it.

Run from the deployment folder after `source gateway.env`, with a test key
made by `python scripts/keys.py create gateway-check --budget 1 --days 1`:

  python scripts/check_gateway.py gateway-check
  python scripts/check_gateway.py gateway-check --spend      # also check spend is recorded
  python scripts/check_gateway.py gateway-check --other alice  # and that keys are isolated
  python scripts/check_gateway.py gateway-check --models claude-haiku-4-5-20251001

Checks, over HTTPS:
  - a request with no key is refused (401)
  - the test key can read its own balance and has a user_id; with --other, it
    cannot read that other key's details
  - the Admin UI is reachable or blocked, as GATEWAY_ADMIN_UI says
  - every served model answers a tool-use request, in both the OpenAI format
    (OpenCode, Copilot CLI) and the Anthropic format (Claude Code)
  - with --spend: after LiteLLM's ~1 minute write delay, each model's calls
    were recorded with a cost above $0. A $0 cost means budgets do nothing for
    that model: set its price in models.yaml.

Each model call is tiny (a few cents in total). Prints no key values.
"""

import argparse
import os
import pathlib
import sys
import time

import boto3
import requests

ROOT = pathlib.Path(__file__).resolve().parent.parent
TOOL_PROMPT = "What is the weather in Paris? Use the get_weather tool."
SCHEMA = {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}
results = []


def check(label, ok, detail=""):
    results.append(ok)
    print(f"  {'ok  ' if ok else 'FAIL'} {label}{'  ' + detail if detail else ''}")


def stack_output(stack, key):
    outputs = boto3.client("cloudformation").describe_stacks(StackName=stack)["Stacks"][0]["Outputs"]
    return next(o["OutputValue"] for o in outputs if o["OutputKey"] == key)


def openai_tool_call(url, headers, model):
    r = requests.post(f"{url}/v1/chat/completions", headers=headers, timeout=120, json={
        "model": model, "max_tokens": 200,
        "messages": [{"role": "user", "content": TOOL_PROMPT}],
        "tools": [{"type": "function", "function": {
            "name": "get_weather", "description": "Current weather for a city", "parameters": SCHEMA}}],
    })
    if not r.ok:
        return False, f"HTTP {r.status_code}: {r.text[:150]}"
    calls = r.json()["choices"][0]["message"].get("tool_calls") or []
    return bool(calls), "" if calls else "answered without calling the tool"


def anthropic_tool_call(url, headers, model):
    r = requests.post(f"{url}/v1/messages", timeout=120,
                      headers={**headers, "anthropic-version": "2023-06-01"}, json={
        "model": model, "max_tokens": 200,
        "messages": [{"role": "user", "content": TOOL_PROMPT}],
        "tools": [{"name": "get_weather", "description": "Current weather for a city",
                   "input_schema": SCHEMA}],
    })
    if not r.ok:
        return False, f"HTTP {r.status_code}: {r.text[:150]}"
    used = any(b.get("type") == "tool_use" for b in r.json().get("content", []))
    return used, "" if used else "answered without calling the tool"


def main():
    stack = os.environ.get("GATEWAY_STACK") or sys.exit("Run `source gateway.env` first.")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("key_name", help="name of a key in secrets/")
    ap.add_argument("--url", default=os.environ.get("GATEWAY_URL"))
    ap.add_argument("--models", nargs="+", help="default: every model the gateway serves")
    ap.add_argument("--other", help="a second key in secrets/ that the first must not be able to read")
    ap.add_argument("--spend", action="store_true", help="wait and check spend is recorded per model")
    args = ap.parse_args()
    url = (args.url or stack_output(stack, "GatewayUrl")).rstrip("/")
    key = (ROOT / "secrets" / f"{args.key_name}.key").read_text().strip()
    headers = {"Authorization": f"Bearer {key}"}
    print(f"Gateway {url}")

    r = requests.get(f"{url}/v1/models", timeout=30)
    check("no key is refused", r.status_code == 401, f"HTTP {r.status_code}")
    r = requests.get(f"{url}/key/info", headers=headers, timeout=30)
    check("key reads its own balance", r.ok, f"HTTP {r.status_code}")
    info = r.json() if r.ok else {}
    token = info.get("key")
    # Without a user_id LiteLLM lets the key read other user_id-less keys' details.
    check("key has a user_id (so it cannot read other keys)", bool(info.get("info", {}).get("user_id")))
    if args.other:
        other = requests.get(f"{url}/key/info", headers={
            "Authorization": f"Bearer {(ROOT / 'secrets' / f'{args.other}.key').read_text().strip()}"},
            timeout=30).json().get("key")
        r = requests.get(f"{url}/key/info", params={"key": other}, headers=headers, timeout=30)
        check(f"key cannot read {args.other}'s details", r.status_code == 403, f"HTTP {r.status_code}")
        r = requests.post(f"{url}/v2/key/info", json={"keys": [other]}, headers=headers, timeout=30)
        check(f"key cannot read {args.other}'s details (v2)", r.ok and not r.json().get("info"),
              f"HTTP {r.status_code}")
    ui = os.environ.get("GATEWAY_ADMIN_UI", "public")
    r = requests.get(f"{url}/ui/", timeout=30, allow_redirects=False)
    want = r.status_code == 403 if ui == "tunnel" else r.status_code < 400
    check(f"Admin UI is {'blocked' if ui == 'tunnel' else 'reachable'} (GATEWAY_ADMIN_UI={ui})",
          want, f"HTTP {r.status_code}")

    served = [m["id"] for m in requests.get(f"{url}/v1/models", headers=headers, timeout=30).json()["data"]]
    for model in args.models or served:
        for fmt, fn in (("openai", openai_tool_call), ("anthropic", anthropic_tool_call)):
            ok, detail = fn(url, headers, model)
            check(f"{model:28} tool use, {fmt} format", ok, detail)

    if args.spend and token:
        print("  waiting 75 s for LiteLLM to write spend ...")
        time.sleep(75)
        master = boto3.client("ssm").get_parameter(
            Name=f"/{stack}/master-key", WithDecryption=True)["Parameter"]["Value"]
        rows = requests.get(f"{url}/spend/logs", params={"api_key": token}, timeout=60,
                            headers={"Authorization": f"Bearer {master}"}).json()
        by_model = {}
        for row in rows if isinstance(rows, list) else []:
            name = row.get("model_group") or row.get("model")
            by_model[name] = by_model.get(name, 0) + (row.get("spend") or 0)
        for model in args.models or served:
            cost = by_model.get(model)
            check(f"{model:28} spend recorded", bool(cost),
                  "no rows yet" if cost is None else f"${cost:.5f}")

    failed = results.count(False)
    print(f"{len(results) - failed} passed, {failed} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
