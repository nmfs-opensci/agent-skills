#!/usr/bin/env bash
# Delete everything the gateway created: the stack (network, instance, disk,
# role, Elastic IP), its Parameter Store entries, and the local key files.
# Keys, budgets and spend history are lost; export them first if you need them
# (python scripts/keys.py list > usage.txt).  Usage: scripts/teardown.sh
#
# It deletes only by exact name: the one stack, which must be a gateway in
# GATEWAY_ACCOUNT, and the seven parameters the gateway writes. CloudFormation
# removes only resources the stack itself created, so nothing else in a shared
# account is touched. Nothing here uses wildcards or tag searches to find
# things to delete.
set -euo pipefail
cd "$(dirname "$0")/.."
source ./gateway.env
source scripts/guard.sh
: "${GATEWAY_STACK:?set GATEWAY_STACK in gateway.env}"

guard_account
[ "$(guard_stack)" = gateway ] || { echo "No gateway stack named '$GATEWAY_STACK' in $AWS_REGION."; exit 1; }

PARAMS=(master-key db-password salt-key ui-password litellm-config caddyfile keyservice)
echo "Account $GATEWAY_ACCOUNT, Region $AWS_REGION. This deletes stack '$GATEWAY_STACK' and its resources:"
aws cloudformation list-stack-resources --stack-name "$GATEWAY_STACK" \
  --query 'StackResourceSummaries[].[ResourceType,PhysicalResourceId]' --output text | sed 's/^/  /'
echo "and these parameters:"
printf "  /$GATEWAY_STACK/%s\n" "${PARAMS[@]}"
read -r -p "Type the stack name to delete all of the above: " answer
[ "$answer" = "$GATEWAY_STACK" ] || { echo "Cancelled."; exit 1; }

aws cloudformation delete-stack --stack-name "$GATEWAY_STACK"
aws cloudformation wait stack-delete-complete --stack-name "$GATEWAY_STACK"
echo "Stack deleted."
for name in "${PARAMS[@]}"; do
  aws ssm delete-parameter --name "/$GATEWAY_STACK/$name" 2>/dev/null \
    && echo "Deleted /$GATEWAY_STACK/$name" || true
done
# Includes JupyterLab's .ipynb_checkpoints copies of key files.
rm -rf secrets build
echo "Teardown complete."
if [ -n "${GATEWAY_HUB_COMMAND:-}" ]; then
  echo "On the hub, remove only this gateway's two files (and leave every other"
  echo "file in that folder alone):"
  echo "  rm ${GATEWAY_HUB_ADMIN_DIR}/${GATEWAY_HUB_COMMAND} ${GATEWAY_HUB_ADMIN_DIR}/${GATEWAY_HUB_COMMAND}.url"
fi
