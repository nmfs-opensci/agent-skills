# Handoff

Rolling index of session state. Keep this lean — a pointer to topic notes in
`claude/notes/`, not a copy of them.

## Repo state

- Repo: `nmfs-opensci/agent-skills`, working on `/home/jovyan/agent-skills`.
- Branch: `main` clean. **No open PRs.** Merged
  so far: #6 (the skill, issue #4) and #8 (README) on 2026-09-03, #10
  (browser-access) on 2026-09-04, #13 (OA lessons, issue #12) and #15 (repo
  rename, issue #14) on 2026-09-18; #19 (a scratch-prefix test always gets a viewer
  and a short README, issue #18) on 2026-09-19, opened from the HYCOM session in a
  separate worktree; #24 (new `litellm-bedrock-gateway` skill, issue #22) on
  2026-09-25; #26 (gateway workshop sign-up, organizer without AWS, per-install
  docs, issue #25) and #28 (organizer keys, named workshops, issue #27) on
  2026-09-28; #31 (`CLAUDE.md` symlink to `AGENTS.md`, issue #30) and #32
  (gateway setup split from adding a workshop, issue #29) and #34 (key batches,
  issue #33; companion `litellm-gateway-template#4`) on 2026-09-29. All
  squash-merged, branches deleted, issues auto-closed.
- **Clinics task B, the install template** `nmfs-opensci/litellm-gateway-template`
  (`~/litellm-gateway-template`): built. Its notes live **here**, not in that
  repo, because template copies would inherit a `claude/` directory:
  [notes/litellm-gateway-template.md](notes/litellm-gateway-template.md).
  #29 is done (PR #32). **Eli is about to try the template for a real
  install** (2026-09-29); the skill is linked on this hub for that. **C,
  the colleague's org-install instructions, is done** as the trimmed
  agent-coders-clinics PR #11 (open, awaiting Eli): template + skill, the
  install's answers, and a revocable organizer key for Eli. Next after
  2026-09-30: clean up `~/agent-coders-clinics` (tracked in that repo's
  handoff).
- **Key batches, #33 → PR #34, merged 2026-09-29**: three roles (installer,
  key issuer, organizer with only a hub account); `keys.py batch`; the hub
  script takes a code or a pasted key and has `--status FILE`; organizer keys
  renamed issuer keys (old names still work). Sign-up kept. Tested end to end
  on a throwaway Greenfield stack, torn down. Decisions and why:
  [notes/litellm-bedrock-gateway-skill.md](notes/litellm-bedrock-gateway-skill.md)
  Eli's real install (still pending) now gets this version. The existing
  install `nmfs-opensci/agent-coders-gateway` (`~/agent-coders-gateway`,
  deployed before #34) has its update plan in agent-coders-gateway#3: local
  files only, no redeploy; decisions there are Eli's.
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
- **The Icechunk skills moved out on 2026-11-13** to
  `ocean-icechunks/ocean-icechunks-skills` (`~/ocean-icechunks-skills`), with
  their history, evals, `docs/` evidence and the five Icechunk notes
  (ocean-icechunks/icechunks#46). Their state, open threads (#21 append
  alignment, HYCOM lessons, the unposted VirtualiZarr issue) and notes are in that
  repo's `agent/handoff.md`. PR #39 was closed here and reopened there as #2. #21 and #40
  were copied there as ocean-icechunks/ocean-icechunks-skills#3 and #4 (GitHub
  cannot transfer between orgs); the originals carry a pointer and are still open.
- This is the **shared skill catalog**, not a working project. Skills live at
  `skills/<name>/`, evaluations separately at `evals/<name>/`. One skill,
  Experimental: `litellm-bedrock-gateway`.
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

## Recent work

- **2026-09-29 — gateway setup split from adding a workshop** (issue #29 → PR
  #32). Step 1 asks only gateway questions; new step 9 adds a workshop and
  records it with `workshop.py plan` in `docs/workshops/<name>.md`. Per-workshop
  settings left `gateway.env`. Not tested against a live gateway. Decisions in
  the gateway note. Also `CLAUDE.md` → `AGENTS.md` symlink (#30 → #31), and the
  gateway skill linked as a personal skill on this hub the same way as
  `virtual-icechunk` (via `~/.agents/skills`).

- **2026-09-28 — organizer keys and named workshops** (issue #27 → PR #28). An
  organizer without AWS gets a revocable `proxy_admin` key, never the master key
  or UI password; several workshops can run at once. Tested end to end in a
  throwaway stack, torn down. Decisions in the gateway note.

- **2026-09-28 — gateway skill: workshop sign-up, organizer without AWS, per-install
  docs** (issue #25 → PR #26). Task A from the clinics repo. Tested end to end in
  `gwskill-test-delete-me`, torn down. Decisions in the gateway note.

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
  `/home/jovyan/agent-skills/skills/virtual-icechunk`. *Since 2026-11-13 the
  link points at `~/ocean-icechunks-skills/skills/virtual-icechunk` instead.*
- **2026-09-03 — session tooling moved into `~/claude-config`** (that repo, not
  this one): the handoff-loading hook, the `claude/handoff.md` + `claude/notes/`
  convention, and Eli's phrase routines ("I am about to clear", "this task is
  done", "I am about to sign off") are now written into the global `CLAUDE.md`
  rather than being re-explained each session.

## Open threads

Not a task list — context for whatever comes up. Ask before acting on any of it.

- `AGENTS.md` says keep the repo agent-independent; a committed `claude/`
  directory sits in mild tension with that. Flagged for Eli, undecided.
- The catalog has room for more skills; nothing is queued.

## Notes

- [litellm-bedrock-gateway-skill.md](notes/litellm-bedrock-gateway-skill.md) —
  Eli's decisions for the gateway skill, why config lives in SSM, the `user_id`
  finding, what is untested
- [litellm-gateway-template.md](notes/litellm-gateway-template.md) — the
  install template repo: Eli's direction, why it has no `claude/` or
  `.gitignore`, what is tested
