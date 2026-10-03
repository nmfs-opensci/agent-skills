# Choosing and changing models

## One list

`models.yaml` in the deployment folder is the only list of served models.
`scripts/render.py` generates from it:

- the instance role's `InvokeServedModels` IAM statement (the server can call
  exactly these models and nothing else);
- LiteLLM's `model_list` (what the gateway serves, under what names, at what
  prices);
- the model table and tool settings in `docs/participant-quickstart.md`, and
  the model tiers in the hub script.

LiteLLM does **not** discover Bedrock models: whatever is not in `model_list`
does not exist for participants. The Admin UI's model dropdown shows LiteLLM's
built-in catalog, not what is served; do not manage models there (the template
does not set `STORE_MODEL_IN_DB`).

## Fields

| Field | Meaning |
|---|---|
| `name` | what clients ask for. Name Claude models by their **Anthropic API IDs** (`claude-sonnet-4-6`), so Claude Code shows the real name, context size and price; with aliases like `sonnet` it shows "Custom model". |
| `label` | human name for the quickstart table |
| `bedrock_id` | the foundation-model ID in this Region, verified with `inspect_account.py` |
| `inference_profile` | `us` (or another geographic prefix) to call through a cross-Region profile; required for current Claude models. `global` is refused (untested IAM). |
| `api` | `invoke` for Claude (Anthropic Messages on Bedrock), `converse` for other models |
| `cache` | add prompt-cache markers for OpenAI-style clients (Claude only) |
| `claude_code_tier` | `haiku`, `sonnet`, `opus`: which model Claude Code uses for each tier. `haiku` is required when any is set: Claude Code's background calls use it and fail if it is not served. |
| `input_price`, `output_price` | USD per million tokens, on-demand, in this Region |
| `price_source` | `litellm` (default for `invoke`) or `config` (default for `converse`) |
| `cache_write_price`, `cache_write_1h_price`, `cache_read_price` | USD per million tokens for 5-minute cache writes, 1-hour cache writes and cache reads. Required for a `cache: true` model priced in `config`; passed to LiteLLM as `cache_creation_input_token_cost`, `cache_creation_input_token_cost_above_1hr` and `cache_read_input_token_cost`. |

## Prices decide whether budgets work

LiteLLM records spend from its own cost map unless the config gives a price. For
Claude through `us.` profiles its map was right, including prompt-cache write
and read rates, so `price_source: litellm`. For several open models it had no
price for us-east-2, or only another Region's; a missing price records **$0 and
the budget never triggers**. So `converse` models pass `input_price` and
`output_price` to LiteLLM.

**A Claude model newer than the pinned LiteLLM has no entry in its cost map.**
Check before adding one: the map for the pinned version is
`model_prices_and_context_window.json` at that tag in the LiteLLM repository,
and the key to look for is `us.<bedrock_id>`. On 2026-10-02, LiteLLM 1.102.1
knew Haiku 4.5 and Fable 5.1 but had no entry at all for Sonnet 5.5 or Opus
5.5. Such a model needs `price_source: config` and, because a coding agent's
spend is mostly cache writes and reads, all three cache prices; `render.py`
refuses a cached config-priced model without them. Take them from the Pricing
API's regional `standard` usage types (`USW2_cache_write_tokens_standard`,
`..._1h_standard`, `USW2_cache_read_tokens_standard`, and
`USW2_input_tokens_standard` / `USW2_output_tokens_standard` for the base
rates); the `_global_` types are what `global.` profiles pay. Provisional:
tested on one deployment, where `check_gateway.py --spend` recorded both
models above $0; whether the cache rates are applied to a real cache-heavy
session on these two models has not been measured.

Take prices from the **AWS Pricing API**, not from memory or a web page:

```python
import boto3, json
p = boto3.client("pricing", region_name="us-east-1")
for page in p.get_paginator("get_products").paginate(
        ServiceCode="AmazonBedrockFoundationModels",
        Filters=[{"Type": "TERM_MATCH", "Field": "regionCode", "Value": "us-east-2"}]):
    for s in page["PriceList"]:
        d = json.loads(s)
        a = d["product"]["attributes"]
        # print a.get("model"), a.get("usagetype") and the OnDemand priceDimensions
```

Claude appears under `AmazonBedrockFoundationModels` with usage types such as
`USE2_InputTokenCount-Units` (regional, what `us.` profiles pay; about 10% above
`_Global`). After a deploy, `check_gateway.py --spend` confirms each model
records a cost above $0.

## Choosing

- **Default to a cheap capable model.** In the reference deployment the
  organizers chose Claude Haiku 4.5 as the default, with Sonnet and Opus
  available; see `costs.md` for why the per-request floor matters.
- **Test tool use, not just chat.** A coding agent is useless on a model that
  will not call tools. `check_gateway.py` sends a tool-use request in both the
  OpenAI and Anthropic formats to every model. Open models passed that test but
  were less reliable in real sessions: one answered with an invented file
  content instead of calling the read tool until told to use it.
- **Newest is not always available.** Check quota (`inspect_account.py`) and
  access (`check_bedrock.py`) before promising a model.

## Changing models on a running gateway

Edit `models.yaml`, run `check_bedrock.py` if a model is new, then
`scripts/deploy.sh`. It updates the IAM role in place, stores the new config in
Parameter Store and reloads the running instance (a restart of about 30 seconds:
warn participants). Keys that were limited to named models keep only those; a
key with no model list gets every served model. Update `docs/participant-quickstart.md`
for participants if names changed.
