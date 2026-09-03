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

When you control or can republish the source files, fixing them first is often
the better engineering: see `references/source-file-design.md`. When you do not,
say plainly what the performance consequence will be and let the owner choose.

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
and a Python workaround is not evidence about browsers.

## Known traps

Read `references/known-issues.md` before debugging anything. The most common:
missing virtual authorization, an unsaved config, a prefix without a trailing
`/`, a reused session after commit, expired destination credentials mid-build,
and one-element coordinate chunks making metadata reads unbearably slow.
