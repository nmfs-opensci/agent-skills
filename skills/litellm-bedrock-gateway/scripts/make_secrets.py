"""Create the gateway's secrets in SSM Parameter Store, once.

Run from the deployment folder after `source gateway.env` (deploy.sh does it):

  python scripts/make_secrets.py

Creates SecureString parameters /<GATEWAY_STACK>/master-key, db-password,
salt-key and ui-password with random values if they do not already exist.
Existing values are never overwritten: changing the salt key would make
LiteLLM's stored keys unreadable. Values are never printed.
"""

import os
import secrets
import sys

import boto3
from botocore.exceptions import ClientError

GENERATORS = {
    # LiteLLM expects keys to start with "sk-".
    "master-key": lambda: "sk-" + secrets.token_urlsafe(32),
    # Hex only, so it can sit in a postgresql:// URL without escaping.
    "db-password": lambda: secrets.token_hex(24),
    "salt-key": lambda: "sk-" + secrets.token_urlsafe(32),
    # Admin UI login (user "admin"), separate from the master key.
    "ui-password": lambda: secrets.token_urlsafe(18),
}


def main():
    stack = os.environ.get("GATEWAY_STACK") or sys.exit("Run `source gateway.env` first.")
    ssm = boto3.client("ssm")
    for name, make in GENERATORS.items():
        path = f"/{stack}/{name}"
        try:
            ssm.put_parameter(Name=path, Value=make(), Type="SecureString", Overwrite=False)
            print(f"created  {path}")
        except ClientError as e:
            if e.response["Error"]["Code"] != "ParameterAlreadyExists":
                raise
            print(f"exists   {path}")


if __name__ == "__main__":
    main()
