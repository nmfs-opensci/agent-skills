#!/usr/bin/env bash
# Operate the gateway instance.  Usage: scripts/instance.sh COMMAND
#   status    state and type
#   stop      stop it (keys, budgets and spend survive on its disk)
#   start     start it again (same URL: the Elastic IP stays)
#   health    ask LiteLLM, on the instance, whether it is ready
#   refresh   reload the LiteLLM config and Caddyfile from Parameter Store
# health and refresh run over SSM Run Command, so nothing reads the logs,
# which can contain the database URL.
set -euo pipefail
cd "$(dirname "$0")/.."
source ./gateway.env
: "${GATEWAY_STACK:?set GATEWAY_STACK in gateway.env}"

ID=$(aws cloudformation describe-stacks --stack-name "$GATEWAY_STACK" \
  --query "Stacks[0].Outputs[?OutputKey=='InstanceId'].OutputValue" --output text)

on_instance() {
  local cid
  cid=$(aws ssm send-command --instance-ids "$ID" --document-name AWS-RunShellScript \
    --parameters "commands=[\"$1\"]" --query Command.CommandId --output text)
  aws ssm wait command-executed --command-id "$cid" --instance-id "$ID" 2>/dev/null || true
  aws ssm get-command-invocation --command-id "$cid" --instance-id "$ID" \
    --query '[Status,StandardOutputContent,StandardErrorContent]' --output text
}

case "${1:-status}" in
  stop)    aws ec2 stop-instances --instance-ids "$ID" --output text >/dev/null
           aws ec2 wait instance-stopped --instance-ids "$ID" ;;
  start)   aws ec2 start-instances --instance-ids "$ID" --output text >/dev/null
           aws ec2 wait instance-running --instance-ids "$ID" ;;
  health)  on_instance "curl -s --max-time 10 localhost:4000/health/readiness" ; exit ;;
  refresh) on_instance "/opt/litellm/refresh.sh"
           echo "LiteLLM restarts in ~30 s; then: scripts/instance.sh health" ; exit ;;
  status)  ;;
  *) echo "usage: $0 status|stop|start|health|refresh" >&2; exit 2 ;;
esac
aws ec2 describe-instances --instance-ids "$ID" \
  --query 'Reservations[0].Instances[0].[InstanceId,State.Name,InstanceType]' --output text
