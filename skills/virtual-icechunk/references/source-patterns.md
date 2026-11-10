# Source patterns

Source access determines discovery, authentication, the parser, and the URLs
embedded in virtual references. It does **not** determine where the Icechunk
repository lives. Read `destination-patterns.md` for that half.

## The stable mechanics

Every source, regardless of provider, needs the same four objects:

```python
from obstore.store import from_url
from obspec_utils.registry import ObjectStoreRegistry
from virtualizarr.parsers import HDFParser   # or NetCDF3Parser
import icechunk

url_prefix = "https://example.org/path/"     # MUST end in "/"
store = from_url(url_prefix)
registry = ObjectStoreRegistry({url_prefix: store})
parser = HDFParser()

config = icechunk.RepositoryConfig.default()
config.set_virtual_chunk_container(
    icechunk.VirtualChunkContainer(
        url_prefix=url_prefix,
        store=icechunk.http_store(),         # or icechunk.s3_store(...)
    )
)
```

Rules that hold for every source:

- **Discover explicit URLs first.** VirtualiZarr V2 does not expand globs in
  `open_virtual_mfdataset`; pass a list you built and sorted yourself.
- **Supply the parser and the registry explicitly.** V2 does not guess.
- **Match the parser to the real format.** `NetCDF3Parser` for classic NetCDF,
  `HDFParser` for NetCDF4/HDF5. An archive may contain both across its history.
- **Every virtual prefix must be registered and later authorized**, including
  anonymous HTTP. A missing authorization is the most common read failure.
- **`url_prefix` must end in `/`** and must match the reference URLs exactly.
- **Load only small variables.** Pass `loadable_variables=["time", "lat",
  "lon"]` (or the equivalent) so coordinates materialize and science arrays stay
  virtual.
- **Save the repository config** with `repo.save_config()` so later public
  readers can discover the virtual containers.

## Provider adapters

Each of these is drawn from a real workflow. Treat the details as
provider-specific, and re-check them against the provider's current
documentation before reuse.

### NASA Earthdata (PACE, and other DAACs)

- Discovery: `earthaccess.search_data(short_name=..., temporal=...)`, filtered
  by cadence and grid, then in-region S3 links.
- Authentication: `earthaccess.login()` for discovery; **temporary** OBDAAC S3
  credentials for the data reads. They expire — see `known-issues.md`.
- Virtualization: `earthaccess.virtualize` wraps the parser/registry setup for
  Earthdata holdings. Reads typically require `us-west-2`.
- References embed `s3://` URLs, so consumers outside that region may be unable
  to read the store at all. **Prefer HTTPS references for new work**, for reach.
  An in-region S3 store may still be worth building alongside it because it can
  be faster; which one is the published product is undecided. Either way,
  record the restriction in the project README.
- PACE derives `time` from the filename because the file metadata was
  insufficient. This is **not preferred** — it was difficult to get right. Use
  in-file time whenever it is trustworthy. If you must fall back to the
  filename, validate it against the product's real cadence, separately for
  daily, monthly, and 8-day products.
- The PACE CHL product has been renamed to **BGS**. Use the new naming.

### Copernicus Marine (GlobColour)

- Discovery: `copernicusmarine get --create-file-list`, then sort the saved
  list. Keep the list as the source manifest.
- The provider S3 URLs are rewritten to CloudFerro HTTPS
  (`https://s3.waw3-1.cloudferro.com/...`) for the virtual references.
- Virtual reads are **intentionally anonymous**, using
  `icechunk.credentials.HttpAccess`, and the rewritten CloudFerro URLs are
  believed stable (project owner, 2026-09-03). Older notebook prose claiming
  consumers need Copernicus credentials is wrong. Re-verify if reads start
  failing.
- Parser: `HDFParser` over an `ObjectStoreRegistry` on the HTTPS prefix.

### NOAA CoastWatch over plain HTTPS

- Discovery: scrape Apache directory listings, walk year folders, retry slow
  listings, and sort filenames. Retry the top-level listing too, not just the
  per-year ones.
- Anonymous HTTPS. A browser-like `User-Agent` header is required for the
  Python discovery and parser requests, which otherwise get HTTP 403.
  Icechunk's own User-Agent succeeds for the payload reads.
  **This is a source-access workaround. It is not a CORS finding and says
  nothing about browser support.**
- The archive spans formats: `NetCDF3Parser` for the older group, `HDFParser`
  for current HDF5, with separate fsspec reader options for NetCDF3.

### Anonymous public S3 (NODD and similar)

