# NMFS OpenSci Agent Skills

A shared, agent-independent catalog of reusable skills for NOAA Fisheries open
science, scientific computing, cloud data, and related workflows. It is intended
for scientists, data practitioners, software developers, and agents working
across repositories and GitHub organizations.

## Skill catalog

| Skill | Description | Status | Maintainer |
| --- | --- | --- | --- |
| [virtual-icechunk](skills/virtual-icechunk/) | Research, build, validate, document, and audit virtual Icechunk stores that reference remote NetCDF/HDF5 files in place. | Experimental | [@eeholmes](https://github.com/eeholmes) |

A skill is added to this table only when its directory and valid `SKILL.md`
exist.

Maturity levels:

- **Experimental** — exploratory guidance that may change substantially.
- **Provisional** — useful in practice but still gathering evidence.
- **Stable** — validated, maintained guidance suitable for routine use.
- **Deprecated** — retained for transition but no longer recommended.

## How the catalog is organized

Each portable bundle lives at `skills/<skill-name>/`. Only `SKILL.md` is
required; references, scripts, and assets are included only when needed:

```text
skills/
└── example-skill/
    ├── SKILL.md
    ├── references/
    ├── scripts/
    └── assets/
```

`SKILL.md` starts with YAML frontmatter containing only a matching `name` and a
`description` that says what the skill does and when to use it. Evaluation
scenarios live separately under `evals/<skill-name>/`, so distributable skill
bundles remain self-contained.

This repository is the shared source catalog. A repository-scoped installed
skill is a copy or checkout made discoverable within one project; a personal
installed skill is made discoverable in a user's agent configuration and can be
used across projects. Installed copies are not the canonical source.

## Using a skill

A skill is a folder of instructions that an agent loads when it recognizes a
matching task. You do not call it like a function. Once a skill is installed,
the agent reads its `description`, and when what you ask matches, it follows
that skill's guidance for the rest of the task.

So the way to use one is to **describe the task in plain language**:

```text
Build a virtual Icechunk store for these NOAA files on Source Cooperative
Why is this store so slow to open?
Review this older repository and tell me what to modernize
```

You do not need to name the skill. If it does not activate on its own, most
agents let you invoke it explicitly by name as a slash command, such as
`/virtual-icechunk`.

### Install one

Pick **personal** if you want the skill in every project on your machine, or
**project** if you want it committed so collaborators get it automatically.

Clone this catalog once:

```bash
git clone https://github.com/nmfs-opensci/agent-skills ~/agent-skills
```

Then link the skill you want into the location your agent reads. Linking rather
than copying means `git -C ~/agent-skills pull` updates every install:

```bash
# Personal, Claude Code
mkdir -p ~/.claude/skills
ln -s ~/agent-skills/skills/<skill-name> ~/.claude/skills/<skill-name>

# Personal, Codex
mkdir -p ~/.agents/skills
ln -s ~/agent-skills/skills/<skill-name> ~/.agents/skills/<skill-name>

# Project: commit the skill so collaborators get it
mkdir -p /path/to/repo/.claude/skills
cp -r ~/agent-skills/skills/<skill-name> /path/to/repo/.claude/skills/
```

The `mkdir -p` matters: the skills directory often does not exist yet, and
`ln -s` fails confusingly without it.

Copy instead of linking if you would rather pin a version than track `main`.
The full list of locations each agent reads is under
[Installation](#installation) below.

### Check that it worked

**Restart the agent.** Skills are discovered when a session starts, so one
installed mid-session will not appear until you restart.

Then ask for something the skill covers and see whether it engages. Many agents
also list what they loaded — in Claude Code, `/skills`.

### If it does not trigger

1. Restart the agent, if you have not since installing.
2. Invoke it by name: `/<skill-name>`.
3. Confirm the file is where the agent looks, and that the directory contains
   `SKILL.md` directly inside it, not nested one level deeper.

## Installation

Select a skill directory, then copy or link the complete directory into the
current skill location documented by the agent:

- **GitHub Copilot CLI:** copy into `.github/skills/`, `.claude/skills/`, or
  `.agents/skills/` in a repository, or `~/.copilot/skills/` or
  `~/.agents/skills/` for personal use. Copilot CLI also provides
  `copilot skill add`.
- **Claude Code:** use `.claude/skills/` in a project or `~/.claude/skills/`
  for personal skills.
- **Codex:** use `.agents/skills/` in a repository or `~/.agents/skills/` for
  personal skills. Older `$CODEX_HOME/skills` installations remain supported
  but are deprecated as a user-skill location.

Installation commands, discovery locations, and agent support can change.
Before installing, check the current official documentation for
[GitHub Copilot Agent Skills][copilot-skills],
[Claude Code skills][claude-skills], and [Codex skills][codex-skills]. The
canonical bundles in this catalog use the portable required subset of the
[open Agent Skills specification][agent-skills] rather than a product-specific
format.

To propose a skill or change, read [CONTRIBUTING.md](CONTRIBUTING.md) and use
the [new-skill](.github/ISSUE_TEMPLATE/new-skill.yml) or
[update-skill](.github/ISSUE_TEMPLATE/update-skill.yml) issue form.

[agent-skills]: https://agentskills.io/specification
[copilot-skills]: https://docs.github.com/en/copilot/concepts/agents/about-agent-skills
[claude-skills]: https://code.claude.com/docs/en/skills
[codex-skills]: https://developers.openai.com/codex/skills
