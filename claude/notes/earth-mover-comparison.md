# earth-mover/agent-skills, compared to ours

Read in full on 2026-09-18 (their repo at `603e50a`). This records the verdict
so a future session does not re-read it from scratch. What was *taken* is in
PR #13; the format material is in
[expanding-format-coverage.md](expanding-format-coverage.md).

## The two skills barely overlap

| | theirs | ours |
|---|---|---|
| Skill | `icechunk-datacube-ingestion`, at the repo root | `skills/virtual-icechunk/` |
| Scope | native **and** virtual; Icechunk **and** Arraylake | virtual references only, NetCDF/HDF5 |
| Organized by | **file format**, plus a 7-step ordered checklist | **workflow mode**, plus source/destination provider |
| Size | ~9 KB `SKILL.md`, 5 short sub-docs (2 empty or truncated) | 153-line `SKILL.md`, 14 references |

Their axis is *what format are the bytes in*; ours is *where do the bytes live,
where does the repo go, and will it be slow*. Neither subsumes the other.

## Where they are genuinely ahead

- **FMRC** (`FMRC.md`) — forecast model run collections, the `fix_ds()` reshape
  into scalar `time` + `step`, edge cases (inhomogeneous step counts reindexed
  onto the union rather than truncated; mixed cadences as separate cubes). We
  have nothing. Still undecided; see the handoff.
- **Format parsers** — see the other note.
- **A runnable eval harness.** See below. This is the real gap.
- A scripted user interview (`COLLECT-DATACUBE-INGESTION-REQUIREMENTS.md`) that
  branches on virtual-vs-native and, correctly, *stops asking about chunking and
  query patterns* once virtual is chosen, because chunking is inherited and
  there is nothing to act on. We know the fact and never turned it into "so do
  not ask". Worth borrowing the branch, not the full questionnaire.
- `pandera.xarray` schema validation, to assert homogeneity across *all* files
  rather than the handful actually inspected.

## Where we are ahead, and should not regress

Source/destination as two independent configurations with separate credentials
— theirs collapses this into Arraylake bucket configs. The entire performance
playbook (`async.concurrency` default of 10, the Dask interaction, the
one-element-chunk trap and its `encoding=` fix). CORS and browser access, which
they do not mention at all. Resume from committed state reconciled against a
manifest, and batching against credential lifetime. Audit mode, learn-and-evolve
classification, the version matrix, README/provenance deliverables.

## Their eval harness — the thing worth porting

`eval/`, a Python package driven by the Claude Agent SDK. The mechanism that
makes an interactive skill testable at all:

- `sdk_loop.py` intercepts `AskUserQuestion` through `can_use_tool` and answers
  it from an LLM persona brief (`personas/*.md`, Haiku), so a run completes
  without a human. That one trick is the whole idea; the rest is bookkeeping.
- Fixtures are YAML (`fixtures/*.yaml`): source location, persona reference,
  expected results, plus the opening prompt.
- Metrics split deterministic (wall clock, tokens, **which reference files got
  `Read`**, schema/VCC/value matches) from LLM-judged (steps-in-order,
  README clarity), one `runs.jsonl` row per run committed to git so a skill PR
  shows its own metric delta in the diff.
- `sdk_loop.py` + `persona.py` are ~200 lines together and would port largely
  as-is.

Their `PLAN.md` says "live smoke run pending", so they have not finished running
it either. Ours are prose scenarios and a rubric, never executed.

## Do not copy

- Their **Arraylake-centric access model** (`get_obstore_for_bucket()`, one
  bucket config). It erases the credential split that is our backbone.
- Their **link hygiene**: `SKILL.md` links four files that do not exist,
  `formats/HDF5.md` is zero bytes while being the netCDF4 path, `GRIB.md` ends
  mid-sentence. That is the argument for an internal-link check in
  `validate_skills.rb`.
- **Frontmatter on every sub-document.** They do it so each file is
  self-describing; our validator permits it but `CONTRIBUTING.md` says
  references are plain. Marginal, skip.
