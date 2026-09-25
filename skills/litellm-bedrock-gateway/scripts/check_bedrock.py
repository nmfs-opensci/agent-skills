"""Call each model in models.yaml directly on Bedrock, as you (not the gateway).

Run from the deployment folder after `source gateway.env`, before the first
deploy and whenever a model starts failing:

  python scripts/check_bedrock.py
  python scripts/check_bedrock.py --control us.amazon.nova-micro-v1:0

Each call is a few tokens (well under a cent). Run it with an identity allowed
aws-marketplace:Subscribe (an administrator): the first call to a Claude model
completes the account's Marketplace subscription, which the gateway's own role
cannot do. It also calls a control model that is not Anthropic's, because the
pattern of failures is the diagnosis:

  Claude fails, control works  -> Anthropic use-case form, subscription, or quota
  everything fails             -> the account itself: payment method, a hold,
                                  or a new-account verification still pending
"""

import argparse
import pathlib
import sys

import boto3
import yaml
from botocore.exceptions import ClientError

ROOT = pathlib.Path(__file__).resolve().parent.parent

HINTS = [
    ("use case details have not been submitted",
     "submit the Anthropic first-time-use form (see the skill's bedrock-readiness reference)"),
    ("not allowed for this account", "account-level block: payment method, or a hold on the account"),
    ("operation not allowed", "account-level block: payment method, or a hold on the account"),
    ("being verified", "new-account verification: wait (usually under 2 hours) and retry"),
    ("aws-marketplace", "this identity cannot subscribe: call once as an administrator"),
    ("too many tokens", "tokens-per-minute quota; request an increase in Service Quotas"),
    ("throttl", "tokens-per-minute quota; request an increase in Service Quotas"),
    ("invalid model identifier", "wrong ID for this Region: check with inspect_account.py"),
    ("on-demand throughput isn", "call it through an inference profile (inference_profile: us)"),
]


def hint(message):
    low = message.lower()
    return next((h for k, h in HINTS if k in low), "")


def call(rt, model_id):
    try:
        rt.converse(modelId=model_id,
                    messages=[{"role": "user", "content": [{"text": "Reply with the word OK."}]}],
                    inferenceConfig={"maxTokens": 10})
        return True, ""
    except ClientError as e:
        err = e.response["Error"]
        return False, f"{err['Code']}: {err['Message'][:160]}"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--models", default=str(ROOT / "models.yaml"))
    ap.add_argument("--control", default="openai.gpt-oss-20b-1:0",
                    help="a non-Anthropic model ID available in the Region")
    args = ap.parse_args()
    session = boto3.Session()
    if not session.region_name:
        sys.exit("Run `source gateway.env` first.")
    spec = yaml.safe_load(pathlib.Path(args.models).read_text())
    rt = session.client("bedrock-runtime")

    form = None
    try:
        form = session.client("bedrock").get_use_case_for_model_access()
    except ClientError as e:
        print(f"Anthropic use-case form: not found in this account ({e.response['Error']['Code']});")
        print("  in an Organization, a form submitted in the management account covers members")
    if form:
        print("Anthropic use-case form: on record for this account (its own, or its organization's)")

    targets = [("control", args.control)] + [
        (m["name"], (f"{m['inference_profile']}." if m.get("inference_profile") else "") + m["bedrock_id"])
        for m in spec["models"]]
    failed = 0
    for name, model_id in targets:
        ok, msg = call(rt, model_id)
        failed += not ok
        print(f"  {'ok  ' if ok else 'FAIL'} {name:28} {model_id}")
        if msg:
            print(f"       {msg}")
            if hint(msg):
                print(f"       -> {hint(msg)}")
    print("\nA pass today is not proof for next week: a new account can answer Claude for a")
    print("grace period before the use-case form is enforced. Re-run before the event.")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
