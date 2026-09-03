# Virtual Icechunk workflow patterns

> **Status: provisional analysis for project-owner review.** This document was
> researched on 2026-09-03. It describes virtual-reference stores only; it is not
> a standard and does not cover materialized Icechunk writes. Upstream APIs and
> operational conclusions must be rechecked before this analysis becomes a skill.

## 1. Executive summary

The three repositories show a recognizable workflow—discover source objects,
virtualize compatible files, write references to Icechunk, commit, and reopen the
result—but not one universally applicable implementation.

* **Likely general pattern:** keep source access and destination storage as two
  independent configurations; prove byte-range access; load only coordinates or
  other small variables; preserve source data chunks; combine only
  schema/chunk/codec-compatible files; configure and authorize every virtual
  chunk prefix explicitly; commit recoverable units; and validate through the
  public read path.
* **Provider-specific:** NASA PACE uses Earthaccess, temporary OBDAAC credentials,
  and in-region S3. Copernicus uses its CLI for discovery and CloudFerro HTTPS for
  virtual reads. CoastWatch uses Apache listings, HTTP range requests, and a
  source-specific User-Agent workaround.
* **Destination-specific:** all three production attempts use Source Cooperative,
  but its endpoint, path-style S3 setup, temporary write credentials, and earlier
  compatibility patch are not source-access requirements and should not be
  generalized to Arraylake or other object stores.
* **Dataset-specific:** PACE chlorophyll and CoastWatch OHC split data into groups
  where native chunk shapes, schemas, grids, formats, or endian codecs differ.
  Virtual stores cannot make incompatible source encodings one homogeneous Zarr
  array without materializing data.
* **Still unsettled:** dependency locking, automated incremental updates,
  state-derived restartability, commit size, branch/tag policy, comprehensive
  validation, and browser access.

Most importantly, **none of the three current repository trees contains an
ERDDAP workflow**. The newest repository uses NOAA CoastWatch over ordinary
HTTPS, not ERDDAP. Its browser-like User-Agent is a Python source-access
workaround, not evidence about browser CORS. ERDDAP and CORS therefore remain
isolated, unresolved topics rather than general patterns.

## 2. Repository chronology

The repositories overlap in time, but their surviving implementations form this
approximate sequence:

