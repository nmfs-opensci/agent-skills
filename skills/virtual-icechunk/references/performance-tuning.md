# Performance tuning

Two different things limit a virtual store, and they have different fixes:

- **The source's native chunk layout.** Unfixable without republishing the files
  (`source-file-design.md`). Measure it, document it, do not promise it away.
- **Concurrency and metadata layout.** Very fixable, and easy to leave at
  defaults that are far too conservative. Everything below is in this category.

Check these against the Icechunk performance guide for your installed version:
<https://icechunk.io/en/v2.2.0/guides/performance/>

## Zarr async concurrency — check this first

Zarr's default is **10 concurrent requests**, which badly under-uses object
storage. Reads that feel mysteriously slow are usually this.

```python
import zarr
zarr.config.get("async.concurrency")        # -> 10 (default)
zarr.config.set({"async.concurrency": 128})
```

- The limit is **per individual Zarr array read/write operation**, not global.
- 128 is Icechunk's suggested value for a large machine close to object
  storage. The useful ceiling depends on where you are relative to the store and
  on the source service — a cross-region HTTPS source will plateau much sooner
  than in-region S3. **Measure it for your location** rather than copying a
  number; try a few values on a representative read and record what you used.
- This is a reader-side setting as much as a writer-side one. Put it in the
  project README and the loading example, not just in the build script.

## Icechunk's global request cap

Each repository caps its own concurrent requests, default **256**:

```python
config = icechunk.RepositoryConfig(max_concurrent_requests=10)
repo = icechunk.Repository.open(storage=storage, config=config)
```

Lower it when something downstream is generating too much concurrency.

## Dask multiplies concurrency

Dask threads or workers sit above Zarr's per-operation limit, so if each task
touches several chunks the concurrency multiplies. Thousands of in-flight HTTP
requests stall or time out. If you raise `async.concurrency` and things get
*worse* under Dask, that is the interaction — cap it with
`max_concurrent_requests` rather than hunting for a network fault.

## Chunk the loaded coordinates

The single most common metadata-performance mistake in these builds. Sources
with one time step per file produce one inline chunk per timestamp, and metadata
reads become unbearable at scale.

```python
vds = open_virtual_mfdataset(urls, loadable_variables=["time", "lat", "lon"], ...)
vds.vz.to_icechunk(session, encoding={"time": {"chunks": (len(vds.time),)}})
```

Both halves matter:

- `loadable_variables` materializes the coordinates — the science arrays stay
  virtual. Without it you cannot combine, and without it there is no coordinate
  array to chunk.
- The `encoding` writes the whole time coordinate as **one** chunk instead of
  thousands. This changes only the materialized coordinate. It does **not**
  rechunk the virtual science data, and nothing can.

Do this on every build with many files, not only when it has already become
slow. Apply the same reasoning to any other coordinate you load.

## Manifest splitting

For large time series, split Icechunk manifests so metadata stays manageable:

```python
config.manifest = icechunk.ManifestConfig(
    splitting=icechunk.ManifestSplittingConfig.from_dict(
        {icechunk.ManifestSplitCondition.AnyArray():
            {icechunk.ManifestSplitDimCondition.DimensionName("time"): 100}}
    )
)
config.manifest.max_concurrent_manifest_fetches_during_commit = 16
```

**Experimental tuning, not a constant.** 100 time chunks per split and 16
concurrent fetches are a reasonable starting point used on several large builds.
They partition Icechunk metadata; they do not rechunk source data. Record what
you used and why.

## Manifest preloading

Manifests load lazily, so the first read of an array pays the manifest fetch.
`ManifestPreloadConfig` with a `ManifestPreloadCondition` (`name_matches`,
`path_matches`, combined with `and_conditions`/`or_conditions`) loads matching
manifests when a session opens, trading memory for lower first-read latency.
Worth considering for a store whose users repeatedly open it for one small read.

## Cold buckets

Object stores reshard based on observed load, so a brand-new bucket or
repository can be measurably slower than the same store once it is warm. Do not
draw conclusions from a first-run benchmark on a fresh bucket.

## What to record

Whatever you tune, write the values into the README alongside the timings in
`validation.md`: `async.concurrency`, any `max_concurrent_requests`, the
manifest split settings, and the region the numbers were measured from. A timing
without its concurrency setting and location is not interpretable.
