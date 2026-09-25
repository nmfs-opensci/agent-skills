# Special case: AWS "new experience" (Builder ID) accounts

Everything here was observed in one account in September 2026 (limited-release
signup). AWS may change it; treat it as a field report.

## How to recognize one

The account was created with "Sign up for AWS (new)". The owner signs in with an
**AWS Builder ID**, work is organized in **projects**, there are **spend
limits**, and **IAM users cannot have console passwords**: humans are the owner
or invited team members. Ask the installer how the account was made before
assuming it is a classic account.

## Facts that shape the install

- **Sign in with `aws login --remote`** as the owner: open the link, sign in with
  the Builder ID (not root), choose the session (after the step below, the
  **Management Account**), paste the code back, and answer **No** to the
  agent-toolkit prompt.
- **The project Region is pinned by contact country**: US → **us-east-2 (Ohio)**.
  Build there. `us.` inference profiles route across US Regions anyway.
- **"Activate advanced features" is irreversible.** It turns the account into an
  **AWS Organization**: a management account (billing; keep workloads out of it),
  a **member account for the project** that AWS names for you, and an Identity
  delegated-admin account. A Region guardrail (service control policy) stays
  attached; in the observed case most services worked only in us-east-2, while
  Bedrock calls were exempt. SCPs never apply to the management account.
- **The AWS-created project account has no `OrganizationAccountAccessRole`**, so
  the management account cannot reach it. Accounts made with Organizations →
  Create account do have it; invited ones do not. Add it from inside the member
  account, in its IAM console: Roles → Create role → *AWS account* → *Another
  AWS account* = the management account ID → policy **AdministratorAccess** →
  name `OrganizationAccountAccessRole`. Use the console wizard rather than
  pasting JSON through a terminal: wrapped lines and stray spaces break the
  policy. Then chain a profile to it with `source_profile` (see
  `aws-access.md`); one `aws login` to the management account covers every
  member account.
- **Each account needs its own payment method.** Without one, Bedrock refuses
  every model, Amazon's included, and opening the account in the console shows
  an "appeal" / "Something went wrong" page. That page is an account-level hold,
  not a permissions problem.
- **All accounts share the root email**, so signing in as root with it always
  lands in the management account.

After this, continue with `bedrock-readiness.md` in the member account.
