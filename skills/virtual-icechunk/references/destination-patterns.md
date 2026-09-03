# Destination patterns

The destination is where the Icechunk metadata repository is written. It is
independent of where the source bytes live, and it uses different credentials.
Configure it separately, and only after the source side works locally.

## The stable mechanics

- Object-storage repositories require a non-empty prefix at creation.
- `Repository.create` for a new repository; `Repository.open` for an existing
  one. Handle only the "already exists" condition — do not wrap both in a bare
  `except Exception`, which hides authentication and network failures.
- Persist intentional configuration with `repo.save_config()`, so public readers
  discover the virtual containers.
- A committed session is read-only. Create a fresh writable session after each
  commit.
- Read back through the **consumer-facing path**, not the writer's in-memory
  repository object.

## Source Cooperative

The only destination with production evidence in the reviewed repositories.

- Writes: S3-compatible storage built from the endpoint
  (`https://data.source.coop`), region, bucket, prefix, path-style setting where
  required, and temporary credentials.
- Credentials: generate short-lived, fine-grained tokens with the `source-coop`
  CLI. Older notebooks read a hand-made JSON credentials file; that is the
  outdated pattern. Check the remaining lifetime before starting a batch and
  refresh between batches.
- Reads: `icechunk.http_storage(full_url)` on the public URL, which must include
  the bucket and the full prefix.
- History: an older Icechunk release needed a private patch here because the
  endpoint lacked server-side copy. Retest on the current release rather than
  carrying a patch.

Both current Source Cooperative stores (CoastWatch OHC, GlobColour) are
complete. The GlobColour build notebook is out of date relative to the finished
store, and the CoastWatch build code looks unfinished only because its batches
were restarted repeatedly. Check the store, not the notebook.

## Google Cloud Storage / NOAA Open Data Dissemination

Evidence comes from a NODD publication workflow rather than an Icechunk write:
<https://github.com/nmfs-opensci/gobai-rfrom-icechunks/blob/main/RFROMV/prep-one-netcdf-for-NODD.ipynb>

- Access via `gcsfs.GCSFileSystem(token=...)` with application-default
  credentials; no token in the notebook.
- Lay the bucket out as `<kind>/<version>/<stream>/`, e.g.
  `gs://noaa-oar-rfrom/netcdf/v2.3/temp_stable/`. A reprocessing lands under its
  own version prefix, so stores built on the old version keep working, and each
  stream is one clean glob for a downstream build.
- Verify the object landed and its size before moving on.

Writing an Icechunk repository itself to GCS has not been done here. Verify the
Icechunk GCS storage API against current documentation and smoke-test it before
treating it as a pattern.

## Generic S3-compatible object storage

Same shape as above: endpoint, region, bucket, prefix, path-style flag,
credentials. Whether the credentials expire is the only part that changes the
build loop. Verify against current Icechunk storage documentation.

## Local storage

Use for every smoke test. A local repository proves the source side without any
destination credentials at all.

## Destinations with no validated example

Arraylake / Earthmover, and NOAA or project object storage other than Source
Cooperative. Each needs its own adapter and its own smoke test before it is
written down as a pattern.

## Publishing alongside the repository

Upload the build notebook or script, the README, and the environment file next
to the Icechunk prefix so the store is self-describing. On Source Cooperative
this is an ordinary S3 upload with the same temporary credentials.
