#!/usr/bin/env bash
# Delete everything the gateway created: the stack (network, instance, disk,
# role, Elastic IP), its Parameter Store entries, and the local key files.
# Keys, budgets and spend history are lost; export them first if you need them
# (python scripts/keys.py list > usage.txt).  Usage: scripts/teardown.sh
set -euo pipefail
cd "$(dirname "$0")/.."
source ./gateway.env
: "${GATEWAY_STACK:?set GATEWAY_STACK in gateway.env}"

read -r -p "Delete stack '$GATEWAY_STACK' and /$GATEWAY_STACK/* in $AWS_REGION? Type the stack name: " answer
[ "$answer" = "$GATEWAY_STACK" ] || { echo "Cancelled."; exit 1; }

aws cloudformation delete-stack --stack-name "$GATEWAY_STACK"
aws cloudformation wait stack-delete-complete --stack-name "$GATEWAY_STACK"
echo "Stack deleted."
for name in master-key db-password salt-key ui-password litellm-config caddyfile; do
  aws ssm delete-parameter --name "/$GATEWAY_STACK/$name" 2>/dev/null \
    && echo "Deleted /$GATEWAY_STACK/$name" || true
done
# Includes JupyterLab's .ipynb_checkpoints copies of key files.
rm -rf secrets build
echo "Teardown complete."
