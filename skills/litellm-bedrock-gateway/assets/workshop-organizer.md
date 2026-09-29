# Running a workshop with a batch of keys

For the organizer of a workshop on the gateway `{{STACK}}`. You need only your
JupyterHub account: no AWS, no copy of any repository and no admin key.

## What you get

A **key file** from your key issuer (the person who manages the gateway's
keys), by direct message or put in your hub home folder, for example
`~/whale-keys.txt`, along with this page. It holds one line per key, like

```text
ws-whale-01 sk-...
ws-whale-02 sk-...
```

Each key has its own budget and expiry, which the key issuer chose with you.
The first line of the file says what they are.

Keep the file private: in your hub home, not in a shared folder, a notebook, a
repository or a group chat. Anyone with a key can use it, from anywhere, until
it runs out, expires or is stopped. If the file came by direct message, save it
on the hub (in a terminal: `cat > ~/whale-keys.txt`, paste, press Enter, then
Ctrl-D) and delete the message.

## Handing out keys

Give **one key per person**, privately: a direct message, or on paper handed
to them. Keep a note of who got which key name (`ws-whale-07`); the gateway
records spending per key, not per person.

Participants open a terminal on the hub and run

```bash
{{HUB_DIR}}/{{HUB_COMMAND}}
```

and paste their key when it asks for a workshop code or key. After that,
`{{HUB_COMMAND}}` in a new terminal starts Claude Code. Your key issuer can
send you a participant page to share (the hub quickstart); the steps above are
all participants strictly need.

## Checking on the workshop

```bash
{{HUB_DIR}}/{{HUB_COMMAND}} --status ~/whale-keys.txt
```

shows every key in the file with what it has spent, its budget and when it
expires. Spending shows up about a minute after use. It uses only the keys in
your file and prints none of them.

## When something goes wrong

- **A key may have leaked, or someone should stop**: tell your key issuer
  which key name (`ws-whale-07`). They can stop it at once. Stopped keys show
  as "not accepted" in `--status`.
- **Someone ran out of budget**: the key issuer can raise it, or you can give
  them an unused key from your file.
- **You need more keys**: ask your key issuer; they add them to a new file or
  the same one.
- **"not set up yet"** or **"Could not reach the workshop gateway"**: the
  gateway is stopped or not ready. Ask your key issuer.
