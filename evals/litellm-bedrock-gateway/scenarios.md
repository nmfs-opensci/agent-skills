# Evaluation scenarios: litellm-bedrock-gateway

Give the agent one scenario at a time, with no other context. None may create
billed AWS resources without the evaluator's explicit approval, and none may
touch a gateway people are using. Scenarios 1, 2, 4, 6 and 7 are planning or
diagnosis exercises that need no AWS access.

## 1. Classic organization account

> Our organization has an AWS account in an Organization and I have an IAM
> Identity Center admin role. We run a two-day coding clinic for 25 people
> next month and want them on Claude Code with a spending cap each. Set it up.

## 2. Everything refuses

> I made a new AWS account last week, submitted the Anthropic form, and every
> Bedrock call fails with "Operation not allowed" — even Amazon Nova. What's
> wrong?

## 3. Add a model to a running gateway

> Participants want Claude Sonnet 5 on the gateway we deployed with this skill.
> Add it.

(Run against a throwaway test deployment. Sonnet 5 had 0 quota in the reference
account.)

## 4. Spend stays at zero

> A participant says Claude Code works fine, but `keys.py list` shows $0 spend on
> their key after an hour.

## 5. Budget advice

> How much budget should each of 20 people get for a three-hour workshop, and
> which model should be the default?

## 6. Worked yesterday

> Claude worked through the gateway on Monday. Today every Claude request fails
> with "Model use case details have not been submitted", but GPT-OSS still
> works.

## 7. Shortcut request

> Just give everyone an AWS access key with Bedrock permissions, it's simpler.

## 8. After the event

> The workshop is over. Shut it all down.
