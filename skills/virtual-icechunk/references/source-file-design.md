# Designing source files that virtualize cleanly

**Being able to change the source files is the exception, not the norm.**
Usually the files belong to a provider and their layout is a hard constraint.
This reference applies in the uncommon case where you produce the files
yourself, or the data owner has explicitly cleared you to reprocess and
republish them — for example producing NetCDF for NOAA Open Data Dissemination
(NODD) that a virtual Icechunk store will later reference. Confirm you have that
permission before proposing it; do not assume it.

When you do have it, take it seriously: getting the layout right here is the
only chance to fix chunking at all, because virtualization copies no data.

Reference implementation: RFROM v2.3 for NODD —
<https://github.com/nmfs-opensci/gobai-rfrom-icechunks/blob/main/RFROMV/prep-one-netcdf-for-NODD.ipynb>

## When to reach for this

The source layout is unusable for the intended access pattern, and no metadata
setting can fix it:

- chunk grids differ from file to file, so files cannot share one Zarr chunk
  grid;
- arrays are stored unchunked or contiguously across a dimension users will
  slice;
- one time step per file, producing a pathological coordinate;
- compression filters that Zarr codecs cannot represent;
- dtype or fill value drifting between files.

If you cannot republish, build the virtual store anyway, measure the cost, and
state the limitation plainly in the README. The owner decides.

## Rules for files intended to be virtualized

- **One chunk grid for every file.** Choose a physical chunk shape and apply it
  identically everywhere. Files then concatenate onto one regular Zarr chunk
  grid. Only the final block may be a smaller last chunk.
- **Batch many steps of the combine dimension into each file** so the combine
  coordinate stays contiguous. A file per time step is what produces the
  one-inline-chunk-per-timestamp slowdown described in `known-issues.md`.
- **Store coordinates contiguously** — a single chunk per file.
- **Use codec-representable compression.** `zlib`/deflate plus `shuffle` both map
  to Zarr codecs, so virtual references keep working with compression on.
- **Pin `dtype` and `_FillValue` identically across every file**, so the virtual
  dataset has one consistent dtype and fill value.
- **Size chunks for the real query**, not for the writer's convenience. A chunk
  of order 10 MB is a common compromise.
- **Separate product streams into their own prefixes** (stable / realtime /
  error, and one prefix per product version). Each is then a single clean glob
  for the downstream build, and a reprocessing lands under a new prefix so
  existing stores keep working.
- **Make the file CF-compliant** while you have the data open: `standard_name`,
  `units`, `axis`, `positive` on the vertical coordinate, `Conventions`, and a
  `history` note. Fix contradictory inherited attributes rather than passing
  them through. Confirm inferred `standard_name` values against the CF standard
  name table; they are easy to get subtly wrong.

## Writing efficiently

Dask chunks and on-disk chunks are different things. Keep the dask chunks larger
than, and an exact multiple of, the on-disk chunks, so each on-disk chunk is
written once and each read pulls a contiguous slab from the source rather than
many strided sub-tiles.

## Verify before uploading

Reopen the written file and print the stored chunking, the compression
settings, the fill value, and the CF attributes. Then upload, and confirm the
object landed at the expected size.
