# Validation

Validation happens through the **consumer-facing read path**: a fresh
`Repository.open` on the published URL with explicit virtual authorization, not
the writer's in-memory repository object. A store is not proven until a public
read from the published location succeeds.

## Completion

Completion means the discovered source count and identity **reconcile exactly**
with the committed combine coordinates and the saved source manifest. A partial
build is not finished; if it is intentionally partial, that must be stated in
the README and in the tag.

Check for duplicate, missing, `NaT`, unordered, or unexpected off-cadence
coordinate values. Model the dataset's real cadence before calling a gap an
error — an 8-day product that resets each January is not broken.

## Structure

Within every group, assert dimensions, dtypes, variable names, coordinate
values, attributes, chunk shapes, and codec compatibility. Confirm the partition
is genuinely homogeneous — that is what makes the virtual array legal at all.

Verify fill and missing-value decoding against known source values, not against
the assumption that it worked.

## Data

Read real chunks, not only metadata: the first, the last, every
transition boundary, and something recent, from **every** group. Metadata that
opens cleanly over broken references is a common and misleading result.

## Access

- Reopen anonymously, or with consumer credentials, from the published URL.
- Confirm every persisted virtual prefix has the intended least-privilege
  authorization and contains no secret.
- Test the intended access environment when it matters: the consumer's region
  for in-region S3 references, or the consumer's credential type for a protected
  source.
- **Do not infer browser support from a Python read.** For a store intended to
  be read from a browser, check CORS on **both** hosts — the repository and the
  source bytes — and verify with a preflight plus a ranged GET, not with Python.
  `references/browser-access.md`. Confirming the headers is still not the same as
  rendering the store in a browser; WASM read paths remain untested.

## Performance

Record performance; do not assert a threshold. Virtual read speed is bounded by
the source's native chunking, which you cannot change — but first make sure you
are not simply measuring Zarr's default `async.concurrency` of 10
(`performance-tuning.md`). Capture, with package versions, compute region, cold
or warm cache, and the concurrency settings used:

1. metadata-only open;
2. one native chunk;
3. one map or slice;
4. a short point time series;
5. the representative scientific query.

These are observations, not benchmarks. Report them in the README so users know
what to expect, and flag when the native layout makes a common access pattern
expensive — for example a point time series over contiguous daily fields, which
must fetch most of each field. No metadata configuration fixes that; only
republishing the source files does (`source-file-design.md`).
