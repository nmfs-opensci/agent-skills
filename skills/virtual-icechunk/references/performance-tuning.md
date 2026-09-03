# Read performance: diagnose and prevent

Use this when asked why a store is slow, whether a store *will* be slow, or to
review a plan before it is built. Slow reads are the most common complaint about
virtual stores, and most of the causes are decisions made at build time that
cost nothing to get right and are expensive to fix afterwards.

Reference: <https://icechunk.io/en/v2.2.0/guides/performance/>

## The mental model

In a virtual store, **metadata and data come from two different hosts**:

| Read | Goes to | Slow because |
|---|---|---|
| Opening the store, listing variables, coordinates | The **destination** — the Icechunk repository | Manifest size and layout, coordinate chunking |
| Actual science values | The **source** — the provider's NetCDF/HDF5 files | Native chunk layout, source location, concurrency |

Establish which one is slow before doing anything else. They share almost no
causes, and the fixes are unrelated. A materialized Zarr store has one host;
this is the thing that makes virtual stores different to reason about.

## Triage, cheapest first

1. **Time the two halves separately.** Time `xr.open_zarr(...)` on its own, then
   time one small data read. Metadata-slow and data-slow are different problems.

2. **Check Zarr's concurrency.** The default is 10, which badly under-uses
   object storage. This alone accounts for multiples, not percentages.

   ```python
   import zarr
   zarr.config.get("async.concurrency")        # -> 10 (default)
   zarr.config.set({"async.concurrency": 128})
   ```

   The limit is **per individual Zarr array read/write operation**. 128 suits a
   large machine close to object storage; the useful ceiling depends on your
   location relative to the *source* and on what that service tolerates.
   Measure two or three values on a representative read rather than copying a
   number, and record what you used. This is a **reader** setting as much as a
   writer one — it belongs in the README and the loading example.

3. **Check the coordinate chunking** if metadata is the slow half. See below.

4. **Check where the source is relative to the reader.** Data bytes come from
   the provider, so a store whose repository is in `us-east-1` but whose
   references point at a European host will have slow data reads from anywhere.
   Nothing in the Icechunk configuration changes this.

5. **Check manifest splitting and preloading** for a large time series.

6. **Check Dask.** Dask threads or workers sit above Zarr's per-operation limit,
   so if each task touches several chunks the concurrency multiplies. Thousands
   of in-flight requests stall or time out. If raising `async.concurrency` made
   things *worse*, this is why — cap it:

   ```python
   config = icechunk.RepositoryConfig(max_concurrent_requests=10)  # default 256
   repo = icechunk.Repository.open(storage=storage, config=config)
   ```

7. **Check the reader's own call.** `chunks={}` gives Dask arrays with the
   backend's preferred chunks — use it before concatenating groups. `chunks=None`
   gives no Dask, and a large selection materializes as NumPy on access.

8. **Check whether the bucket is cold.** Object stores reshard based on observed
   load, so a new bucket or repository is measurably slower until it warms. Do
   not benchmark a first run on a fresh bucket.

9. **Only then, the source's native chunk layout.** This is the one cause you
   cannot configure away — see "Unfixable" below.

## Design decisions that cause slow reads

Flag these during Research & plan, and when reviewing someone else's plan. Each
has produced a real problem in these builds.

| Decision | Consequence | Do instead |
|---|---|---|
| Appending one-time-step files without chunking the loaded coordinate | One inline chunk per timestamp; metadata reads crawl at scale | Chunk the combine coordinate on write (below) |
| No manifest splitting on a long time series | One enormous manifest fetched on open | Split on the combine dimension |
| Lazily loading manifests for a store users open repeatedly for one small read | First-read latency every time | Configure preloading |
| Splitting into many groups or repositories when one would do | Users open and concatenate several stores | Prefer one repository, one group, many variables |
| References pointing at a host far from the intended readers | Every data read crosses a region or an ocean | Choose the reference scheme deliberately; document the restriction |
| In-region `s3://` references | Fast in that region, slow or unusable outside | Decide consciously; consider HTTPS for reach |
| Loading more than the coordinates | Materializes data that should have stayed virtual | Keep `loadable_variables` minimal |
| Publishing timings without the concurrency setting and region | Nobody can reproduce or interpret them | Record both |

## Chunk the loaded coordinates

The single most common metadata-performance mistake here. Do it on **every**
multi-file build, proactively — not after someone reports that opening the store
takes minutes.

```python
vds = open_virtual_mfdataset(urls, loadable_variables=["time", "lat", "lon"], ...)
vds.vz.to_icechunk(session, encoding={"time": {"chunks": (len(vds.time),)}})
```

Both halves matter. `loadable_variables` materializes the coordinates so the
science arrays stay virtual — without it there is no coordinate array to chunk.
The `encoding` writes the whole time coordinate as **one** chunk instead of
thousands. It changes only the materialized coordinate; it does **not** rechunk
the virtual science data, and nothing can. Apply the same reasoning to any other
coordinate you load.

## Manifest splitting and preloading

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
They partition Icechunk metadata; they do not rechunk source data.

Manifests load lazily, so the first read of an array pays the fetch.
`ManifestPreloadConfig` with a `ManifestPreloadCondition` (`name_matches`,
`path_matches`, combined via `and_conditions`/`or_conditions`) loads matching
manifests when a session opens — memory for lower first-read latency.

## Unfixable: the source's native chunk layout

Virtualization preserves source chunks exactly. If a daily global field is
stored contiguously, a one-point time series must fetch most of every field, and
no Icechunk or Zarr setting changes that. Chunks that are too small make request
overhead dominate; chunks that are too large over-fetch.

When you hit this, say so plainly rather than tuning around it. The only real
fix is republishing the source files, which is usually not available — see
`source-file-design.md` for the exceptional case where it is.

## Reporting a diagnosis

Say which half is slow, what you measured, what you changed, and what the
remaining floor is. Quantify against a baseline where you can: "metadata open
went from 90 s to 2 s by chunking the time coordinate; data reads are 4× faster
at `async.concurrency=128`; the point time series is still slow and cannot be
fixed without republishing the source files." Record the numbers with package
versions, region, cold or warm cache, and concurrency settings, per
`validation.md`.
