#!/usr/bin/env bash
# Forward localhost:4000 on this machine to LiteLLM on the instance through SSM
# Session Manager: the admin route to the Admin UI when GATEWAY_ADMIN_UI=tunnel.
# Needs session-manager-plugin. Runs until Ctrl-C.  Usage: scripts/tunnel.sh
set -euo pipefail
cd "$(dirname "$0")/.."
source ./gateway.env
PORT="${GATEWAY_LOCAL_PORT:-4000}"

ID=$(aws cloudformation describe-stacks --stack-name "$GATEWAY_STACK" \
  --query "Stacks[0].Outputs[?OutputKey=='InstanceId'].OutputValue" --output text)
echo "Tunnel: http://localhost:$PORT -> $ID:4000 (Admin UI at /ui; Ctrl-C to close)"
exec aws ssm start-session --target "$ID" \
  --document-name AWS-StartPortForwardingSession \
  --parameters "{\"portNumber\":[\"4000\"],\"localPortNumber\":[\"$PORT\"]}"
