# Handoff

Rolling index of session state. Keep this lean — a pointer to topic notes in
`claude/notes/`, not a copy of them.

## Repo state

- Repo: `nmfs-opensci/agent-skills`, working on `/home/jovyan/agent-skills`.
- Branch: `main`, clean, up to date with `origin/main`. **No open PRs, no open
  issues.** PR #6 (`skill/virtual-icechunk`, issue #4) and PR #8
  (`docs/using-a-skill`, issue #7) both squash-merged 2026-09-03; branches
  deleted, issues auto-closed.
- This is the **shared skill catalog**, not a working project. Skills live at
  `skills/<name>/`, evaluations separately at `evals/<name>/`. One skill so far:
  `virtual-icechunk` (Experimental).
- `docs/virtual-icechunk-patterns.md` is the prior provisional analysis of the
  three fish-pace repositories. It is the evidence base the skill was built
  from — read it before changing the skill's technical claims.

## Working principles

- `AGENTS.md` and `CONTRIBUTING.md` are the repo conventions and they are
  strict. Read both before editing. Highlights: exactly one `SKILL.md` per
  bundle with only `name` + `description` frontmatter; no README/changelog
  inside a skill directory; evaluations stay outside the bundle; mark uncertain
  guidance Experimental or Provisional.
- Keep the repo **agent-independent**. Do not add product-specific files to a
  skill bundle. (`claude/` is session notes, not part of the catalog.)
- Run `ruby .github/scripts/validate_skills.rb` before every commit. It checks
  frontmatter, name/directory match, and scans the whole tree for secrets.
- Commit to `main` only for handoff-only changes; everything else gets an issue,
  a branch, a PR, a squash merge, and a deleted branch. Eli wants the written
  record — put the real reasoning in the issue and PR body.
- Never modify production Icechunk stores, datasets, or object storage while
  validating a skill.

## Critical caveat

**`skills/virtual-icechunk/` has never been run.** It was validated only by the
repo validator, cross-reference checks, and paper dry-runs of its own eval
scenarios — Eli explicitly declined live testing in the session that wrote it.
Nothing in it is proven against a real source, destination, or build. See
`claude/notes/virtual-icechunk-skill.md`.

## In progress / next

- **Test `virtual-icechunk` for real** (not started). Run Research & plan and
  the smoke-test mode against an actual dataset, then feed what breaks back
  through `skills/virtual-icechunk/references/learn-and-evolve.md`. This is the
  obvious next task and the skill's status should not move off Experimental
  until it happens.
- **Unresolved topics deliberately left out of the skill**, each recorded in
  `learn-and-evolve.md`: ERDDAP as a virtual source (no validated example
  exists); browser/WASM reading and CORS (never tested in a browser); Arraylake
  and non-Source-Cooperative destinations; automated incremental updates; the
  PACE HTTPS-vs-in-region decision; dependency lock strategy. Each needs a real
  example before it becomes guidance.
- The catalog has room for more skills; nothing is queued.
