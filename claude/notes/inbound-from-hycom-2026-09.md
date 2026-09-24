# Lessons from the HYCOM and OISST work, not yet in the skill (2026-09-19)

Written by the session that built `ocean-icechunks/hycom` (GOFS 3.1 reanalysis, 306 TB,
63,341 uncompressed NetCDF-3 files) and documented `ocean-icechunks/noaa-oisst`. Evidence is
in `~/hycom/claude/notes/` (`plan-issue-1.md`, `smoke-test-findings.md`,
`production-build-2026-09-18.md`) and `~/icechunks/claude/notes/viewers.md`. Only PR #19 (a
scratch-prefix test always gets a viewer and a short README) has been folded into the skill.
Everything below is a candidate for a Learn pass — check each against the versions then
current before writing it in.

## The skill is wrong here

- **`vds.vz.to_icechunk(session, encoding={...})` does not exist in VirtualiZarr 2.7.3.** The
  snippet is in `SKILL.md` ("Known traps"), `performance-tuning.md`, `current-workflow.md` and
  `known-issues.md`. Loaded variables go through `Dataset.to_zarr`, so the one-chunk `time` is
  set with `var.encoding["chunks"] = (n,)` before the write. Verify which releases, if any,
  accepted `encoding=`.
- **`chunks={}` is not universally right.** `project-docs.md` and `known-issues.md` recommend
  it. At HYCOM's scale each 4-D variable is 2,570,880 dask chunks, and every operation costs
  ~1.4 s + ~2.2 s and ~1 GB before data moves. What works: `chunks=None` (still lazy), select,
  then `.chunk()` the selection. `chunks=None` with no `.chunk()` loads the whole selection.
  The threshold is chunk count, not store size: 16k chunks per variable (OISST) is fine.

## New patterns

- **References can be computed instead of parsed** when the source is uncompressed NetCDF-3
  (or any format with a readable header and contiguous data): one small ranged GET per file
  for the header, `ChunkManifest.from_arrays`, no parser. 63,341 files of 4.8 GB scanned in
  75 s and written in two minutes. It also allows **sub-chunking** an unchunked variable along
  its leading axes (one chunk per depth level), which the skill's "unchunked arrays → correct
  but slow" paragraph does not contemplate. The price is a per-file header check that refuses
  to build unless every file agrees — HYCOM had two header layouts 40 bytes apart, mixed
  within experiments, and a template built from one file would have misplaced 43 % of the data.
- **Skeleton plus `region=` writes** for a regular combine axis with gaps: write the
  full-length coordinates and empty science arrays once, then references per batch with
  `to_icechunk(region={"time": slice(a, b)})`. Restartable in any order, and the loaded
  coordinates stay in one chunk (appending adds a chunk per batch). A misaligned region
  start is refused by VirtualiZarr 2.7.3 (verified 2026-09-24; see
  `append-alignment-issue-21.md`), so this pattern is safe from the #21 pitfall.
- **Declare big-endian data as native dtype plus `bytes(endian=big)`**, not `>i2`: with `>i2`
  VirtualiZarr 2.7.3 refuses every later region/append write ("inconsistent dtypes: int16 vs
  >i2"). Probably an upstream bug in `check_same_dtypes`; unreported.
- **Missing steps on a regular axis** are simply unreferenced and read as fill in ~0.1 s. Mark
  them with a real source variable that is NaN there (HYCOM's `tau`), not an invented flag.
- **`s3://` virtual references** (OISST) are authorized with
  `icechunk.containers_credentials({prefix: icechunk.s3_anonymous_credentials()})`, not
  `HttpAccess`. `source-patterns.md` has "no validated example" for anonymous S3; this is one,
  as a reader. icechunk-js rewrites `s3://` to HTTPS, so such a store can draw in a browser if
  the bucket has CORS.
- **Version floors, measured:** `icechunk.http_storage` is absent in 1.1.21 and present from
  2.0.1; `credentials.HttpAccess` arrives in 2.1.0. Python < 3.12 quietly installs 1.1.x, and
  readers then get an `AttributeError` that says nothing about versions. READMEs now carry a
  standard warning above the opening code.
- **Zarr attributes are untyped JSON**, so a float32 `scale_factor` reads back as float64 and
  xarray decodes packed ints to float64 (twice the memory of the source NetCDF). Exporting to
  NetCDF for a CF check also needs `flag_values` recast and `_FillValue: None` on coordinates.
- **S3 CORS:** `GET /?cors` on a bucket answers the question directly
  (`NoSuchCORSConfiguration`, or the policy). The S3 policy JSON in `browser-access.md` is the
  console format; the CLI wants it wrapped in `{"CORSRules": [...]}`. Still unapplied by us.

## Viewer lessons (`browser-access.md`, `project-docs.md`)

- A gridlook clone is per machine and goes stale silently: four viewers were published from
  one 98 commits behind. The publisher now fetches and refuses.
- gridlook hard-codes a demo default dataset for URLs with no fragment; a bare
  `viewer/index.html` link opens someone else's data.
- One `--dist` shared across products means a product without its own catalog publishes the
  last product's.
- Source Cooperative does not echo `Cache-Control` for `index.html`; a republished viewer looks
  unchanged until a hard reload. curl the server before believing a bug report.

## A documentation standard worth pointing at from `project-docs.md`

Eli's store READMEs share one format (title "— Icechunk", emoji navbar, fixed section
order); reference copy `ocean-icechunks/noaa-ohc/README.md`. It is Eli's house style rather
than agent-independent guidance, so probably a pointer, not a rule.

## A store built by someone else

Documenting `noaa-oisst` (NERACOOS/GMRI's store) turned up the skill's own first trap in the
wild — `daily/time` as 16,452 one-value chunks, a 7 s open — and metadata copied from a daily
group onto monthly statistics with `valid_max` not rescaled. Reported as
ocean-icechunks/noaa_oisst#2. A reasonable Audit-mode example.
