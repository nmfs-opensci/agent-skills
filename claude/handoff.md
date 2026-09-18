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

## What the skill has been through

**`skills/virtual-icechunk/` has been used on a real build.** It was written
without live testing (2026-09-03), but `fish-pace/icechunks` has since adopted
it: that repository's `CLAUDE.md` names it as the authority to prefer over
re-deriving practice from its own notebooks, and the OA-indicators store was
built under it on 2026-09-17. So it is no longer unproven — though "used" is
not "systematically evaluated", and the eval scenarios in `evals/` have still
only ever been dry-run on paper.

**The evidence from real builds lives in the other repository**, not here:
`~/icechunks/claude/notes/oa-indicators.md` and `.../viewers.md` are where a
build's lessons get written down first. Harvesting them into the skill is a
deliberate step that has happened once (PR #13) and will need doing again.

## Recent work

- **2026-09-18 — folded the OA-indicators build and earth-mover corrections
  into the skill** (issue #12 → PR #13). The skill had been asserting that no
  virtual store was ever rendered in a browser; one was, and the matching
  negative case (CoastWatch, blocked at the source host) confirms the two-host
  CORS model and gives it a diagnosable symptom. Also corrected the claim that
  `Range` forces a preflight — a single `bytes=a-b` range is CORS-safelisted.
  Compared against the Icechunk vendor's own skill,
  `earth-mover/agent-skills`, and took five things from it. Format coverage
  beyond NetCDF/HDF5 and an FMRC reference were left for a separate decision.
- **2026-09-04 — browser access and CORS became a mode** (PR #10). Replaced the
  blanket "CORS is untested" disclaimers with `references/browser-access.md`:
  tested GCS policies, a forwardable admin request, and how to verify without a
  browser.
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

- **Two decisions deferred out of PR #13**, both needing Eli rather than a
  default: whether to cover formats beyond NetCDF/HDF5 (earth-mover documents
  virtual parsers for GRIB, TIFF/COG and existing Zarr — the skill's own
  `description` draws the line at NetCDF/HDF5), and whether to add an FMRC
  reference for forecast model run collections. FMRC is the strongest single
  document in earth-mover's repo and the skill has nothing on it.
- The evals have never been executed. earth-mover's repo has a runnable harness
  (Claude Agent SDK, LLM personas answering `AskUserQuestion` through
  `can_use_tool`, metrics committed per run as JSONL) that would port; ours are
  prose scenarios and a rubric. Not started, and their own harness has not had
  a live run either.
- Topics still deliberately left out of the skill, each recorded in
  `references/learn-and-evolve.md`: ERDDAP as a virtual source (no validated
  example); WASM read paths and browser rendering from a GCS source
  specifically; Arraylake and non-Source-Cooperative destinations; automated
  incremental updates; the PACE HTTPS-vs-in-region decision; dependency lock
  strategy. Each needs a real example before it becomes guidance. Browser
  rendering in general has left this list — see PR #13.
- `AGENTS.md` says keep the repo agent-independent; a committed `claude/`
  directory sits in mild tension with that. Flagged for Eli, undecided.
- The catalog has room for more skills; nothing is queued.
