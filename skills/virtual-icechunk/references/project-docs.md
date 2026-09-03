# Project README and loading example

Both are required deliverables of a Create run, and both belong to the
dataset/project repository — never inside this skill. Publish them next to the
Icechunk prefix, together with the environment file and the build code, so the
store is self-describing.

## README contents

State plainly:

- **That this is a virtual store**: the science bytes stay at the source, and
  who operates that source. A user needs to know their reads depend on a third
  party staying up.
- **The exact public repository URL**, the groups, coverage, variables, and any
  known gaps or excluded files.
- **Why the groups or separate repositories exist**, so nobody later "fixes" a
  deliberate split.
- **Source and destination authentication as two distinct steps**, with the
  credential type each needs.
- **Compute-region or network restrictions.** If the references are in-region
  S3, say which region and that reads from elsewhere may be slow or impossible.
- **Minimum and tested package versions.**
- **A representative read**, with lazy-loading guidance — `chunks={}` before
  concatenating groups, `chunks=None` for direct NumPy access.
- **Source chunk limitations and observed performance**, including any access
  pattern that is expensive because of the native layout, and the
  `zarr.config.set({"async.concurrency": ...})` value the timings were measured
  with. Readers need that setting as much as the writer did.
- **Provenance**: build notebook or script, source manifest, snapshot ID or tag,
  and the update date.
- **Anything unverified**, explicitly. Browser support in particular must not be
  claimed unless it was actually tested in a browser.

A one-line README is not acceptable for a published store.

## Loading function

Provide a small function, module, or documented snippet that a user can copy. It
should take the dataset or group selection, obtain credentials at call time —
never embed them — and:

1. open the public repository metadata;
2. read the persisted virtual-container list from the repository config;
3. authorize each prefix with the correct source credential type;
4. open a named branch, tag, or snapshot;
5. call `xr.open_zarr(..., chunks={}, consolidated=False)` where appropriate;
6. concatenate only documented compatible groups, then sort and check the
   combine coordinate.

Keep it complete and standalone: it must not depend on variables defined earlier
in a build notebook. Test it in a fresh kernel before publishing.
