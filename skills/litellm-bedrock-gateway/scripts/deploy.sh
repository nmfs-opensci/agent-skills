#!/usr/bin/env bash
# Create or update the gateway from models.yaml and gateway.env.
# Usage: scripts/deploy.sh   (from the deployment folder, after `aws login`)
# Renders the files and docs, creates missing secrets, stores the LiteLLM and
# Caddy configs and the workshop key service in Parameter Store, deploys the
# stack, writes the URL to secrets/gateway-url, and on an update reloads the
# running instance, so the running config always matches models.yaml.
set -euo pipefail
cd "$(dirname "$0")/.."
source ./gateway.env
source scripts/guard.sh
: "${GATEWAY_STACK:?set GATEWAY_STACK in gateway.env}"

# Before anything is written: the right account, and a stack name that is
# either free or already this gateway's.
guard_account
state=$(guard_stack)

python scripts/render.py
python scripts/make_secrets.py

# Plain String parameters (no secrets in them). Intelligent-Tiering moves a
# config over 4 KB to the Advanced tier ($0.05 a month) instead of failing.
# Advanced parameters still stop at 8 KB, so the key service is stored gzipped
# and base64-encoded; refresh.sh on the instance decodes it.
gzip -9c assets/keyservice.py | base64 | tr -d "\n" > build/keyservice.py.gz.b64
for p in litellm-config:build/litellm-config.yaml caddyfile:build/Caddyfile \
         keyservice:build/keyservice.py.gz.b64; do
  aws ssm put-parameter --name "/$GATEWAY_STACK/${p%%:*}" --type String \
    --tier Intelligent-Tiering --overwrite --value "file://${p#*:}" >/dev/null
  echo "stored   /$GATEWAY_STACK/${p%%:*}"
done

deploy_args=(--stack-name "$GATEWAY_STACK" --template-file build/gateway.yaml
  --parameter-overrides "DomainName=${GATEWAY_DOMAIN:-}"
  --capabilities CAPABILITY_IAM --no-fail-on-empty-changeset)

if [ "$state" = absent ]; then
  aws cloudformation deploy "${deploy_args[@]}"
else
  # An update is shown before it is applied. Anything CloudFormation would
  # remove or replace needs the stack name typed back, since a replaced
  # instance or Elastic IP loses keys, spend history or the URL.
  aws cloudformation deploy "${deploy_args[@]}" --no-execute-changeset >/dev/null
  cs=$(aws cloudformation list-change-sets --stack-name "$GATEWAY_STACK" --query \
    'reverse(sort_by(Summaries[?Status==`CREATE_COMPLETE`], &CreationTime))[0].ChangeSetId' --output text)
  if [ "$cs" = None ]; then
    echo "No changes to the stack."
  else
    echo "Planned changes to stack $GATEWAY_STACK (action, resource, type, replacement):"
    aws cloudformation describe-change-set --change-set-name "$cs" --query \
      'Changes[].ResourceChange.[Action,LogicalResourceId,ResourceType,Replacement]' --output text
    risky=$(aws cloudformation describe-change-set --change-set-name "$cs" --query \
      "length(Changes[?ResourceChange.Action=='Remove' || ResourceChange.Replacement=='True' || ResourceChange.Replacement=='Conditional'])" \
      --output text)
    if [ "$risky" != 0 ]; then
      read -r -p "This removes or replaces resources. Type the stack name to apply: " answer
      if [ "$answer" != "$GATEWAY_STACK" ]; then
        aws cloudformation delete-change-set --change-set-name "$cs"
        echo "Cancelled; nothing changed in the stack."
        exit 1
      fi
    fi
    aws cloudformation execute-change-set --change-set-name "$cs"
    aws cloudformation wait stack-update-complete --stack-name "$GATEWAY_STACK"
    echo "Stack $GATEWAY_STACK updated."
  fi
fi

url=$(aws cloudformation describe-stacks --stack-name "$GATEWAY_STACK" \
  --query "Stacks[0].Outputs[?OutputKey=='GatewayUrl'].OutputValue" --output text)
# The URL stays out of committed files (install repos are often public).
mkdir -p secrets && chmod 700 secrets
printf '%s\n' "$url" > secrets/gateway-url
echo "Gateway URL: $url  (saved in secrets/gateway-url)"
echo "Docs for this install: docs/   Hub script: hub/"

if [ "$state" = gateway ]; then
  scripts/instance.sh refresh
else
  echo "First boot installs Docker and starts the containers; allow ~3 minutes,"
  echo "then check with: scripts/instance.sh health"
fi
