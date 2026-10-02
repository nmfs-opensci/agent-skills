# Safety checks shared by the scripts that change AWS (deploy, teardown,
# instance, tunnel). Source it after gateway.env. The gateway is often built in
# an account that also runs other infrastructure, such as a JupyterHub, so a
# wrong profile or a mistyped GATEWAY_STACK must stop here rather than update,
# stop or delete something that is not this gateway.

# Every gateway stack carries this description; nothing else should.
GATEWAY_DESCRIPTION_PREFIX="LiteLLM gateway to Amazon Bedrock"

guard_fail() { echo "guard: $*" >&2; exit 1; }

# The credentials must belong to the account recorded in gateway.env.
guard_account() {
  [ -n "${GATEWAY_ACCOUNT:-}" ] ||
    guard_fail "set GATEWAY_ACCOUNT in gateway.env to the 12-digit account ID the gateway lives in"
  local actual
  actual=$(aws sts get-caller-identity --query Account --output text) ||
    guard_fail "cannot read the signed-in identity; sign in first"
  [ "$actual" = "$GATEWAY_ACCOUNT" ] ||
    guard_fail "signed in to account $actual, but gateway.env says GATEWAY_ACCOUNT=$GATEWAY_ACCOUNT"
}

# Prints "absent" or "gateway"; refuses outright if a stack of that name exists
# but was not built from the gateway template.
guard_stack() {
  local desc
  if ! desc=$(aws cloudformation describe-stacks --stack-name "$GATEWAY_STACK" \
        --query 'Stacks[0].Description' --output text 2>/dev/null); then
    echo absent
    return
  fi
  case "$desc" in
    "$GATEWAY_DESCRIPTION_PREFIX"*) echo gateway ;;
    *) guard_fail "stack '$GATEWAY_STACK' exists but is not a LiteLLM gateway; refusing to touch it" ;;
  esac
}

# The instance ID from the stack's outputs, checked to belong to that stack.
guard_instance_id() {
  [ "$(guard_stack)" = gateway ] || guard_fail "no gateway stack named '$GATEWAY_STACK'"
  local id owner
  id=$(aws cloudformation describe-stacks --stack-name "$GATEWAY_STACK" \
    --query "Stacks[0].Outputs[?OutputKey=='InstanceId'].OutputValue" --output text)
  [[ "$id" =~ ^i-[0-9a-f]+$ ]] || guard_fail "stack '$GATEWAY_STACK' has no InstanceId output"
  owner=$(aws ec2 describe-instances --instance-ids "$id" --query \
    "Reservations[0].Instances[0].Tags[?Key=='aws:cloudformation:stack-name'].Value | [0]" --output text)
  [ "$owner" = "$GATEWAY_STACK" ] ||
    guard_fail "instance $id is not tagged as part of stack '$GATEWAY_STACK'"
  echo "$id"
}
