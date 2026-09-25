#!/usr/bin/env bash
# Start a deployment folder: a copy of these scripts and templates plus the two
# files you edit (gateway.env, models.yaml).  Usage: scripts/init_deployment.sh DIR
# The copy is deliberate: a running gateway should not change because the
# skill was updated. Never overwrites an existing gateway.env or models.yaml.
set -euo pipefail
dest="${1:?usage: init_deployment.sh DIR}"
skill="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$dest/scripts" "$dest/assets"
cp "$skill"/scripts/*.py "$skill"/scripts/*.sh "$skill"/scripts/requirements.txt "$dest/scripts/"
cp "$skill"/assets/gateway-template.yaml "$skill"/assets/participant-quickstart.md "$dest/assets/"
[ -e "$dest/gateway.env" ] || cp "$skill/assets/gateway.env.example" "$dest/gateway.env"
[ -e "$dest/models.yaml" ] || cp "$skill/assets/models.yaml" "$dest/models.yaml"
[ -e "$dest/.gitignore" ] || cp "$skill/assets/gitignore" "$dest/.gitignore"
rm -f "$dest/scripts/init_deployment.sh"
echo "Deployment folder ready: $dest"
echo "Next: edit gateway.env and models.yaml there, then make its .venv."
