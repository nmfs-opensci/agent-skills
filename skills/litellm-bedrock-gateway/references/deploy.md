# Deploying the gateway

## What gets built

One CloudFormation stack, so one command removes everything:

| Resource | Why |
|---|---|
| VPC, public subnet, internet gateway, route | its own network; no NAT gateway (the instance has a public address) |
| security group | inbound 443 and 80 (Let's Encrypt challenge and redirect); outbound 443 only |
| IAM role + instance profile | Bedrock invoke on exactly the served models; read its own `/<stack>/*` parameters; SSM management |
| EC2 `t4g.small` (arm64), Amazon Linux 2023, 20 GB encrypted gp3 | LiteLLM, Postgres and Caddy in Docker; IMDSv2 required, hop limit 2 so containers get the role's credentials |
| Elastic IP | a fixed address, so the HTTPS name survives stop/start |

Outside the stack, in Parameter Store under `/<stack>/`: SecureString
`master-key`, `db-password`, `salt-key`, `ui-password` (from
`make_secrets.py`, never overwritten, never printed) and String
`litellm-config`, `caddyfile` (from `render.py`, rewritten by every deploy).

Images are pinned by digest (`version-matrix.md`). HTTPS is Caddy with a Let's
Encrypt certificate for `<elastic ip>.sslip.io`, which needs no domain, or for
`GATEWAY_DOMAIN` if set.

Cost: about $0.57 a day running (instance, public IPv4, disk), about $5 a month
stopped (disk $1.60 plus Elastic IP $3.60). Bedrock tokens are separate and
metered per request (`costs.md`).

## Steps

1. `scripts/init_deployment.sh <folder>` (from the skill), then in that folder:
   make `.venv` with `scripts/requirements.txt`, edit `gateway.env` (profile,
   Region, `GATEWAY_STACK`, `GATEWAY_DOMAIN`, `GATEWAY_ADMIN_UI`) and
   `models.yaml`. Put the folder under version control if the installer wants
   it: `.gitignore` already excludes `secrets/`, `build/` and `.venv/`.
2. `source gateway.env`, confirm the identity, run `inspect_account.py` and
   `check_bedrock.py` (steps 3–4 of the skill).
3. **Show the installer what will be created and what it costs, and get a yes.**
4. `scripts/deploy.sh`. It renders, creates missing secrets, stores the configs,
   deploys the stack (about 3 minutes) and writes
   `build/participant-quickstart.md` with the gateway URL.
5. First boot installs Docker and starts the containers: allow 2–3 minutes, then
   `scripts/instance.sh health` should print
   `{"status":"healthy","db":"connected"}`.
6. With a domain: point its DNS A record at the Elastic IP (in the `GatewayUrl`
   output's address, or `aws ec2 describe-addresses`). Caddy retries the
   certificate until DNS resolves.
7. Verify (`verify.md`) before handing out a single key.

## Updating

Rerun `scripts/deploy.sh` after any change to `models.yaml` or `gateway.env`.
When the stack already exists it also runs `scripts/instance.sh refresh`, which
fetches the new LiteLLM config and Caddyfile on the instance and restarts the
containers. User data runs only at first boot and holds no model details, so the
instance is never replaced for a model change. Never edit
`/opt/litellm/config.yaml` on the instance by hand: the next deploy overwrites
it, and until then the running gateway and `models.yaml` disagree.

Changing `GATEWAY_DOMAIN` changes user data (the host name LiteLLM and Caddy are
told at first boot). CloudFormation documents a user-data change as an update
with interruption (stop and start), and user data does not rerun, so the new
name would never reach LiteLLM or Caddy. This has not been tested here. Choose
the domain before the first deploy; to change it later, tear down and rebuild, and tell participants the
new URL.

## Admin UI exposure (the installer's choice)

`GATEWAY_ADMIN_UI` in `gateway.env`:

- `public`: `https://<host>/ui`, user `admin`, password in
  `/<stack>/ui-password`. Organizers can watch spend from any browser. The
  login is on the internet, protected by a random 24-character password.
- `tunnel`: Caddy answers 403 on `/ui` and the login routes; the UI is at
  `http://localhost:4000/ui` while `scripts/tunnel.sh` runs. Every organizer who
  wants the UI then needs AWS access and session-manager-plugin.

Either way the master key is never typed into a browser. Show the password only
when needed:

```bash
aws ssm get-parameter --name "/$GATEWAY_STACK/ui-password" \
  --with-decryption --query Parameter.Value --output text
```