No validated example exists in the reviewed repositories. The mechanics are the
generic ones above with `icechunk.s3_store(region=..., anonymous=True)` as the
virtual container store; verify against current Icechunk storage documentation
and prove it with a smoke test before treating it as a pattern.

### Sources you control

If you produce or can republish the source files, their layout is a design
decision rather than a constraint — see `source-file-design.md`. Fixing the
chunk grid before publication is the only opportunity to fix it at all.

## THREDDS and ERDDAP: does the server expose files at all?

Most US ocean data sits behind a THREDDS Data Server (TDS), an ERDDAP, or
both. A virtual reference needs a **file** at a stable URL that honours byte
ranges. Most of what these servers offer is a **generated response** instead:
the server reads the file, cuts out the request, and re-encodes it. A generated
response cannot be referenced, however reliable it looks.

Answer this first, before any parser work. The checks are general, because they
follow from how the software works. Whether a given server passes them is a
per-server, often per-dataset, admin setting, so one server's answer says
nothing about another's.

### THREDDS (TDS)

- **Only the `HTTPServer` service serves files**, at `/thredds/fileServer/...`.
  OPeNDAP (`/dodsC/`), NCSS (`/ncss/`), WMS, WCS and NcML are generated. Look
  for a `serviceType="HTTPServer"` entry in the dataset's catalog XML, then make
  a ranged request against a `fileServer` URL and expect HTTP 206.
- **Paths can be hidden on purpose.** `/thredds/ncml/<dataset>` returning
  `location="Not provided because of security concerns."` means the admin hid
  the file paths. Treat it as a deliberate policy, ask the data owner, and do
  not try to work around it.
- **The `.das` shows native chunking before you have a file.** For NetCDF-4
  sources, `<OPeNDAP URL>.das` lists `_ChunkSizes` per variable. TDS 4.6 did not
  show compression; check a real file for that.
- **Forecast collections (FMRC) are not a file list.** The `runs/` catalog
  lists one virtual dataset per model run, the `files/` catalog (when enabled)
  lists the real run files, and the "Best" time series is stitched from
  overlapping runs. A virtual store of the best series must choose which run
  supplies each step, which is only chunk-aligned when there is one step per
  chunk. A `files/` catalog that returns 404 means the raw run files are not
  exposed.

### ERDDAP

- **A griddap download is always generated, so it can never be referenced.**
  The `.nc` it returns is NetCDF-3 classic, uncompressed, with fixed dimensions.
  It carries the source's `_ChunkSizes` attribute, which describes nothing in
  that file.
- **Variables and units may differ from the source.** Per-dataset
  configuration can rename coordinates (commonly `lat`/`lon` to
  `latitude`/`longitude`) and re-encode time (seconds since 1970). Do not infer
  source names or units from an ERDDAP response.
- **ERDDAP may be only a proxy.** `NC_GLOBAL:sourceUrl` in
  `/erddap/info/<datasetID>/index.json` shows what is behind it, often a THREDDS
  OPeNDAP URL. Then the THREDDS checks above decide.
- **`/erddap/files/<datasetID>/` is the only route to real files**, and only
  where the admin enabled it. No virtual store has been built against it yet.
- ERDDAP's `/info/` and `/search/` JSON are the fastest way to size a dataset:
  dimensions, lengths, time coverage and variables, in one small request.

### When the answer is no

The source cannot be virtualized from outside, whatever the parser. The options
are the data owner's to grant: enable `HTTPServer`; copy the unchanged files to
object storage and virtualize against the copy; or republish reprocessed files
(`source-file-design.md`). A **temporary** file endpoint is fine for copying
but never for references: every reference breaks when it is switched off.

Generated services are also slow for bulk transfer, because the server
re-encodes every response. Do not use their throughput to estimate a plain file
copy.

Evidence: PacIOOS (`pae-paha.pacioos.hawaii.edu`, ERDDAP 2.29.0 and TDS 4.6),
probed 2026-11-10. Every check above came back closed there: no `HTTPServer`,
paths hidden, `files/` 404 on both servers, ERDDAP proxying THREDDS OPeNDAP, and
about 1 MB/s through either generated service. That is one server's
configuration. Many THREDDS servers do offer `fileServer`.

## Sources with no validated example

Do not invent an adapter section for these. Research them fresh, prove them in a
smoke test, and only then write them down:

- ERDDAP's `files/` endpoint, and THREDDS `fileServer`, as the source of a
  built store. The checks above say whether they exist, not that a build
  against them works.
- Any browser/WASM read path, for any provider.
- Signed or expiring source URLs (probably incompatible with virtual references).
