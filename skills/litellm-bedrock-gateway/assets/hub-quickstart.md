# Claude Code on the JupyterHub (workshop)

You need nothing but this hub: no AI account and no AWS account.

## First time

1. Open a terminal: **File → New → Terminal**.
2. Run:

   ```bash
   {{HUB_DIR}}/{{HUB_COMMAND}}
   ```

3. Type the **workshop code** that {{ORGANIZER}} gives you.

It gets you a personal key (${{BUDGET}} to spend, lasts {{DAYS}} days),
installs Claude Code if needed, and starts it. The first start asks a few setup
questions: pick a theme and say yes to trusting the folder.

## After that

Open a **new** terminal (the short name does not work in the terminal you used
the first time), then:

```bash
{{HUB_COMMAND}}
```

Start it in the folder you want to work in, for example `cd ~/my-project`
first. The full path, `{{HUB_DIR}}/{{HUB_COMMAND}}`, always works.

## Check your spending

```bash
{{HUB_COMMAND}} --budget
```

It shows what you have spent, your budget and when your key expires. Spending
shows up about a minute after you use Claude.

## Useful

- Inside Claude Code: `/model` switches models, for example
  `/model {{STRONGER_MODEL}}`. The default, {{DEFAULT_LABEL}}, is the cheapest.
- Your key is yours: it is saved in `~/.config/{{HUB_COMMAND}}/key` and use is
  recorded against it. Do not share it.

## If you have your own Claude account

Keep using `claude` as usual. `{{HUB_COMMAND}}` keeps its settings and history
in `~/.config/{{HUB_COMMAND}}/claude` and never touches your own login or
settings in `~/.claude`.

## If something goes wrong

- **"That workshop code is not right"**: check the code and try again.
- **"A key for ... was already issued"**: you, or someone using your name,
  already signed up. Ask {{ORGANIZER}}.
- **"All workshop keys are handed out"** or **"sign-up is closed"**: ask
  {{ORGANIZER}}.
- **"not set up yet"** or **"Could not reach the workshop gateway"**: the
  gateway is not ready or is stopped. Ask {{ORGANIZER}}.
