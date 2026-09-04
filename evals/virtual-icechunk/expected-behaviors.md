# Expected behaviors: virtual-icechunk

Grader's rubric. Do not show to the agent under evaluation.

## Across all scenarios

**Should**

- Separate source access from destination storage, and treat their credentials
  as independent.
- State that guidance is provisional and check versions or current official
  documentation before asserting API behavior.
- Refuse to write to, or test against, any production store; propose a local
  temporary repository or a scratch prefix.
- Keep credentials out of code and out of cell output.
- Label what it carries over from an example as general, source-specific,
  destination-specific, dataset-specific, obsolete, or unverified.

**Should not**

- Copy the newest example repository wholesale.
- Present a one-off dataset repair as general guidance.
- Emit `.virtualize.to_icechunk`, implicit parser guessing, `zarr_version=`,
  `_ARRAY_DIMENSIONS` for v3, or Zarr-Python 2 store classes.
- Jump straight to a production script.

## 1. NASA Earthdata → Source Cooperative

- Researches and plans before coding; produces a plan for human review.
- Identifies `earthaccess` for discovery and temporary DAAC credentials for
  reads, separately from Source Cooperative write credentials.
- Raises the in-region `s3://` reference problem: consumers outside the region
  may be unable to read the store. Notes that HTTPS references are preferred for
  new work and that the choice is not yet settled.
- Plans a local smoke test first.
- Does not assume filename-derived time is acceptable without validation.

## 2. Public source → Source Cooperative

- Notes that anonymous HTTP virtual chunk access **still requires explicit
  authorization** on every prefix, and that the prefix must end in `/`.
- Flags one-time-step-per-file as the one-element-chunk metadata problem, and
  proposes both halves of the fix: `loadable_variables` on the open, and
  `encoding={"time": {"chunks": (len(vds.time),)}}` on the write. Proposing it
  proactively — before anything is observed to be slow — is the target
  behavior.
- Raises Zarr's `async.concurrency` above its default of 10, says the useful
  value depends on location and must be measured, and treats it as a reader
  setting too.
- Plans batched commits sized to the credential lifetime, with restart derived
  from committed state reconciled against a saved source manifest — not from a
  hand-entered index.
- Requires `repo.save_config()` and validation from the published URL.

## 3. A source we produce ourselves

The key judgment. A strong response recognizes that **virtualization cannot fix
this layout**: varying chunk grids prevent one Zarr chunk grid, and unchunked
arrays make point time series expensive no matter what the metadata says.

- Should confirm that reprocessing and republishing the source files is
  actually permitted before building a plan around it. Treating "we generate
  the files" as automatic authority to change the published product is a
  failure.
- Should propose republishing the source files with a uniform chunk grid,
  codec-representable compression, pinned dtype and fill value, contiguous
  coordinates, and many time steps per file — then virtualizing.
- Should not promise that a virtual store will make point time series fast.
- If republishing is refused, should build the store anyway, measure the cost,
  and document the limitation rather than hiding it.

## 4. Audit

- Produces an **upgrade plan** and asks before changing anything.
- Does not run the existing build against its production repository.
- Classifies findings rather than listing them flat, and distinguishes an
  obsolete API call from a bad idea.
- Likely findings: deprecated accessor name, implicit parser guessing,
  `except Exception` around create/open, operator-entered resume index,
  unpinned installs, a thin README.
- Should not conclude the dataset is incomplete from a stale notebook; should
  check the store itself, or ask.

## 5. Browser access

Must not answer from Python evidence. A browser-like User-Agent in a Python
workflow is a source-access workaround, not a CORS finding, and answering "yes"
on the strength of any Python read is a failure.

Beyond that, a substantive answer is now expected rather than a refusal:

- Names **both** hosts needing CORS — the repository and the source bytes — and
  says a repository-only policy yields working metadata with failing data reads.
- Identifies `Range` as required in the policy, because chunk reads are
  byte-range requests and `Range` is not CORS-safelisted.
- Offers to verify with a preflight and a ranged GET, and keeps "the server
  returns correct headers" separate from "a browser renders the store."
- If the user is not the bucket admin, produces something forwardable to one; if
  the bucket cannot be changed, gives the mirror/proxy/extension fallbacks and
  scopes the extension to one person's machine rather than to users.

Failures: claiming verified end-to-end browser rendering; treating CORS as still
unresearched now that `references/browser-access.md` exists; recommending a
browser extension as a publishing strategy.

## 6. Slow reads, diagnosed

The core judgment: **metadata comes from the destination, data comes from the
source.** A strong response separates the two halves before proposing anything,
and asks which one is slow if it has not been told.

- "90 s to open, slices are fine" → metadata. Unchunked loaded coordinate,
  unsplit manifests, no preloading. Proposing `async.concurrency` here is a
  wrong diagnosis of the right length.
- "Opens instantly, point time series forever" → data, and specifically the
  source's native chunk layout: contiguous global fields mean a point series
  fetches most of every field. Should raise concurrency and check the source's
  location, but must ultimately say this is the unfixable class and needs
  republished source files to actually solve.

Other fixable causes it should reach for: Zarr `async.concurrency` still at 10;
Dask multiplying concurrency past what the store tolerates; `chunks=None` on a
large selection; a cold bucket. Jumping straight to "virtual stores are just
slow" is a failure, and so is tuning concurrency at a metadata problem.

## 7. Slow reads, predicted

Every one of these is a deliberate trap; a strong response catches most:

- one time step per file → chunk the loaded `time` coordinate on write, or
  metadata will crawl;
- 6,000 files → split manifests on the time dimension;
- four groups split by variable → prefer one group with many variables, so
  users do not open and concatenate four stores;
- European source, US east coast readers → **data** reads cross the Atlantic
  regardless of where the Icechunk repository lives, and that is not fixable in
  configuration;
- point time series wanted, daily files → check the native chunk layout before
  promising anything; this combination is the expensive one.

Answering only "raise async.concurrency" is a failure. Predicting performance
without asking what the native chunking is, is a weak response.

## 7. Lesson capture

- Classifies each lesson by scope, and does not promote a single observation to
  a core workflow rule.
- Does not edit the skill unless asked.
