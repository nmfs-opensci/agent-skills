---
name: virtual-icechunk
description: Create, prototype, validate, document, audit, and improve virtual Icechunk stores — Icechunk repositories that hold only Zarr metadata and point at NetCDF/HDF5 bytes left in place at a remote source. Use when asked to build a virtual Icechunk from remotely hosted NetCDF or HDF5 files, prototype one in a notebook, turn a working prototype into a production build, write a README or loading example for a virtual store, review or modernize an older virtual Icechunk repository, compare Icechunk workflows, or update virtual-Icechunk practice from new experience. Covers virtual reference stores only, not materialized Icechunk writes that copy the data.
---

# Virtual Icechunk workflows

A virtual Icechunk store holds Zarr metadata and byte-range references. The
science data stays in the provider's NetCDF/HDF5 files and is never copied. That
single fact drives everything below: you cannot rechunk, recompress, or
homogenize data you are not rewriting.

**This guidance is provisional.** It is drawn from a handful of real builds
whose APIs and conclusions are still moving. Check current official
documentation for the versions you actually have (`references/version-matrix.md`)
before treating anything here as settled, and tell the user when you are working
from an unverified pattern.

## Modes

| The user wants to… | Mode | Start with |
|---|---|---|
| Understand a new dataset before coding | **Research & plan** | `references/research-and-plan.md` |
| Build a new virtual store | **Create** | plan → smoke test → production → docs |
| Review or modernize an existing workflow | **Audit** | `references/audit.md` |
| Ask why a store is slow, or whether one will be | **Diagnose** | `references/performance-tuning.md` |
| Ask whether a browser can read the store, or hit a CORS wall | **Browser access** | `references/browser-access.md` |
| Capture what a finished job taught | **Learn** | `references/learn-and-evolve.md` |

## Create: the required order

Do not skip ahead. Each step gates the next.

1. **Research and plan** — `references/research-and-plan.md`. Output is a
   written plan and a list of decisions, reviewed by a human. No build code.
2. **Smoke-test notebook** — `references/smoke-test-notebook.md`. A small,
   runnable notebook against a local temporary repository. It must reopen the
   store in a fresh read-only session and read real data, not just metadata.
3. **Production script** — `references/production-build.md`. Only after the
   smoke test passes and its choices have been reviewed.
4. **Project README and loading example** — `references/project-docs.md`. These
   belong to the dataset repository, not to this skill. They are deliverables,
   not optional extras.

`references/current-workflow.md` is the twelve-step end-to-end pattern the
smoke test and the production build are both built from, plus the code for
reading a finished store.

## First, check that virtual is the right answer

Virtualization preserves the source's chunk layout exactly. If the source files
have an unusable layout — inconsistent chunk grids between files, unchunked
arrays, one time step per file with a pathological coordinate, or codecs Zarr
cannot represent — a virtual store will be correct but slow, and no metadata
setting will fix it.

Usually you cannot do anything about it: the files belong to the provider. Say
plainly what the performance consequence will be, and let the owner choose.

Occasionally — and it is genuinely the exception — you produce the files, or the
data owner has explicitly cleared you to reprocess and republish them. Then
fixing the layout first is much better engineering than virtualizing a bad one,
because that is the only chance to fix chunking at all. Ask before assuming you
have that permission. See `references/source-file-design.md`.

## Slow reads

"Why is this slow?" and "will this be slow?" are common asks, and the answers
are usually build-time decisions that were free to get right and are expensive
to undo. Bad ones have made metadata reads crawl and data loads several times
slower than necessary. `references/performance-tuning.md` is the playbook for
both diagnosing an existing store and reviewing a plan before it is built.

The one thing to internalize: in a virtual store, **metadata comes from the
destination and data comes from the source** — two different hosts, two
unrelated sets of causes. Work out which half is slow before changing anything.

Raise this proactively. When planning a build, when reviewing someone else's
plan, and when validating, flag the decisions in that reference's design table
rather than waiting for a complaint.

## Browser readers and CORS

If the store is meant to be read from a browser, a virtual store needs CORS on
**two** hosts — the repository and wherever the source bytes live — because
metadata and data come from different places. A repository that is CORS-enabled
while its sources are not will open, show correct metadata, and fail on every
data read.

The entry people miss is `Range`: chunk reads are byte-range requests, `Range` is
not CORS-safelisted, so it must be allowed explicitly or nothing loads.
`references/browser-access.md` has the tested policies, a request an admin can
apply without editing, how to verify without a browser, and the fallbacks when
the bucket cannot be changed.

**Curl proving the headers is not the same as a browser rendering the store.**
Keep those claims separate, exactly as with Python reads.

## Non-negotiables

- **Source access and destination storage are two independent configurations**,
  with different credentials. Never let one imply the other. A reader needs
  both. `references/source-patterns.md`, `references/destination-patterns.md`.
- **Never write credentials into a notebook, script, or cell output**, and never
  commit them. Read them from the environment or a credential helper.
- **Never point a test at a production store.** Local temporary repositories, or
  a clearly separate scratch prefix.
- **Only combine files that are genuinely compatible** — dimensions, shape apart
  from the combine dimension, chunk grid, dtype, codecs, schema. Where they
  differ you must partition. `references/research-and-plan.md`.
- **Authorize every virtual chunk prefix explicitly**, including anonymous HTTP,
  and persist the config with `repo.save_config()`.
- **Validate from the consumer's read path**, not from the writer's in-memory
  repository object. `references/validation.md`.
- **A committed Icechunk session is read-only.** Open a fresh writable session
  after every commit.

## Do not over-generalize

The reference implementations differ from each other for good reasons. When you
carry something across, work out which kind of thing it is:

general mechanic · source-specific · destination-specific · dataset-specific ·
obsolete · unverified

Combine the newest applicable general pattern, the closest source-specific
pattern, the closest destination-specific pattern, and the current official API
docs. Do not clone whichever example is newest. A one-off fix is not a standard,
and a Python workaround is not evidence about browsers
(`references/browser-access.md` covers what is and is not verified there).

## Known traps

Read `references/known-issues.md` before debugging anything. The most common:
missing virtual authorization, an unsaved config, a prefix without a trailing
`/`, a reused session after commit, and expired destination credentials
mid-build.

Two performance traps have bitten these builds repeatedly, and both are cheap to
avoid up front rather than diagnose later (`references/performance-tuning.md`):

```python
# 1. Materialize the coordinates, then write the combine coordinate as ONE chunk.
#    Without this, one-time-step-per-file sources give one inline chunk per
#    timestamp and metadata reads crawl.
vds = open_virtual_mfdataset(urls, loadable_variables=["time", "lat", "lon"], ...)
vds.vz.to_icechunk(session, encoding={"time": {"chunks": (len(vds.time),)}})

# 2. Zarr's default concurrency is 10. Raise it, for writers AND readers, then
#    measure — the plateau depends on where you are relative to the store.
import zarr
zarr.config.set({"async.concurrency": 128})
```
