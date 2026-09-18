# Learn and evolve

This skill is a living playbook. At the end of a Create run or an Audit, assess
what the work taught and whether any of it transfers.

## Classify each lesson

| Class | Meaning | Where it belongs |
|---|---|---|
| Core workflow change | Applies to every virtual build | `SKILL.md` or `current-workflow.md` |
| Source-specific | True for one provider or access style | `source-patterns.md` |
| Destination-specific | True for one object store | `destination-patterns.md` |
| Validation improvement | A check that should always run | `validation.md` |
| Known issue or workaround | A failure mode and its response | `known-issues.md` |
| Provisional experiment | Worked once; not yet guidance | Note it, do not promote it |

The bar for a core workflow change is that it held on more than one dataset,
provider, or destination. One success is an anecdote. Provider quirks stay in
provider sections no matter how much time they cost you.

## Rules

- **Update the skill only when asked**, or when updating it is explicitly part
  of the task. Otherwise report the lessons and let the owner decide.
- Say what the evidence is: which dataset, which versions, what was observed.
- Keep the distinction between *this failed* and *this always fails*.
- When a new example resolves something listed below as unverified, update that
  entry and cite the example.
- Re-check version-sensitive claims against current official docs before
  promoting them.

## Provisional and unverified, as of 2026-09-18

Treat everything here as open. Do not present any of it as settled practice.

**Deliberately out of scope for now**

- ERDDAP as a virtual source. No validated example exists. Research it fresh;
  do not reuse another provider's HTTP workaround and call it an ERDDAP or CORS
  pattern.
- WASM read paths, and parts of browser reading — but the headline has moved. A
  virtual store **has** been rendered end to end in a browser (OA indicators,
  confirmed 2026-09-18), so "nothing has ever rendered" is false and must not be
  repeated.
  What is still open is narrower: rendering from a GCS source, the S3 policy in
  `references/browser-access.md`, and whether a given viewer handles extra
  dimensions, its own catalog metadata, or CF time. A successful Python read is
  still not evidence of any of it, and one render does not generalize.
- Automated incremental discovery, append, scheduling, and conflict handling.

**Unresolved**

- Arraylake / Earthmover, and NOAA or project object storage other than Source
  Cooperative, need their own adapters and smoke tests before being written up.
- Whether PACE should publish in-region `us-west-2` S3 references, HTTPS
  references, or both. The current preference is HTTPS for reach, but an
  in-region store may be materially faster and both may be worth building. Open.
- Whether PACE time must be derived from filenames. It is used because the file
  metadata was insufficient, it was difficult to get right, and it is not
  preferred. Prefer in-file time whenever it is trustworthy; if you must use the
  filename, validate it against the real cadence for every product.
- Whether a compatibility partition should be a group or an independent
  repository, beyond the default in `research-and-plan.md`.
- Commit concurrency as a scale-tuning choice. The manifest split *threshold* is
  partly answered: VirtualiZarr documents splitting a virtual dataset across
  commits past roughly 50 million chunks. Below that ceiling there is still no
  published number, and none has been measured here.
- Whether the source manifest and build provenance belong inside the Icechunk
  repository or beside it.
- Exhaustive validation versus sampled checks at known transitions.
- Dependency lock strategy for notebooks meant to stay runnable.

**Settled by the OA-indicators build, 2026-09-17** (`ocean-icechunks/icechunks`
PR #24;
a virtual store at `ocean-icechunks/oa-indicators/climatology`, NCEI accession
0270962, twelve NetCDFs merged into one flat group of 72 variables)

- A virtual store renders in a browser across two hosts. The store's own viewer
  draws from `data.source.coop` plus `www.ncei.noaa.gov` — transport verified on
  the build date, rendering confirmed by the project owner on 2026-09-18. The
  matching negative
  is equally informative: the CoastWatch OHC viewer, same repository host,
  renders coordinates and no science arrays because `coastwatch.noaa.gov` sends
  no `Access-Control-Allow-Origin`. The two-host model is confirmed, and so is
  its exact symptom.
- A single `Range: bytes=a-b` is CORS-safelisted, so a blocked browser read
  often involves no preflight at all. This corrects what
  `references/browser-access.md` used to say.
- One variable per file merges into one flat group; it does not concatenate, and
  it does not justify one store per file. The mirror image of CoastWatch's
  codec-driven split.
- `xr.merge`'s `combine_attrs` reaches variable attributes, so `"drop"` empties
  them all. It presents as VirtualiZarr losing metadata and is not.
- `vz.to_icechunk` defaults to `mode="w-"`; a re-run raises `ContainsGroupError`.
- Phony all-zero HDF5 dimension scales are repairable with `swap_dims` rather
  than being grounds to exclude a file.
- A transient `StorageError` on a virtual chunk read is a dropped connection,
  not corruption. Retry before investigating.
- CF compliance was substantive work, and real CF standard names existed for
  only six of twelve indicators. None were invented for the rest — the right
  outcome, and the reason the "check against the CF table" rule earns its place.

**Settled by the project owner, 2026-09-03**

- Copernicus/CloudFerro virtual reads are intentionally anonymous, and the
  rewritten CloudFerro URLs are believed stable. Re-verify if reads start
  failing.
- The CoastWatch OHC store is complete. Its build code looks unfinished because
  the batches were restarted repeatedly — that is a restart-mechanism lesson,
  not an incomplete dataset.
- The GlobColour store is complete; its notebook is out of date relative to the
  finished build. Do not infer completeness or practice from a stale notebook —
  check the store.
- The PACE CHL → BGS rename is real and the new naming should be used.
