#!/usr/bin/env bash
# Create or update the gateway from models.yaml and gateway.env.
# Usage: scripts/deploy.sh   (from the deployment folder, after `aws login`)
# Renders the files, creates missing secrets, stores the LiteLLM and Caddy
# configs in Parameter Store, deploys the stack, and on an update reloads the
# running instance, so the running config always matches models.yaml.
set -euo pipefail
cd "$(dirname "$0")/.."
source ./gateway.env
: "${GATEWAY_STACK:?set GATEWAY_STACK in gateway.env}"

python scripts/render.py
python scripts/make_secrets.py

existed=no
aws cloudformation describe-stacks --stack-name "$GATEWAY_STACK" >/dev/null 2>&1 && existed=yes

# Plain String parameters (no secrets in them). Intelligent-Tiering moves a
# config over 4 KB to the Advanced tier ($0.05 a month) instead of failing.
for p in litellm-config:build/litellm-config.yaml caddyfile:build/Caddyfile; do
  aws ssm put-parameter --name "/$GATEWAY_STACK/${p%%:*}" --type String \
    --tier Intelligent-Tiering --overwrite --value "file://${p#*:}" >/dev/null
  echo "stored   /$GATEWAY_STACK/${p%%:*}"
done

aws cloudformation deploy \
  --stack-name "$GATEWAY_STACK" \
  --template-file build/gateway.yaml \
  --parameter-overrides "DomainName=${GATEWAY_DOMAIN:-}" \
  --capabilities CAPABILITY_IAM \
  --no-fail-on-empty-changeset

url=$(aws cloudformation describe-stacks --stack-name "$GATEWAY_STACK" \
  --query "Stacks[0].Outputs[?OutputKey=='GatewayUrl'].OutputValue" --output text)
python scripts/render.py --url "$url" >/dev/null
echo "Gateway URL: $url"
echo "Participant instructions: build/participant-quickstart.md"

if [ "$existed" = yes ]; then
  scripts/instance.sh refresh
else
  echo "First boot installs Docker and starts the containers; allow ~3 minutes,"
  echo "then check with: scripts/instance.sh health"
fi
