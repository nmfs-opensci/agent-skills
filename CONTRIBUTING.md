# Contributing

Open or use a GitHub issue to describe the repeated workflow before creating or
changing a skill. Base guidance on concrete examples and actual experience, and
record significant reasoning and evidence in the issue or pull request.

## Create or update a skill

1. Create one lowercase, hyphenated directory at `skills/<skill-name>/`.
2. Include exactly one `SKILL.md` in the bundle. Keep it concise and move
   detailed guidance into `references/`.
3. Add `scripts/` only when deterministic, reusable execution is valuable, and
   test every bundled script. Add `assets/` only when the skill uses them.
4. Put realistic evaluation scenarios under `evals/<skill-name>/`, separate
   from the distributable bundle. Assess observable behavior without revealing
   a hidden answer to the agent being evaluated. A typical evaluation directory
   can contain `scenarios.md` and `expected-behaviors.md`.
5. Mark uncertain guidance Experimental or Provisional. Do not turn a one-off
   fix into universal guidance.
6. Check current official documentation when upstream APIs or agent behavior
   may have changed.
7. Run the repository validator and all modified scripts.
8. Submit the change through a pull request.

Only `SKILL.md` is required. Optional directories should be created only when
used. Individual skill directories should not contain their own `README.md`,
changelog, installation guide, or other extra files unless the Agent Skills
specification requires them in the future.

## `SKILL.md`

Every `SKILL.md` begins with YAML frontmatter containing only:

```yaml
---
name: example-skill
description: Describe what the skill does and when an agent should use it.
---
```

The frontmatter name must match the directory name. Names use only lowercase
letters, digits, and hyphens. After the frontmatter, provide focused instructions
and use progressive disclosure rather than placing every detail in the core
file.

## Safety and scope

Never include credentials, tokens, private endpoints, controlled data, sensitive
NOAA information, or other secrets. Keep contributions agent-independent and
avoid product-specific files unless they provide a clear additional benefit.

Keep pull requests focused. Update the README catalog when adding, renaming,
stabilizing, deprecating, or removing a skill, and update relevant evaluations
when behavior changes.
