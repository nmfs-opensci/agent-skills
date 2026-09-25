# Getting Bedrock to answer: the per-account checklist

This checklist took two days to learn the first time. Work through it **per
account**: in an Organization, accounts do not all inherit each other's
settings. Then run `python scripts/check_bedrock.py` as an administrator and do
not deploy until every model passes.

## The checklist

1. **Payment method on the account itself.** Without one, Bedrock refuses
   *every* model, Amazon's included: `Operation not allowed`, or "Access to
   Bedrock models is not allowed for this account". In the observed
   Organization, each member account needed its own card.
2. **Anthropic first-time-use (use-case) form**, for Claude only. It is hard to
   find in the console; submit it with the API (`bedrock` client,
   `put_use_case_for_model_access(formData=...)`, where `formData` is JSON with
   `companyName`, `companyWebsite`, `intendedUsers`, `industryOption`,
   `otherIndustryOption`, `useCases`). The installer fills in the answers: they
   are statements to Anthropic on the organization's behalf, so never invent
   them. In an Organization, the form submitted in the **management account
   covers the member accounts**. Missing form: `Model use case details have not
   been submitted`. `check_bedrock.py` reports whether one is on record.
3. **Marketplace subscription.** It completes automatically on the first call to
   each Claude model, but only from an identity allowed
   `aws-marketplace:Subscribe` (AdministratorAccess is). The gateway's instance
   role cannot do it, so make one administrator call per Claude model before the
   server relies on it: `check_bedrock.py` does exactly that.
4. **New-account verification.** A brand-new account may answer "being
   verified, normally takes less than 2 hours". Wait it out.
5. **Quotas** (Service Quotas → Amazon Bedrock → tokens per minute).
   `inspect_account.py` lists them. New accounts have had **0** for the newest
   Claude models while older ones had quota; a model at 0 cannot be served until
   an increase is granted, which can take days. For a large group, compare the
   quota with the load (see `operate.md`).

## Two traps

- **The first-call grace period.** A new account can answer Claude for a while
  before the use-case form is enforced, then start refusing. A success on day one
  proves little: re-run `check_bedrock.py` a day or two before the event.
- **Blaming the form for an account problem.** Always call a non-Anthropic model
  as well (`check_bedrock.py` calls `openai.gpt-oss-20b-1:0` by default; pass
  `--control` for another). If *it* fails too, the problem is the account
  (payment method, hold, verification), not the Anthropic form.

## Reading `check_bedrock.py`

| Result | Likely cause |
|---|---|
| everything fails, including the control | payment method, a hold, verification pending |
| only Claude fails, "use case details" | the Anthropic form |
| only Claude fails, mentions `aws-marketplace` | the identity cannot subscribe; call as an administrator |
| one model throttled or "too many tokens" | quota for that model |
| "invalid model identifier" | wrong ID for this Region; check with `inspect_account.py` |
| "on-demand throughput isn't supported" | call it through an inference profile (`inference_profile: us`) |

## Related Bedrock facts

- Current Claude models are called through **inference profiles**: `us.` (and
  other geographic prefixes) route within that geography; `global.` routes
  anywhere and is cheaper, but needs a different IAM policy that this template
  has not been tested with, so `render.py` refuses it.
- **bedrock-mantle** (`https://bedrock-mantle.<region>.api.aws/v1`) is Bedrock's
  OpenAI-compatible endpoint, used with a Bedrock API key. It does not need the
  Anthropic form, but in the observed account Claude had 0 quota there. The
  gateway uses the regular `bedrock-runtime` endpoint.
- Short-term Bedrock API keys expire within 12 hours; long-term ones create an
  IAM user. Neither is needed for the gateway.
