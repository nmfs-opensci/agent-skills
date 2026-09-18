# virtual-icechunk skill — design decisions

Built 2026-09-03 from issue #4, merged as PR #6. Evidence base:
`docs/virtual-icechunk-patterns.md`, the three fish-pace repositories,
`docs/example-virtual-icechunk-pipeline.ipynb`, the RFROM NODD prep notebook in
`nmfs-opensci/gobai-rfrom-icechunks`, and official docs for icechunk 2.2.0,
virtualizarr 2.7.3, xarray 2026.7.0, zarr 3.3.0 (versions verified on PyPI
2026-09-03).

## Shape

`SKILL.md` + 14 files in `references/`. Five modes: Research & plan → Create →
Audit → Diagnose → Learn. Create is gated in order — reviewed plan, then a
smoke-test notebook against a **local temporary** repository, then the
production script, then the project README and loading example.

The organizing idea throughout is that **source access and destination storage
are two independent configurations with independent credentials**. Most of the
confusion in the older repositories traces back to conflating them.

## Decisions Eli made, that a reader should not silently revisit

- **ERDDAP is out.** The prior analysis found no ERDDAP workflow in any
  reference repo — the CoastWatch one is plain HTTPS with a User-Agent
  workaround. The skill records "no validated example" rather than guessing, and
  explicitly forbids relabelling the User-Agent fix as an ERDDAP or CORS
  finding. Do not add an ERDDAP section without a real example.
- **`agents/openai.yaml` omitted** even though issue #4 listed it, because
  `CONTRIBUTING.md` says bundles hold only `SKILL.md` plus
  references/scripts/assets. Flagged in PR #6 as a convention conflict for Eli
  to reconcile.
- **Browser/WASM and CORS were out**, untested — *superseded twice*. PR #10
  (2026-09-04) brought CORS in with tested policies; PR #13 (2026-09-18) brought
  browser rendering in, because the OA-indicators viewer draws. What survives
  intact is the rule underneath: inferring browser support from a Python read is
  still an error, and so is inferring it from curl, or from one store having
  rendered.
- **Rebuilding source files is the exception**, needing the data owner's
  explicit clearance — RFROM/GOBAI-O2 had it, which is unusual. An earlier draft
  read as though it were a routine option; corrected.
- Facts Eli supplied that contradict the repositories' own artifacts: the
  CoastWatch and GlobColour stores are **complete** (their build notebooks are
  stale, and CoastWatch's looks unfinished only because batches were restarted);
  CloudFerro anonymous reads are **intentional** with stable URLs; PACE prefers
  **HTTPS** though in-region S3 may be faster and the choice is open;
  filename-derived time is **not preferred**; the PACE **CHL → BGS** rename is
  real and should be used.

The full set of 16 answered questions is on issue #4; the durable subset is in
`references/learn-and-evolve.md`.

## Emphases that came from Eli directly, not from the analysis

Two performance traps that had bitten real builds, both now in `SKILL.md`
itself and expanded in `references/performance-tuning.md`:

1. `loadable_variables` on the open **plus**
   `encoding={"time": {"chunks": (len(vds.time),)}}` on the write. Without it,
   one-time-step-per-file sources make metadata reads crawl. Stated as a
   proactive default for every multi-file build, not a fix applied after
   someone complains.
2. Zarr's `async.concurrency` defaults to 10, which badly under-uses object
   storage — "5x slower than it could be" territory. Documented as a reader
   setting as much as a writer one, and as something to measure per location
   rather than copy.

Because "why is this slow" and "will this be slow" are common asks, Diagnose
became a first-class mode. `performance-tuning.md` is built around the
distinction that makes virtual stores different: **metadata reads come from the
destination repository, data reads come from the source host** — two hosts, two
unrelated sets of causes, so establish which half is slow before changing
anything.

## Testing status

**Used on a real build, never systematically evaluated.** Dry-running the eval
scenarios on paper before release surfaced three real gaps, since fixed: the
research checklist never asked whether variables are split across files;
CF-compliance was only covered for files you produce, though metadata is the one
thing a virtual store *can* fix; and nothing guarded the destructive cleanup
cells every build notebook grows.

Since then `ocean-icechunks/icechunks` adopted the skill — its `CLAUDE.md` names it as
the authority to prefer over that repository's own notebooks — and the
OA-indicators store was built under it on 2026-09-17. PR #13 harvested what that
build taught, including one place where the skill was flatly wrong (it claimed
no virtual store had ever rendered in a browser) and one mechanism claim that was
wrong in a way that would have misdirected a diagnosis (`Range` was said to force
a CORS preflight; a single `bytes=a-b` range is safelisted, so often nothing
preflights and the ranged GET's `Access-Control-Allow-Origin` is what decides).

The lesson for this repo is procedural: **a build's evidence lands in the build
repository's own `claude/notes/`, and someone has to carry it across.** It sat
uncollected for two weeks, during which this repo's handoff still said the skill
had never been run. The eval scenarios remain un-executed.
