# NMFS OpenSci Agent Skills

A shared, agent-independent catalog of reusable skills for NOAA Fisheries open
science, scientific computing, cloud data, and related workflows. It is intended
for scientists, data practitioners, software developers, and agents working
across repositories and GitHub organizations.

## Skill catalog

| Skill | Description | Status | Maintainer |
| --- | --- | --- | --- |

No skills have been published yet. A skill is added to this table only when its
directory and valid `SKILL.md` exist.

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
