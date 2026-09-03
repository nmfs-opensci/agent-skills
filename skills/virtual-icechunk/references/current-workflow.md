# Current end-to-end workflow

The strongest provisional general pattern, with provider details injected only
at the marked boundaries. Steps 1–7 involve no destination credentials at all.

1. **Record versions.** icechunk, virtualizarr, xarray, zarr, obstore, provider
   client, Python. `version-matrix.md`.

2. **Discover source objects** with the provider's API, CLI, or listing.
   *(source-specific — `source-patterns.md`)* Save the ordered list as a source
   manifest. It is what makes restart and completion checking possible.

3. **Probe representative objects** on both sides of every suspected transition:
   byte-range access, authentication, format, dimensions, native chunks, codecs,
   coordinates, schema.

4. **Partition the manifest** so each target Zarr array is homogeneous in
   dimensions, shape apart from the combine dimension, chunk grid, dtype,
   codecs, and meaningful schema. `research-and-plan.md`.

5. **Build the source objects:** `from_url` → `ObjectStoreRegistry` → the right
   parser → an Icechunk `VirtualChunkContainer` whose `url_prefix` ends in `/`.

6. **Open a one-file virtual dataset.** Load only coordinates and small
   variables via `loadable_variables`. Apply documented dataset-specific
   metadata repair here, without materializing science arrays.

   Metadata is the one thing a virtual store *can* fix, so fix it: make the
   result CF-compliant (`standard_name`, `units`, `axis`, `positive` on a
   vertical coordinate, `Conventions`), drop attributes that contradict the
   real encoding, and sanitize values that cannot be JSON-serialized. Record
   every change. Confirm inferred `standard_name` values against the CF
   standard name table.

7. **Smoke-test locally**, before any destination is configured.
   `smoke-test-notebook.md`.

8. **Configure the destination independently.** *(destination-specific —
   `destination-patterns.md`)* Create or explicitly open the repository, then
   persist the intended configuration with `repo.save_config()`.

9. **Combine compatible files** — either one multi-file virtual dataset or
   ordered append batches. Set chunking only for the materialized coordinate
   arrays; virtual science arrays keep their source chunks.

   ```python
   vds = open_virtual_mfdataset(urls, loadable_variables=["time", "lat", "lon"], ...)
   vds.vz.to_icechunk(session, encoding={"time": {"chunks": (len(vds.time),)}})
   ```

   Do this on every multi-file build, not only when metadata reads have already
   become slow — see `performance-tuning.md`.

10. **Write and commit a recoverable unit.** Record the snapshot ID and the
    manifest position it corresponds to, then open a fresh writable session.

11. **Reopen from the consumer-facing read path** with explicit per-prefix
    virtual authorization and a `readonly_session`.

12. **Validate** structure, coverage, values, and representative reads. Tag the
    finished build. Publish the README, the loading example, and the environment
    file. `validation.md`, `project-docs.md`.

## Reading the finished store

```python
import icechunk as ic
import xarray as xr

storage = ic.http_storage("https://data.source.coop/<account>/<prefix>")
repo = ic.Repository.open(storage)
auth = {p: ic.credentials.HttpAccess for p in repo.config.virtual_chunk_containers or []}
store = repo.reopen(authorize_virtual_chunk_access=auth).readonly_session("main").store
ds = xr.open_zarr(store, consolidated=False, chunks={})
```

Readers should raise `zarr.config.set({"async.concurrency": 128})` too; it is
not a writer-only setting (`performance-tuning.md`).

`HttpAccess` is right for anonymous HTTPS sources. An S3-backed source needs the
matching S3 credential type instead, and the reader needs credentials the writer
never had to think about. Use `chunks={}` when you will concatenate groups, so
nothing materializes eagerly; `chunks=None` gives NumPy on access.

## Performance

Before timing anything, raise Zarr's async concurrency — the default of 10 is
the most common cause of a store that "feels slow". Manifest splitting,
preloading, and the concurrency interaction with Dask are all in
`performance-tuning.md`.
