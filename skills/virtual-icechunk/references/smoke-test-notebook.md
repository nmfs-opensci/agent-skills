# Smoke-test notebook

The first implementation artifact for any new dataset. It must be small enough
to rerun repeatedly and must isolate source behavior from destination behavior.
Favor readable, inspectable cells over abstraction; helpers come later, if
experience justifies them.

**Never point a smoke test at a production repository.** Write to a local
temporary directory, or to a clearly separate scratch prefix.

## Cell outline

1. **Versions.** Import and print the versions of icechunk, virtualizarr,
   xarray, zarr, obstore, and any provider client, plus the Python version.
   Write them into a markdown cell as the tested environment.

2. **Discover a small file list.** Use the real discovery method, but take only
   a handful of files — and include files from **both sides of every suspected
   transition**, not just the first few. Print the URLs.

3. **Authenticate.** Obtain source credentials from the environment, a
   credential helper, or a provider CLI. Never write a token into the notebook,
   and clear credential values out of any cell output before committing.

4. **Prove byte-range access.** For HTTPS sources, issue a small range request
   and assert HTTP 206 and the expected magic bytes. If this fails, stop.

5. **Inspect one representative file per group.** Report dimensions,
   coordinates, variables, dtypes, attributes, native chunk shapes, codecs, and
   fill-value encoding. This is what tells you whether the partition in your
   plan is right.

6. **Build the source objects.** `from_url` → `ObjectStoreRegistry` → parser →
   `VirtualChunkContainer`. See `source-patterns.md`.

7. **Open a one-file virtual dataset.** Load only coordinates and small
   variables. Apply any dataset-specific metadata repair here, and print what
   was changed.

8. **Create a temporary local Icechunk repository** and write that one file.
   Then append two or three more compatible files and commit. Set the loaded
   coordinate's chunking explicitly if the source is one time step per file.

9. **Reopen in a fresh read-only session** — a new `Repository.open`, not the
   writer's in-memory object — with explicit virtual authorization for every
   prefix.

10. **Assert the structure.** Dimensions, coordinate values and their order,
    variables, dtypes, chunk shapes, and decoded missing values against known
    source values.

11. **Read real data, not just metadata.** A small field, plus a subset shaped
    like the intended science query. Time both and print the timings.

12. **Test the intended access environment** when it matters: the consumer's
    region for in-region S3 references, or the consumer's credential type for a
    protected source. Do not infer browser support from a Python read.

13. **List what is still unknown** in a final markdown cell, before scaling up.

14. **Clean up only the temporary local repository.**

## Keep out of the smoke test

Remote-destination debugging, destructive cleanup of anything shared, and full
production runs. If you need to test destination endpoint semantics, write a
second minimal notebook that changes only step 8 to use the remote storage and
writes to a scratch prefix.

## Cleanup and teardown cells

Every real build notebook grows cells that list and delete objects under a
prefix, because a botched store has to be removed before rebuilding. Keep them,
but make them hard to run by accident:

- put them in a clearly labelled troubleshooting section at the **end**;
- guard every destructive cell with `%%script false --no-raise` so a
  run-all cannot fire it;
- list what would be deleted, and print the count, before deleting anything;
- gather the keys first, then delete, so paginating a changing listing cannot
  skip objects;
- name the exact bucket and prefix inline — never a variable that some earlier
  cell might have rebound.

## Exit criteria

The smoke test has succeeded when a fresh read-only session, opened from the
consumer-facing path, returns correct values for every group, and the remaining
unknowns have been reviewed by a human. Only then write the production script.
