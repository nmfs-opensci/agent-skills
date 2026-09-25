# Versions and dated facts

Everything here goes stale. Check it before relying on it, and update this file
(with the date) when you do.

| Item | Value | Checked |
|---|---|---|
| LiteLLM image | `ghcr.io/berriai/litellm-database:v1.102.1`, pinned by digest in the template | 2026-09-25 (latest release) |
| Caddy image | `caddy:2.11.4-alpine` (public ECR), pinned by digest | 2026-09-25 |
| Postgres image | `postgres:16-alpine` (public ECR), pinned by digest | 2026-09-25 |
| AMI | Amazon Linux 2023 arm64, latest via SSM public parameter | resolved at deploy |
| AWS CLI | v2 ≥ 2.32 for `aws login` (tested 2.37.1) | 2026-09-25 |
| boto3 | `boto3[crt]` (tested 1.43) | 2026-09-25 |
| Claude Code, OpenCode, Copilot CLI | tested with the versions current on 2026-09-25 (OpenCode 1.18.32, Copilot CLI 1.0.80) | 2026-09-25 |
| Models and prices | `assets/models.yaml`, us-east-2, Pricing API | 2026-09-25 |
| Claude Code prompt size | 34–53k tokens per request | 2026-09-25 |

## Checking the image digests

A digest pins the multi-architecture index (the template runs on arm64). For
images on public ECR:

```bash
repo=docker/library/caddy tag=2.11.4-alpine
tok=$(curl -s "https://public.ecr.aws/token/?scope=repository:$repo:pull" | python3 -c 'import sys,json;print(json.load(sys.stdin)["token"])')
curl -sI -H "Authorization: Bearer $tok" \
  -H "Accept: application/vnd.oci.image.index.v1+json,application/vnd.docker.distribution.manifest.list.v2+json" \
  "https://public.ecr.aws/v2/$repo/manifests/$tag" | grep -i docker-content-digest
```

Upgrade LiteLLM deliberately, in a test stack first, and rerun
`check_gateway.py --other ... --spend`: the scripts depend on its admin API, and
the key-isolation finding in `security.md` was tested on 1.102.1 only.
