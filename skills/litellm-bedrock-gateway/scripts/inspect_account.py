"""Read-only inspection of an AWS account before building the gateway.

Run from the deployment folder after `source gateway.env`:

  python scripts/inspect_account.py

Makes no changes and prints no credentials; account IDs are shortened to their
last four digits. Checks who you are, whether an Organization can restrict the
account, whether the IDs in models.yaml exist here, Claude token quotas,
what already exists in the Region, and whether a budget alarm is set.
"""

import pathlib
import re
import sys

import boto3
import yaml
from botocore.exceptions import ClientError

session = boto3.Session()
REGION = session.region_name
MODELS = pathlib.Path(__file__).resolve().parent.parent / "models.yaml"


def mask(text):
    return re.sub(r"\b\d{8}(\d{4})\b", r"…\1", str(text))


def section(title):
    print(f"\n## {title}")


def attempt(label, fn):
    try:
        return fn()
    except ClientError as e:
        print(f"  {label}: {e.response['Error']['Code']}")
    except Exception as e:  # noqa: BLE001 - report and keep going
        print(f"  {label}: {type(e).__name__}: {e}")
    return None


def identity():
    section("Identity")
    me = session.client("sts").get_caller_identity()
    print(f"  profile {session.profile_name}, region {REGION}")
    print(f"  {mask(me['Arn'])}")
    org = attempt("organization",
                  lambda: session.client("organizations").describe_organization()["Organization"])
    if org:
        mgmt = org["MasterAccountId"] == me["Account"]
        print(f"  in an AWS Organization; this is {'its management' if mgmt else 'a member'} account")
        if not mgmt:
            print("  service control policies may restrict Regions or services here;")
            print("  ask the organization's admin, or read them from the management account")
        else:
            scps = attempt("SCPs", lambda: session.client("organizations").list_policies(
                Filter="SERVICE_CONTROL_POLICY")["Policies"])
            for p in scps or []:
                print(f"    SCP: {p['Name']}")
    return me


def served_models():
    section(f"models.yaml against this account ({REGION})")
    if not MODELS.exists():
        print("  no models.yaml here; skipped")
        return
    spec = yaml.safe_load(MODELS.read_text())
    if spec.get("region") != REGION:
        print(f"  models.yaml is for {spec.get('region')}, not {REGION}: IDs and prices differ by Region")
    br = session.client("bedrock")
    profiles = set()
    token = None
    while True:
        kw = {"typeEquals": "SYSTEM_DEFINED", "maxResults": 100, **({"nextToken": token} if token else {})}
        page = attempt("list inference profiles", lambda: br.list_inference_profiles(**kw))
        if not page:
            break
        profiles |= {p["inferenceProfileId"] for p in page["inferenceProfileSummaries"]}
        token = page.get("nextToken")
        if not token:
            break
    for m in spec.get("models", []):
        found = attempt(m["name"], lambda: br.get_foundation_model(
            modelIdentifier=m["bedrock_id"])["modelDetails"])
        status = found.get("modelLifecycle", {}).get("status", "?") if found else "NOT FOUND"
        prof = ""
        if m.get("inference_profile"):
            pid = f"{m['inference_profile']}.{m['bedrock_id']}"
            prof = f"  profile {'ok' if pid in profiles else 'NOT FOUND: ' + pid}"
        print(f"  {m['name']:28} {status}{prof}")


def quotas():
    section("Bedrock quotas mentioning Claude tokens per minute (applied values)")
    sq = session.client("service-quotas")
    found = 0
    for page in sq.get_paginator("list_service_quotas").paginate(ServiceCode="bedrock"):
        for q in page["Quotas"]:
            name = q["QuotaName"]
            if "Claude" in name and "tokens per minute" in name.lower():
                found += 1
                print(f"  {q['Value']:>12,.0f}  {name}")
    if not found:
        print("  none applied; defaults are in `list_aws_default_service_quotas`")
    print("  a value of 0 for a model means it cannot be used until a quota increase is granted")


def existing():
    section(f"Existing resources in {REGION}")
    ec2 = session.client("ec2")
    offered = ec2.describe_instance_type_offerings(
        LocationType="availability-zone",
        Filters=[{"Name": "instance-type", "Values": ["t4g.small"]}],
    )["InstanceTypeOfferings"]
    print(f"  t4g.small offered in {len(offered)} availability zones")
    inst = [i for r in ec2.describe_instances()["Reservations"] for i in r["Instances"]
            if i["State"]["Name"] != "terminated"]
    print(f"  EC2 instances (not terminated): {len(inst)}")
    eips = ec2.describe_addresses()["Addresses"]
    vpcs = ec2.describe_vpcs()["Vpcs"]
    print(f"  Elastic IPs: {len(eips)} (default quota 5), VPCs: {len(vpcs)} (default quota 5)")
    stacks = session.client("cloudformation").list_stacks(StackStatusFilter=[
        "CREATE_COMPLETE", "UPDATE_COMPLETE", "ROLLBACK_COMPLETE",
        "UPDATE_ROLLBACK_COMPLETE", "CREATE_FAILED", "DELETE_FAILED",
    ])["StackSummaries"]
    print(f"  CloudFormation stacks: {[s['StackName'] for s in stacks] or 'none'}")


def budgets(me):
    section("Spending guards")
    b = attempt("budgets", lambda: session.client("budgets", region_name="us-east-1").describe_budgets(
        AccountId=me["Account"]).get("Budgets", []))
    if b is not None:
        print(f"  AWS Budgets: {[x['BudgetName'] for x in b] or 'none (consider one as a backstop)'}")


def main():
    if not session.profile_name or not REGION:
        sys.exit("Run `source gateway.env` first.")
    me = identity()
    served_models()
    quotas()
    existing()
    budgets(me)


if __name__ == "__main__":
    main()
