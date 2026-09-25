# Handoff

Rolling index of session state. Keep this lean — a pointer to topic notes in
`claude/notes/`, not a copy of them.

## Repo state

- Repo: `nmfs-opensci/agent-skills`, working on `/home/jovyan/agent-skills`.
- Branch: `main`, clean, up to date with `origin/main`. **No open PRs.** Merged
  so far: #6 (the skill, issue #4) and #8 (README) on 2026-09-03, #10
  (browser-access) on 2026-09-04, #13 (OA lessons, issue #12) and #15 (repo
  rename, issue #14) on 2026-09-18; #19 (a scratch-prefix test always gets a viewer
  and a short README, issue #18) on 2026-09-19, opened from the HYCOM session in a
  separate worktree; #24 (new `litellm-bedrock-gateway` skill, issue #22) on
  2026-09-25. All squash-merged, branches deleted, issues auto-closed.
- **Lessons from the HYCOM build are waiting for a Learn pass**, including two places
  where the skill is wrong (`to_icechunk(encoding=...)` does not exist in VirtualiZarr
  2.7.3; `chunks={}` breaks down at millions of chunks):
  [notes/inbound-from-hycom-2026-09.md](notes/inbound-from-hycom-2026-09.md).
- **In progress: issue #21**, the append pitfall from the CEFI audit. Decisions are
  made and the failure is verified by running; no skill edits yet. No branch
  (the empty `issue-21-append-alignment` was deleted 2026-09-25; branch again
  from `main`). Everything is in
  [notes/append-alignment-issue-21.md](notes/append-alignment-issue-21.md).
- **Eli to post the upstream VirtualiZarr issue** (drafted 2026-09-24, not yet posted).
  The draft and its repro are in `~/tmp/claude-1000/`
  (`virtualizarr-append-issue.md`, `virtualizarr-append-repro.py`). Read it, then:

  ```bash
  gh issue create -R zarr-developers/VirtualiZarr \
    --title "to_icechunk(append_dim=...) silently misplaces data when the existing length isn't a multiple of the chunk size" \
    --body-file ~/tmp/claude-1000/virtualizarr-append-issue.md
  ```

  Then give the issue number to the session writing the #21 skill changes, which should
  cite it.
- **Also open: #23**, a skill that checks a repo's license, reuse statement and
  citation file (Eli, 2026-09-25). Nothing done.
- #20 ("LiteLLM") no longer exists here: it was transferred to
  `nmfs-opensci/agent-coders-clinics` as issue #1 (closed). The reusable part
  became the `litellm-bedrock-gateway` skill (#22 → PR #24):
  [notes/litellm-bedrock-gateway-skill.md](notes/litellm-bedrock-gateway-skill.md).
  Follow-ups for the clinics repo are in agent-coders-clinics#8.
- **Also open: #11, "add info on /tmp"**, filed 2026-09-04 by a hub
  admin, not by Eli. It asks that guidance mention copying data to `/tmp` because
  `$HOME` and `~/shared` are slow on this JupyterHub. It is about repo-level
  agent guidance (`AGENTS.md`), not about the skill, and nothing has been done
  with it. Ask before acting.
- This is the **shared skill catalog**, not a working project. Skills live at
  `skills/<name>/`, evaluations separately at `evals/<name>/`. Two skills, both
  Experimental: `virtual-icechunk` and `litellm-bedrock-gateway`.
- `docs/virtual-icechunk-patterns.md` is the prior provisional analysis of the
  three reference repositories. It is the evidence base the skill was built
  from — read it before changing the skill's technical claims. It is a snapshot
  of 2026-09-03 practice, though: for CoastWatch specifically, the live
  repository `ocean-icechunks/icechunks` (moved from `fish-pace/icechunks` on or
  before 2026-09-18) and its `claude/notes/` are fresher. The other two,
  `fish-pace/globcolour-Icechunks` and `fish-pace/pace-icechunks`, did not move.
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
without live testing (2026-09-03), but `ocean-icechunks/icechunks` has since adopted
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

- **2026-09-25 — added the `litellm-bedrock-gateway` skill** (issue #22 → PR #24).
  A self-contained copy of the clinics gateway, now its source of truth, with one
  model list (`models.yaml`) and config in Parameter Store. Tested end to end in a
  throwaway stack. Found that LiteLLM keys without a `user_id` can read each
  other's details; the skill sets one.
  [notes/litellm-bedrock-gateway-skill.md](notes/litellm-bedrock-gateway-skill.md).
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

- **Formats beyond NetCDF/HDF5 — Eli will do this later, deliberately not now**
  (decided 2026-09-18). The skill's scope and `description` stay as they are.
  The dossier for that work — parsers, packages, current versions, the layout
  decision, and what each format needs before it counts as guidance — is in
  [notes/expanding-format-coverage.md](notes/expanding-format-coverage.md).
  Do not start it unasked.
- **FMRC (forecast model run collections)** is still undecided, and is the other
  half of the same question: most real GRIB is forecast output, so the two will
  probably arrive together. earth-mover's `FMRC.md` is the strongest single
  document in their repo and the skill has nothing on it.
- The evals have never been executed. earth-mover has a runnable harness that
  would largely port — the mechanism and the metric list are in
  [notes/earth-mover-comparison.md](notes/earth-mover-comparison.md). Not
  started, and their own harness has not had a live run either.
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

## Notes

- [litellm-bedrock-gateway-skill.md](notes/litellm-bedrock-gateway-skill.md) —
  Eli's decisions for the gateway skill, why config lives in SSM, the `user_id`
  finding, what is untested
- [append-alignment-issue-21.md](notes/append-alignment-issue-21.md) — #21 decisions,
  the verified repro, and why VirtualiZarr's append misplaces data
- [virtual-icechunk-skill.md](notes/virtual-icechunk-skill.md) — why the skill
  is shaped the way it is, and its testing status
- [expanding-format-coverage.md](notes/expanding-format-coverage.md) — GRIB,
  TIFF and Zarr: where the material is, for the later widening
- [earth-mover-comparison.md](notes/earth-mover-comparison.md) — how the
  vendor's skill compares, what was taken, what to port next
