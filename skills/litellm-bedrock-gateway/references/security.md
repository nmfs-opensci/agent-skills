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
