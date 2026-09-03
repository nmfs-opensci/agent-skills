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
- This file is loaded automatically at session start by a `SessionStart` hook
  (`~/claude-config/claude/hooks/load-repo-handoff.py`), which also lists the
  filenames in `claude/notes/`. Project memory for this repo lives in
  `~/claude-config/claude/memory/-home-jovyan-agent-skills/`, symlinked into
  `~/.claude/projects/`, so it is versioned and syncs between hubs.

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

## Recent work

- **2026-09-03 — built the `virtual-icechunk` skill** (issue #4 → PR #6). Five
  modes, 14 reference files, evals. Eli answered 16 open technical questions
  during the build; the durable subset is in
  `claude/notes/virtual-icechunk-skill.md` and in the skill's
  `references/learn-and-evolve.md`.
- **2026-09-03 — README "Using a skill" section** (issue #7 → PR #8), because
  the install docs said where files go but never how a skill activates. The
  team is new to Agent Skills.
- **2026-09-03 — `virtual-icechunk` installed as a personal skill** on this hub:
  `~/.claude/skills/virtual-icechunk` → `~/.agents/skills/virtual-icechunk` →
  `/home/jovyan/agent-skills/skills/virtual-icechunk`. A `git pull` here updates
  it everywhere; it is available in every repo on this machine.
- **2026-09-03 — session tooling moved into `~/claude-config`** (that repo, not
  this one): the handoff-loading hook, the `claude/handoff.md` + `claude/notes/`
  convention, and Eli's phrase routines ("I am about to clear", "this task is
  done", "I am about to sign off") are now written into the global `CLAUDE.md`
  rather than being re-explained each session.

## Open threads

Not a task list — context for whatever comes up. Ask before acting on any of it.

- The skill has never been run (see above). A real trial would be the natural
  next thing, but it is not scheduled.
- Topics deliberately left out of the skill, each recorded in
  `references/learn-and-evolve.md`: ERDDAP as a virtual source (no validated
  example); browser/WASM reading and CORS (never tested in a browser); Arraylake
  and non-Source-Cooperative destinations; automated incremental updates; the
  PACE HTTPS-vs-in-region decision; dependency lock strategy. Each needs a real
  example before it becomes guidance.
- `AGENTS.md` says keep the repo agent-independent; a committed `claude/`
  directory sits in mild tension with that. Flagged for Eli, undecided.
- The catalog has room for more skills; nothing is queued.
