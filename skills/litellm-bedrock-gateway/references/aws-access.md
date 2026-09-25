# Signing in to AWS without long-lived keys

**Provisional for classic and organization accounts**: the commands are standard
AWS CLI, but this gateway has only been installed from a "new experience"
account (see `new-experience-accounts.md`). Record what differs when you install
elsewhere.

## Tools

- **AWS CLI v2, version 2.32 or later.** `aws login` does not exist earlier, and
  the PyPI `awscli` package is v1. On Linux without root, install into
  `~/.local`:

  ```bash
  curl -sSfL https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip -o awscliv2.zip
  unzip -q awscliv2.zip && ./aws/install -i ~/.local/aws-cli -b ~/.local/bin --update
  ```

- **boto3 with the `crt` extra** (`boto3[crt]`, in `scripts/requirements.txt`).
  Without it, boto3 cannot read credentials made by `aws login`.
- **session-manager-plugin**, only if you will use `scripts/tunnel.sh` (Admin UI
  behind the tunnel). It is not a pip package; install it from AWS's download
  page for the platform.

Make a virtual environment in the deployment folder and install only
`scripts/requirements.txt`; `gateway.env` activates `.venv` if it exists.

## Pick one way to sign in

In order of preference. None of them writes a long-lived secret to disk.

1. **IAM Identity Center (SSO)**, the usual choice in an organization:
   `aws configure sso` once, then `aws sso login --profile <name>`.
2. **`aws login`** with a console identity: `aws login --profile <name>`, or
   `aws login --remote --profile <name>` on a machine without a browser (open the
   printed link on your laptop, sign in, paste the code back). Sessions last up
   to 12 hours. Changing the password of the signed-in identity ends existing
   sessions (`LoginRefreshRequired`); just log in again.
3. **An assumed role** from one of the above, via a profile with `role_arn` and
   `source_profile`. Use this to work in a member account from a management
   account login:

   ```ini
   [profile gateway]
   role_arn = arn:aws:iam::<MEMBER_ACCOUNT_ID>:role/OrganizationAccountAccessRole
   source_profile = <the profile you log in with>
   region = us-east-2
   ```

   Always name the source profile in the login command
   (`aws login --profile <source>`), since `AWS_PROFILE` points at the role.

Do not create IAM access keys, and do not create a long-term Bedrock API key: it
silently creates an IAM user (`BedrockAPIKey-…`) that someone must later find
and delete.

## Clear injected credentials first

Many environments inject credentials that the AWS tools use **before** any
profile, so every command silently runs in another account:

- a JupyterHub or CI role: `AWS_ROLE_ARN` with `AWS_WEB_IDENTITY_TOKEN_FILE`;
- static keys: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`;
- `AWS_BEARER_TOKEN_BEDROCK`, a Bedrock API key: Bedrock calls go to whichever
  account made it, regardless of profile.

`gateway.env` unsets all of these. Source it in every new shell (and, for an
agent whose shell does not persist, prefix each command:
`source gateway.env && …`). Then confirm where you are before anything else:

```bash
aws sts get-caller-identity --query Arn --output text
```

## Permissions the installer needs

Enough to create a CloudFormation stack with an IAM role, EC2 networking and an
instance, Parameter Store entries, and Systems Manager commands; plus
`bedrock:*` read and invoke, and `aws-marketplace:Subscribe` for the first
Claude call (see `bedrock-readiness.md`). AdministratorAccess in a dedicated
account is the simple case. A narrower policy is possible but has not been
worked out; if the installer has one, run `inspect_account.py` and treat any
AccessDenied as the thing to resolve, not to work around.
