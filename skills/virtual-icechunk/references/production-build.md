# Production build

Write this only after the smoke test has passed and its choices have been
reviewed. It is a runnable Python script, not a notebook, and it must survive
being interrupted.

## Shape

- **Configuration at the top, logic below.** Everything that changes between
  variables, streams, or test-versus-production runs lives in one block:
  dataset/stream identifiers, URL prefixes, destination bucket and prefix,
  batch size, group layout, chunk choices.
- **No credentials in the file.** Read them from the environment or a credential
  helper at call time.
- **Do not force unlike sources through one abstraction.** Extract a helper only
  when a second real workflow has proven it reusable. Provider- and
  destination-specific code stays explicit.

## Batching and commits

- Batch size is a configuration value, not a constant. Choose it so a batch
  completes comfortably inside the destination credential lifetime.
- Commit each batch atomically, then open a **fresh writable session** — a
  committed session is read-only.
- Record for every commit: snapshot ID, the manifest range it covers, the file
  count, the first and last combine-coordinate values, and the package versions.
- Check the remaining credential lifetime *before* starting a batch, and refresh
  between batches rather than failing mid-write.

## Restart and recovery

**Derive progress from the committed repository state, reconciled against the
saved source manifest.** Open the repository, read the committed combine
coordinate, and match it against the manifest to find the first unprocessed
file.

An operator-supplied start index is permitted only as an explicit override for
an operator who knows why they are using it — never as the primary mechanism. A
hand-entered integer silently skips or duplicates data, and that has happened in
practice in more than one earlier workflow.

Before each batch, verify: combine coordinates are ordered and unique; no
schema, chunk, or codec drift has crept into the group; the destination
credentials cover the expected duration.

After each batch, reopen and validate the committed boundary before advancing.

## Failures

- Log progress and failures with enough context to resume by hand.
- Handle only the "repository already exists" condition when choosing between
  `Repository.create` and `Repository.open`. A bare `except Exception` around
  both hides authentication, network, and configuration errors — this is a real
  and repeated source of wasted debugging.
- Record every source file you skipped and why. A build that quietly drops files
  is worse than one that stops.

## Finishing

1. Validate the final committed state from the consumer-facing read path
   (`validation.md`).
2. Create an immutable tag naming the last data date covered by the build:

   ```python
   final_snapshot = repo.lookup_snapshot(repo.lookup_branch("main"))
   if tag_id not in repo.list_tags():
       repo.create_tag(tag_id, final_snapshot.id)
   ```

   Builds run on `main`. A staging branch is not required. If you expire
   snapshots afterwards, assert that `main` and the tag still resolve to the
   final snapshot before deleting anything.
3. Publish the environment file, the build script or notebook, and the README
   next to the store (`project-docs.md`).