| Period | Repository and generation | Evidence and interpretation |
|---|---|---|
| 2026-06-27 to 2026-07-27 | [`fish-pace/pace-icechunks`](https://github.com/fish-pace/pace-icechunks/tree/77adbd0d158fe446756e3496fe5a2ab1005a48a8): NASA PACE OCI | Initial CHL notebooks appeared in [`de6b6dc`](https://github.com/fish-pace/pace-icechunks/commit/de6b6dcb51122c4c7b3ef8457b70de0ad6abb2a0); RRS in [`0b4338d`](https://github.com/fish-pace/pace-icechunks/commit/0b4338d2c3424b4a943198bb5910f67f48b7e9a6); Kd was refined through [`8b24f34`](https://github.com/fish-pace/pace-icechunks/commit/8b24f347ba5495e63ab471e534f493e34d26e4ca). Temporary-credential recovery and cadence/grid groups developed here. Copernicus experiments were added on July 24, then deliberately removed in [`8e88bfb`](https://github.com/fish-pace/pace-icechunks/commit/8e88bfb716c486d7bd5978045dcbb1f81779e5df); they are history, not current code. |
| 2026-07-25 to 2026-08-06 | [`fish-pace/globcolour-Icechunks`](https://github.com/fish-pace/globcolour-Icechunks/tree/03b273566415ea7ea3eeb2c391ca1b2e70676f37): Copernicus GlobColour | Prototypes arrived in [`936edc0`](https://github.com/fish-pace/globcolour-Icechunks/commit/936edc04ba1767ce92c016822c7454b978d00833); “need to fix manifest” expanded the catalog in [`f9aa826`](https://github.com/fish-pace/globcolour-Icechunks/commit/f9aa8263bac2255171284bf71dc32e953481c5c8); [`03b2735`](https://github.com/fish-pace/globcolour-Icechunks/commit/03b273566415ea7ea3eeb2c391ca1b2e70676f37) added manifest splitting and restart logic. The checked output validates 5,740 of a listed 10,490 files, so completion is not established. |
| 2026-08-25 to 2026-08-26 | [`fish-pace/icechunks`](https://github.com/fish-pace/icechunks/tree/447ff435dfd70ed3438a9d12bf5e7a22ec309fc8): NOAA CoastWatch OHC | The full pipeline landed in [`a9a674e`](https://github.com/fish-pace/icechunks/commit/a9a674e0633f1d3a1529f7be335865d6c156c8a1), with smoke tests in [`4dc330f`](https://github.com/fish-pace/icechunks/commit/4dc330fb86275c2ea624216a5f7aafb51df7947a). [`2b54a2b`](https://github.com/fish-pace/icechunks/commit/2b54a2b2eeb5cb1bdfb469a7baa29f2a6056b578) records incremental updates as undesigned. [`e7546f7`](https://github.com/fish-pace/icechunks/commit/e7546f70e6b89edb0a071ad22493527d2300915d) changed destination references but explicitly left rebuilding for later. |

Relevant issues explain choices better than the minimal READMEs:

* PACE [issue 1](https://github.com/fish-pace/pace-icechunks/issues/1)
  motivated the removed Copernicus experiment and prohibited a hard-coded user.
* CoastWatch [issue 2](https://github.com/fish-pace/icechunks/issues/2)
  documents the schema/codec boundaries, missing-value behavior, and the
  one-element time-chunk performance problem.
* CoastWatch [issue 9](https://github.com/fish-pace/icechunks/issues/9) asks for
  future standardization while requiring current package-version checks.
* The only GlobColour issue is explicitly a
  [materialized GOBAI write](https://github.com/fish-pace/globcolour-Icechunks/issues/1);
  it is outside this analysis.

No explanatory issue comments or review threads were found in the three projects.

## 3. Package-version comparison

| Project | Recorded environment | Icechunk | VirtualiZarr | Xarray / Zarr | Reproducibility assessment |
|---|---|---|---|---|---|
| PACE | [`environment.yml`](https://github.com/fish-pace/pace-icechunks/blob/77adbd0d158fe446756e3496fe5a2ab1005a48a8/environment.yml) specifies Python 3.12 and `earthaccess>=0.18`; notebook output shows Python 3.12.12 and Earthaccess 0.18.0 | Unpinned upgrade | Unpinned upgrade | Both unpinned | Weak: no lockfile or recorded versions for the core stack. |
| GlobColour | Notebook metadata records Python 3.12.12 | Current production output records 2.1.2; the diagnostic notebook records a local `2.1.1+patched` wheel | Unpinned upgrade | Both unpinned | Weak: [`copernicus-icechunk-sc.ipynb`](https://github.com/fish-pace/globcolour-Icechunks/blob/03b273566415ea7ea3eeb2c391ca1b2e70676f37/copernicus-icechunk-sc.ipynb) installs latest packages at run time; no environment file exists. |
| CoastWatch | Notebook metadata records Python 3.12.12 | `>=2.1` | `>=2.4` | Both unpinned | Better lower bounds, but no lockfile and some imported direct dependencies are omitted from the install cell in [`ocean-heat-production-sc.ipynb`](https://github.com/fish-pace/icechunks/blob/447ff435dfd70ed3438a9d12bf5e7a22ec309fc8/coastwatch-heat-content/ocean-heat-production-sc.ipynb). |
| Current official releases checked 2026-09-03 | VirtualiZarr 2.7.3 requires Python ≥3.12 | 2.2.0 | 2.7.3 | Xarray 2026.07.0; Zarr-Python 3.3.0 | These are comparison points, not retroactive claims about notebook runtimes. |

Current API facts were checked against versioned official documentation:

* Icechunk 2.2.0:
  [storage](https://icechunk.io/en/v2.2.0/guides/storage/),
  [configuration and virtual credentials](https://icechunk.io/en/v2.2.0/guides/configuration/),
  [virtual datasets](https://icechunk.io/en/v2.2.0/guides/virtual/), and
  [transactions/version control](https://icechunk.io/en/v2.2.0/understanding/version-control/).
* VirtualiZarr 2.7.3:
  [API](https://virtualizarr.readthedocs.io/en/stable/api/virtualizarr.html) and
  [V2 migration guide](https://virtualizarr.readthedocs.io/en/stable/migration_guide.html).
* Xarray 2026.07.0:
  [`open_zarr`](https://docs.xarray.dev/en/v2026.07.0/generated/xarray.open_zarr.html),
  [`to_zarr`](https://docs.xarray.dev/en/v2026.07.0/generated/xarray.Dataset.to_zarr.html),
  and the [Zarr encoding specification](https://docs.xarray.dev/en/v2026.07.0/internals/zarr-encoding-spec.html).
* Zarr-Python 3.3.0:
  [storage](https://zarr.readthedocs.io/en/stable/user-guide/storage/),
  [performance](https://zarr.readthedocs.io/en/stable/user-guide/performance/), and
  [v3 migration](https://zarr.readthedocs.io/en/stable/user-guide/v3_migration/).

## 4. Source-access comparison

Source access determines discovery, authentication, parser, and the URLs embedded
in virtual references. It does **not** determine where the Icechunk repository is
stored.

| Concern | NASA PACE | Copernicus GlobColour | NOAA CoastWatch OHC |
|---|---|---|---|
| Discovery | `earthaccess.search_data` by short name, date range, cadence, and grid; get in-region links. See [`pace-chl-icechunk-sc.ipynb`](https://github.com/fish-pace/pace-icechunks/blob/77adbd0d158fe446756e3496fe5a2ab1005a48a8/pace-chl-icechunk-sc.ipynb). | `copernicusmarine get --create-file-list`, then sort the saved list. See [`copernicus-icechunk-sc.ipynb`](https://github.com/fish-pace/globcolour-Icechunks/blob/03b273566415ea7ea3eeb2c391ca1b2e70676f37/copernicus-icechunk-sc.ipynb). | Scrape Apache directory listings, discover year folders, retry slow listings, sort names, and split at known filenames. See [`ocean-heat-production-sc.ipynb`](https://github.com/fish-pace/icechunks/blob/447ff435dfd70ed3438a9d12bf5e7a22ec309fc8/coastwatch-heat-content/ocean-heat-production-sc.ipynb). |
| Source authentication | Earthaccess login for discovery; temporary OBDAAC S3 credentials for consumer reads. | The CLI may authenticate discovery. Checked virtual reads use anonymous CloudFerro HTTPS `HttpAccess`; the notebook's statement that reads require Copernicus credentials is not demonstrated. | Anonymous HTTPS. A browser-like User-Agent is needed by Python discovery/parser requests; Icechunk's own User-Agent succeeds for payload reads. |
| Embedded reference scheme | `s3://ob-cumulus-prod-public/...` in `us-west-2`. | Convert provider S3 URLs to `https://s3.waw3-1.cloudferro.com/...`. | Native `https://coastwatch.noaa.gov/...` URLs. |
| Parser | HDF/NetCDF4 via HDF parser, largely through `earthaccess.virtualize`. | `HDFParser` with an `ObjectStoreRegistry` over HTTPS. | `NetCDF3Parser` for older groups and `HDFParser` for current HDF5. NetCDF3 needs separate fsspec reader options. |
| Loaded data | PACE passes `load=False`; filename-derived time is assigned. | Load coordinate candidates and decode time; science arrays remain virtual. | Load `time`, `latitude`, and `longitude`; science arrays remain virtual. |
| Source validation | In-region URL and selected data reads. | Sorted first/last URL and one plotted slice; no complete source-list reconciliation. | Assert HTTP 206, exact boundary names, source magic bytes, and group boundaries. |
| Browser evidence | None. | Destination CORS headers were inspected in a debug notebook; source CloudFerro CORS and end-to-end browser reads were not. | None; User-Agent and range tests ran in Python, not a browser. |

### Source classifications

| Finding | Category | Status |
|---|---|---|
| Discover explicit URLs before calling `open_virtual_mfdataset` | Likely current general pattern | VirtualiZarr V2 does not expand globs in `open_virtual_mfdataset`; provider discovery stays pluggable. |
| Parser + `ObjectStoreRegistry` for `open_virtual_dataset` | Likely current general pattern | Required by VirtualiZarr V2; use the parser appropriate to actual file format. |
| Load coordinates/small metadata but not science payload | Likely current general pattern | Needed for combination while preserving virtualization. The exact variable list is dataset-specific. |
| Earthaccess and OBDAAC credentials | Source-specific | NASA only; keep source credentials separate from destination credentials. |
| Copernicus CLI and S3-to-CloudFerro-HTTPS rewrite | Source-specific | Validate URL stability, query requirements, and anonymous access before reuse. |
| Apache scraping, filename boundary, retries, and browser User-Agent | Source-specific / dataset-specific | CoastWatch only. The top-level year request lacks the same retry protection as file listings. |
| Replace all grids from a trusted file, drop all-zero files, add `-999` metadata | Dataset-specific workaround | CoastWatch OHC only; assumptions require owner confirmation and provenance. |
| Derive PACE time from filename | Dataset-specific workaround | Appropriate only if filename semantics are authoritative for each cadence. |
| ERDDAP access | Unresolved source-specific pattern | No current implementation was found in these repositories. Do not label CoastWatch HTTP behavior “ERDDAP.” |

## 5. Destination-storage comparison

All checked production workflows target Source Cooperative, so they provide no
direct operational evidence for other NOAA/project object storage or
Earthmover/Arraylake.

| Concern | Pattern observed | Classification |
|---|---|---|
| Source Cooperative writes | Build S3-compatible storage from endpoint, region, bucket, prefix, path-style setting where needed, and temporary credentials. | Destination-specific |
| Source Cooperative reads | Open public repository metadata with `icechunk.http_storage(full_url)`. The full bucket and prefix are required. | Destination-specific |
| Credential lifetime | Refresh via Source Cooperative CLI; reopen repository and create a new writable session after commits. | Destination-specific implementation of a general expiring-credential concern |
| Repository config | CoastWatch calls `repo.save_config()` so later public readers discover virtual containers. PACE contains later config-repair cells. | Likely current Icechunk pattern |
| Create/open | Each project catches any exception from `Repository.create` and then tries `Repository.open`. | Questionable/experimental; catch only the expected “already exists” condition in a future workflow |
| Compatibility | PACE says Source Cooperative required a monkey-patched Icechunk; GlobColour's debug notebook traces failures to unsupported server-side copy and later succeeds with Icechunk 2.1.2. | Historical destination-specific workaround; likely obsolete, but verify on the target endpoint with Icechunk 2.2.0 |
| Other destinations | No implementation in the three repositories. | Unresolved: Arraylake, other S3, and NOAA/project storage need separate adapters and smoke tests |

Current Icechunk 2.2.0 documentation supports local, object-store, and read-only
HTTP repository storage and requires a non-empty prefix for newly created object
storage repositories. This is independent of the virtual source container.

## 6. Common end-to-end workflow

The following is the strongest **provisional general pattern**, with provider
details injected at the marked boundaries:

1. Record exact dependency versions and relevant provider/tool versions.
2. Discover source objects with a provider API/CLI/listing; save or hash the
   ordered manifest for audit and restart reconciliation.
3. Check representative objects for stable random byte-range access,
   authentication, format, dimensions, native chunks, codecs, coordinates, and
   schema. Check every transition, not just the first file.
4. Partition the manifest so each target Zarr array is homogeneous in dimensions,
   shape (apart from the combine dimension), chunk grid, dtype, codecs, and
   meaningful variable schema.
5. Build source-only objects: an `ObjectStoreRegistry`, the correct parser, and an
   Icechunk `VirtualChunkContainer` whose URL prefix ends in `/`.
6. Open a one-file virtual dataset. Load only coordinates and small variables
   required for combine/validation. Apply documented, dataset-specific metadata
   repair without materializing science arrays.
7. Run a local smoke test before configuring the remote destination.
8. Configure destination storage independently. Create or explicitly open the
   repository; persist intentional repository configuration.
9. Combine compatible files either in a multi-file virtual dataset or in ordered
   append batches. Set desired chunking only for materialized coordinate arrays;
   virtual science arrays retain source chunks.
10. Write through `.vz.to_icechunk`, commit a descriptive unit, record its snapshot
    ID and source-manifest checkpoint, then acquire a new writable session.
11. Reopen from the consumer-facing read path with explicit per-prefix virtual
    credentials and `readonly_session`.
12. Validate structure, time coverage, values, representative byte-range reads,
    and expected access patterns. Publish a minimal loading function and note all
    location/authentication constraints.

Current official APIs support `append_dim` and `region`, Icechunk transactions,
branches, tags, snapshots, conflict detection, and rebasing. The notebooks use
only a `main` branch and returned snapshot IDs; none establishes a branch/tag
release policy.

## 7. Smoke-test notebook pattern

A smoke test should be small enough to rerun and should isolate source behavior
from destination behavior. The CoastWatch
[`ocean-heat-test-local.ipynb`](https://github.com/fish-pace/icechunks/blob/447ff435dfd70ed3438a9d12bf5e7a22ec309fc8/coastwatch-heat-content/ocean-heat-test-local.ipynb)
is the clearest existing shape:

1. Pin/report versions.
2. Select files on both sides of every suspected schema/format/chunk transition.
3. Assert a small range request returns the expected bytes/status.
4. Inspect parser output, source chunk metadata, and codecs.
5. Create a temporary local Icechunk repository and matching virtual container.
6. Write one file, append two or three compatible files, and commit.
7. Reopen with explicit virtual authorization and Xarray.
8. Assert dimensions, coordinate order, schema, and decoded missing values.
9. Read a small field and an access-pattern-representative subset; time and plot
   them.
10. Delete only the temporary local repository.

Do not mix remote-destination debugging, destructive cleanup, or complete
production execution into the smoke-test path. A second minimal notebook may
replace only step 5 with destination storage to test endpoint semantics.

## 8. Production-build pattern

The repositories contain two competing production approaches:

| Approach | Evidence | Strength | Limitation |
|---|---|---|---|
| Sequential per-file append, commit every N files | PACE writers and GlobColour [`copernicus-icechunk-sc.ipynb`](https://github.com/fish-pace/globcolour-Icechunks/blob/03b273566415ea7ea3eeb2c391ca1b2e70676f37/copernicus-icechunk-sc.ipynb) | Fine-grained durable checkpoints; refreshes short-lived credentials | Slow repeated metadata mutation; manual `start_index` can skip or duplicate data |
| Combine all files in one compatible group, commit once | CoastWatch [`ocean-heat-production-sc.ipynb`](https://github.com/fish-pace/icechunks/blob/447ff435dfd70ed3438a9d12bf5e7a22ec309fc8/coastwatch-heat-content/ocean-heat-production-sc.ipynb) | Efficient parallel metadata opening; one coherent write | Coarse recovery; existing group is skipped even if incomplete; incremental append remains undesigned |

A future production builder should keep configurable batches but derive progress
from committed repository state plus a saved source manifest, not from an
operator-entered integer alone. Before each batch it should:

* verify ordered, unique combine coordinates;
* reject schema/chunk/codec drift into a new compatibility group;
* confirm destination credentials cover the expected batch duration;
* write and commit atomically;
* record snapshot, source IDs, counts, first/last coordinates, and versions;
* reopen and validate the committed boundary before advancing.

Manifest splitting every 100 time chunks and 16 concurrent manifest fetches
appears in the larger GlobColour, PACE RRS/Kd, and CoastWatch workflows. This is
an **experimental scale tuning choice**, not a universal constant. It partitions
Icechunk metadata; it does not rechunk source data.

## 9. Validation and performance checks

### Minimum completion checks

* Compare discovered source count/identity with committed coordinates and the
  recorded manifest.
* Check no duplicate, missing, `NaT`, unordered, or unexpected off-cadence combine
  coordinates. Model cadence correctly (for example, annual eight-day resets)
  before calling a gap an error.
* Assert dimensions, dtypes, variables, coordinate values, attributes, chunk
  shapes, and codec compatibility within every group.
* Read first, last, transition-boundary, and recent science chunks—not just
  metadata—from every group.
* Verify missing/fill decoding with assertions on known source values.
* Reopen anonymously or with consumer credentials from the published URL, not
  from the writer's in-memory repository.
* Verify every persisted virtual prefix has the intended least-privilege
  authorization and no secret.

### Evidence already present

PACE performs detailed time-axis checks in
[`pace-rrs-icechunk-sc.ipynb`](https://github.com/fish-pace/pace-icechunks/blob/77adbd0d158fe446756e3496fe5a2ab1005a48a8/pace-rrs-icechunk-sc.ipynb);
its recorded gaps need dataset-aware interpretation. Its example notebook records
rough observations including a roughly 2.65-second open of a logical 6-TB RRS
dataset and 14.5 seconds for a coarsened global slice. CoastWatch checks group
boundaries, expected variable differences, source magic bytes, and one plotted
field per region. GlobColour reopens a 5,740-step, roughly 26-TB logical dataset
and plots one date, but does not prove completion of its 10,490-file list.

These notebook timings are **observations, not benchmarks**. A repeatable
performance record should capture package versions, compute region, cold/warm
cache, concurrency, source/destination, elapsed time, bytes and request count for:

1. metadata-only open;
2. one native chunk;
3. one map/slice;
4. a short point time series;
5. the representative scientific query.

Native source chunks constrain virtual-read performance. CoastWatch notes that a
point read from a contiguous daily array may fetch most of a field; no metadata
configuration can turn that into efficient small spatial chunks without
materialization. Conversely, the CoastWatch issue identified 10,490 inline
one-element time chunks as metadata overhead. The production fix writes the
materialized time coordinate as one chunk while leaving science data virtual.

For Xarray, current [`open_zarr`](https://docs.xarray.dev/en/v2026.07.0/generated/xarray.open_zarr.html)
semantics distinguish `chunks={}` (Dask with backend-preferred chunks) from
`chunks=None` (no Dask; values become NumPy arrays when accessed). The CoastWatch
README correctly uses `chunks={}` before cross-group concatenation to avoid
eagerly materializing several GB.

## 10. README and loading-function patterns

The CoastWatch
[`README`](https://github.com/fish-pace/icechunks/blob/447ff435dfd70ed3438a9d12bf5e7a22ec309fc8/coastwatch-heat-content/README.md)
is the strongest user-facing example. A published virtual dataset README should
state:

* that science bytes remain at the source and which party operates it;
* exact public repository URL, groups, coverage, variables, and known gaps;
* why groups/repositories are separate;
* source and destination authentication as distinct steps;
* compute-region or network restrictions;
* minimum/tested package versions;
* lazy loading guidance and a representative read;
* source chunk limitations and expected performance;
* build notebook/code, source manifest, snapshot/tag, and update date;
* known unverified claims, especially browser support.

A loading function should accept dataset/group selection and obtain credentials
at call time. It should:

1. open public repository metadata;
2. read the persisted virtual-container list;
3. authorize each known prefix with the correct source credential type;
4. open a named branch/tag/snapshot;
5. call `xr.open_zarr(..., chunks={}, consolidated=False)` where appropriate;
6. concatenate only documented compatible groups and sort/check the coordinate.

PACE's
[`README`](https://github.com/fish-pace/pace-icechunks/blob/77adbd0d158fe446756e3496fe5a2ab1005a48a8/README.md)
and [`pace-icechunk-examples.ipynb`](https://github.com/fish-pace/pace-icechunks/blob/77adbd0d158fe446756e3496fe5a2ab1005a48a8/pace-icechunk-examples.ipynb)
demonstrate Earthdata read credentials and cross-chunk-group concatenation.
GlobColour's one-line README is insufficient and its notebook prose conflicts
with its anonymous HTTP authorization about whether consumers need Copernicus
credentials.

## 11. Known failure modes and lessons learned

| Failure or lesson | Evidence | Classification / response |
|---|---|---|
| Destination token expires during a multi-hour build | PACE and GlobColour recorded runs | General expiring-credential concern; Source Cooperative refresh mechanism is destination-specific. Commit and reopen before expiry. |
| Manual resume index can be wrong | Both append workflows | Experimental. Reconcile committed IDs/times against the source manifest. |
| Writable session reused after commit | Newer code always creates a fresh session | General Icechunk rule: a committed session becomes read-only. |
| Missing virtual authorization | PACE's removed Copernicus commits [`627efae`](https://github.com/fish-pace/pace-icechunks/commit/627efae749fce23a1f950277b69c02ae26998036) and [`ffa711e`](https://github.com/fish-pace/pace-icechunks/commit/ffa711ec6ffcb71610a7f94e69a9e7af0c300694) | Explicitly authorize each external prefix even for anonymous HTTP. |
| Virtual prefix mismatch | Documented in the CoastWatch project handoff | Prefixes must match and end in `/`; current Icechunk docs confirm this. |
| Config supplied but not persisted | CoastWatch requires `repo.save_config()` | Persist intentional virtual containers for later readers. |
| Source schema/chunk/codec changes | PACE CHL and CoastWatch OHC | Create separate compatible groups; concatenate compatible variables at read time. |
| Slow metadata from one-element time chunks | CoastWatch issue 2 | Choose chunks for loaded coordinate arrays explicitly. Do not confuse this with virtual payload rechunking. |
| NaN metadata cannot be serialized as JSON | CoastWatch OHC | Dataset-specific sanitation; log removed attributes. |
| Corrupt all-zero coordinates/data | CoastWatch OHC | Dataset-specific exclusion/repair; record omitted source files. |
| Default Python User-Agent receives 403 | CoastWatch | Source-specific. It is not a CORS finding. |
| Source Cooperative lacked an Icechunk operation | GlobColour debug notebook records server-side-copy HTTP 501 and a patched 2.1.1 wheel | Historical destination-specific workaround. Retest released 2.2.0; do not retain a private patch by default. |
| Catch-all create/open fallback hides root cause | All projects | Replace in future code with explicit existence handling and preserve auth/network/config errors. |
| Published destination may not match validated destination | CoastWatch [`CLAUDE.md`](https://github.com/fish-pace/icechunks/blob/447ff435dfd70ed3438a9d12bf5e7a22ec309fc8/CLAUDE.md) says the new destination still needed a rebuild | Treat availability as unresolved until a new public read succeeds. |

## 12. Older patterns that may need updating

“Obsolete” below means current official APIs provide contrary guidance; it does
not erase useful operational evidence.

| Older pattern | Current assessment |
|---|---|
| VirtualiZarr `.virtualize.to_icechunk` accessor in GlobColour prototypes | **Obsolete API name:** VirtualiZarr V2 retains it as a deprecated alias. Use `.vz.to_icechunk`. |
| Implicit VirtualiZarr parser/storage guessing | **Obsolete in V2:** supply a parser and `ObjectStoreRegistry`. Current checked workflows mostly do. |
| Icechunk 2.1.1 private patched wheel | **Likely obsolete workaround:** current production output reached 2.1.2 and official release is 2.2.0; endpoint verification is still required. |
| Unpinned `pip install -U` in production notebooks | **Questionable rather than API-obsolete:** capture a tested environment because current packages have explicit compatibility floors. |
| Zarr-Python 2 `DirectoryStore`, `FSStore`, or generic mutable mappings | **Obsolete for new Zarr-Python 3 code:** use `LocalStore`, `FsspecStore`, or the v3 async Store API per the [migration guide](https://zarr.readthedocs.io/en/stable/user-guide/v3_migration/). These names are not prominent in the checked workflows. |
| `zarr_version=` in new Zarr APIs | Prefer current `zarr_format=`. Xarray may retain compatibility aliases, so do not claim every alias is removed there. |
| `_ARRAY_DIMENSIONS` as a Zarr v3 dimension convention | **Obsolete for v3:** Xarray documents native `dimension_names`; `_ARRAY_DIMENSIONS` is the v2 convention. |
| Assuming Zarr v3 cannot use consolidated metadata | **Outdated categorical claim:** Xarray/Zarr now support it as an extension. Existing Icechunk readers explicitly use `consolidated=False`, which is valid but not a universal requirement. |
| Calling any ordinary HTTPS workaround “ERDDAP/CORS” | **Incorrect generalization:** no ERDDAP workflow or browser test exists in these trees. |

The parsers `HDFParser` and `NetCDF3Parser`, `open_virtual_dataset`,
`open_virtual_mfdataset`, `loadable_variables`, `.vz.to_icechunk`,
`Repository.create/open`, virtual containers, commits, snapshots, branches, and
tags are current APIs in the checked official versions.

## 13. Experimental or unsettled decisions

* Per-file append versus multi-file combine, and the optimal commit/checkpoint
  size.
* Manifest split threshold and commit concurrency.
* Whether a compatibility partition should be a group or an independent
  repository.
* Whether PACE's in-region S3 references are acceptable as the public product or
  whether broadly reachable HTTPS references are required.
* Whether Copernicus virtual reads are durably anonymous and whether rewritten
  URLs remain stable.
* Automated incremental discovery, append, scheduling, and conflict handling.
* Repository branches for staging, immutable tags for releases, and retention or
  garbage collection policy.
* Exhaustive validation versus sampled checks at known transitions.
* Dependency lock strategy for notebooks intended to remain runnable.
* Browser/WASM support, source and destination CORS, and browser-safe
  authentication.
* Earthmover/Arraylake and non-Source-Cooperative destination adapters.
* Whether to store the source manifest and build provenance inside or beside the
  Icechunk repository.

## 14. Questions for the project owner

1. Which repository/dataset actually contains the intended ERDDAP workflow? Was
   CoastWatch HTTPS mistakenly described as ERDDAP, or is a fourth example
   missing?
2. Which NODD example should inform anonymous S3 access? None of the three current
   trees clearly covers it.
3. Is the new `ocean-icechunks/noaa-ohc` CoastWatch destination now rebuilt and
   publicly validated, despite the checked handoff saying that remained to do?
4. Is the 5,740-step GlobColour store intentionally partial, and should the
   10,490-file source list be completed or regenerated?
5. Are CloudFerro virtual reads intentionally anonymous? If not, which
   consumer-safe credential mechanism should be documented?
6. Should PACE remain an AWS `us-west-2` in-region product, or should a future
   workflow prefer HTTPS for broader access?
7. Is filename-derived PACE time authoritative for daily, monthly, and eight-day
   products, and how should annual cadence resets be validated?
8. Should the PACE CHL-to-BGS naming change alter product IDs, destination paths,
   or only documentation?
9. Should compatibility boundaries become groups in one repository or separate
   repositories? What user-facing rule should decide?
10. What is the required restart guarantee: manual checkpoints, idempotent
    manifest reconciliation, or a fully scheduled incremental updater?
11. What branch/tag policy should identify “published,” “staging,” and immutable
    releases?
12. What completion and performance thresholds must a production build meet?
13. Must browser/WASM reading be supported? If yes, which source providers and
    authentication flows are in scope, and who owns CORS changes?
14. Which destination should be the first non-Source-Cooperative reference
    implementation: Arraylake or another object store?
15. Should future notebooks use a committed lockfile, a constrained environment,
    or record-only runtime manifests?
16. May dataset-specific repairs replace coordinates from a trusted file, or must
    corrupt files always be excluded and separately reported?

## 15. Proposed future virtual-Icechunk skill

Do not create the skill until the questions above are reviewed. A portable,
revision-friendly bundle could use:

```text
skills/virtual-icechunk/
├── SKILL.md
├── references/
│   ├── workflow.md
│   ├── compatibility-and-partitioning.md
│   ├── validation.md
│   ├── source-adapters.md
│   ├── destination-adapters.md
│   ├── browser-and-cors.md
│   └── version-matrix.md
└── scripts/
    └── (only deterministic validators justified by review)
```

The concise `SKILL.md` should:

* state that guidance is provisional and virtual-only;
* require current official documentation/version checks;
* route users through source discovery/access separately from destination setup;
* require a smoke test and compatibility partitioning before production;
* require explicit virtual authorization, recoverable commits, and public-path
  validation;
* send provider, dataset, destination, and browser details to references rather
  than presenting them as universal.

References should distinguish:

* **stable mechanics:** parser/registry, virtual-container authorization,
  commits/snapshots, compatibility checks;
* **provider adapters:** Earthaccess/NASA, Copernicus, NODD, HTTPS, and—only after
  an example is supplied—ERDDAP;
* **destination adapters:** Source Cooperative, generic object storage, and
  Arraylake;
* **dataset recipes:** PACE time/chunk splits and CoastWatch format/grid repairs,
  clearly labeled non-general;
* **experimental guidance:** batching, manifests, updates, branches/tags, and
  CORS, each with a review date.

Evaluations should ask an agent to classify a new source/destination pair, detect
an incompatible codec or chunk transition, design a restartable build without
embedding credentials, and refuse to infer browser support from a Python read.
Any future script must operate only on supplied metadata or temporary test
stores, never production repositories or datasets.
