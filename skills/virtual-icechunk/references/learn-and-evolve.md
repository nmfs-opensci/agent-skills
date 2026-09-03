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

## Provisional and unverified, as of 2026-09-03

Treat everything here as open. Do not present any of it as settled practice.

**Deliberately out of scope for now**

- ERDDAP as a virtual source. No validated example exists. Research it fresh;
  do not reuse another provider's HTTP workaround and call it an ERDDAP or CORS
  pattern.
- Browser and WASM reading, and source or destination CORS. Nothing has been
  tested in a browser. A successful Python read is not evidence.
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
- Manifest split threshold and commit concurrency as scale-tuning choices.
- Whether the source manifest and build provenance belong inside the Icechunk
  repository or beside it.
- Exhaustive validation versus sampled checks at known transitions.
- Dependency lock strategy for notebooks meant to stay runnable.

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
