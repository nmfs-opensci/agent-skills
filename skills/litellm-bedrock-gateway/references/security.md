# Security choices and why

- **No AWS credentials for participants.** The only AWS credential is the
  instance role, allowed to invoke exactly the served models and to read its own
  `/<stack>/*` parameters. A leaked participant key can spend at most its
  budget, until it expires or is blocked.
- **Secrets never printed.** `make_secrets.py` generates the master key, database
  password, salt key and UI password straight into Parameter Store
  (SecureString). User data writes them only into root-only env files on the
  instance. Health is checked with `instance.sh health` (SSM Run Command), not by
  reading container logs, which can contain the database URL.
- **The salt key is never rotated.** Changing it makes LiteLLM's stored keys
  unreadable; `make_secrets.py` refuses to overwrite.
- **Keys have a `user_id`.** Tested on LiteLLM 1.102.1: a key could read another
  key's alias, spend and budget through `GET /key/info?key=<hash>` and
  `POST /v2/key/info` whenever **neither key had a `user_id`** (the ownership
  check compares two empty values). With `user_id` set, both return 403 or
  nothing. `keys.py` sets `user_id` to the key's name, and `check_gateway.py`
  checks it. Blocking `?key=` in Caddy was tried and rejected: it missed
  `/v2/key/info` and broke the Admin UI, which uses `/key/info?key=` itself.
  Hashes are not normally discoverable by participants (`/key/list` and
  `/spend/logs` refuse them), so this was a defence-in-depth fix.
- **Workshop sign-up gives nothing to someone who only knows a username.** The
  key service never returns a key that already exists, refuses wrong codes
  slowly, caps the number of keys, and closes by itself; its admin route needs
  an admin key, checked with LiteLLM on every request (`workshop-signup.md`).
- **Key issuers without AWS get their own revocable admin key, never the master
  key or the Admin UI password**, neither of which can be revoked or rotated
  here. `keys.py issuer revoke` stops a key at once, but not what it already
  did: an admin key can create more admins (the revoke lists them) and change
  proxy settings (nothing detects that). Tested on LiteLLM 1.102.1
  (`workshop-signup.md`).
- **A workshop organizer with a batch of keys holds no admin key.** The hub
  script's `--status` asks each key about itself only. Participant keys cannot
  delete, block or update any key, their own included (401, tested on 1.102.1).
  Letting keys delete themselves through an `internal_user` owner was
  rejected: such a key can also mint new keys without budget or expiry
  (`workshop-signup.md`, "Key batches").
- **A key works from anywhere that has the gateway URL**, not only the hub.
  Per-key budget and expiry bound a leaked key until it is blocked.
- **No committed file holds the gateway URL**, because install repos are
  often public. It lives in `secrets/gateway-url`.
- **Admin UI with its own password**, so the master key is never typed into a
  browser; published or tunnel-only by the installer's choice (`deploy.md`).
- **Minimal network.** Inbound 443 and 80 only (80 serves the certificate
  challenge and redirects); outbound 443 only; IMDSv2 required.
- **Pinned images** (by digest), so a rebuild runs the same software.
- **Keys go out privately and are never shared.** Organizers create them; key
  files are mode 600 and git-ignored; teardown deletes them, including
  JupyterLab checkpoint copies.
- **Short lives.** Give keys an expiry that ends with the event, and stop or
  tear down the instance when it is not in use.

## Sharing an account with other infrastructure

The gateway is often built in an account that already runs something people
depend on, such as the JupyterHub its participants use. Tested 2026-10-02 in
such an account (an EKS-based hub in the same Region):

- **Every script that changes AWS checks where it is.** `scripts/guard.sh`,
  sourced by `deploy.sh`, `teardown.sh`, `instance.sh` and `tunnel.sh`,
  refuses to run unless the signed-in account is `GATEWAY_ACCOUNT`, and
  refuses any existing stack named `GATEWAY_STACK` whose description is not
  the gateway template's. Without it, a mistyped stack name would let
  `deploy.sh` replace another stack's resources with the gateway's and
  `teardown.sh` delete it. `instance.sh` and `tunnel.sh` also check that the
  instance carries the stack's `aws:cloudformation:stack-name` tag.
- **An update is shown before it is applied.** `deploy.sh` creates a change
  set for an existing stack, prints it, and needs the stack name typed back
  if anything would be removed or replaced.
- **Teardown deletes only by exact name.** It lists the stack's resources
  and the seven parameters it will delete before asking; CloudFormation
  removes only what the stack created. It prints the two hub files to remove
  by hand, and nothing else.
- **The instance role cannot read other parameters.**
  `AmazonSSMManagedInstanceCore` allows `ssm:GetParameter` and
  `ssm:GetParameters` on every parameter in the account, so the template adds
  an explicit Deny for everything outside `/<stack>/*`. Checked with the IAM
  policy simulator: its own parameters `allowed`, any other `explicitDeny`.
- **Nothing in the template is account-wide or named.** It makes its own VPC
  (no peering), and its role, profile and security group get generated names,
  so none can collide with existing ones.
- **Shared quotas.** The gateway takes one VPC and one Elastic IP (default
  quotas 5 each per Region) and 2 vCPUs of the on-demand Standard quota.
  `inspect_account.py` reports the counts; check there is room for the other
  infrastructure to grow (an EKS cluster rebuilt with highly available NAT
  needs a VPC and up to three Elastic IPs).
- **The installer's own credentials are the remaining risk.** Installing
  needs broad rights in the account, and an agent working with them could
  change anything. A policy limited to the gateway's resources has not been
  worked out; until it is, keep to the scripts and ask before any other AWS
  command that is not read-only.
