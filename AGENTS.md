# Instructions for coding agents

These repository-wide instructions apply to any coding agent working here.
Task-specific workflows belong in individual skills, not in this file.

- Read the relevant issue and existing skill before editing.
- Preserve compatibility with the open Agent Skills convention. Do not make the
  repository specific to one agent product.
- Keep every skill portable, self-contained, and independently installable.
- Use progressive disclosure: metadata first, a concise `SKILL.md`, and detailed
  references only as needed.
- Clearly distinguish stable guidance from experimental or provisional
  findings.
- Cite evidence for changes based on external documentation or example
  repositories. Report unresolved uncertainty rather than inventing a standard.
- Validate every modified skill, test every modified script, and update relevant
  evaluations when behavior changes.
- Avoid unrelated changes.
- Never expose credentials, private endpoints, controlled data, sensitive NOAA
  information, or other secrets.
- Do not modify production services, repositories, datasets, or object stores
  while validating a skill.

Repository contribution conventions belong in this `AGENTS.md` and
`CONTRIBUTING.md`; reusable task instructions belong under `skills/`.
