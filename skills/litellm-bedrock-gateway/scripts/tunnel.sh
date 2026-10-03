#!/usr/bin/env bash
# Forward localhost:4000 on this machine to LiteLLM on the instance through SSM
# Session Manager: the admin route to the Admin UI when GATEWAY_ADMIN_UI=tunnel.
# Needs session-manager-plugin. Runs until Ctrl-C.  Usage: scripts/tunnel.sh
set -euo pipefail
cd "$(dirname "$0")/.."
source ./gateway.env
source scripts/guard.sh
PORT="${GATEWAY_LOCAL_PORT:-4000}"

# The right account, and an instance that belongs to this gateway's stack.
guard_account
ID=$(guard_instance_id)
echo "Tunnel: http://localhost:$PORT -> $ID:4000 (Admin UI at /ui; Ctrl-C to close)"
exec aws ssm start-session --target "$ID" \
  --document-name AWS-StartPortForwardingSession \
  --parameters "{\"portNumber\":[\"4000\"],\"localPortNumber\":[\"$PORT\"]}"
