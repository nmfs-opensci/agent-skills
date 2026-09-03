# Known issues and outdated patterns

Every entry here was observed in a real workflow. The classification says how
far it generalizes.

## Failure modes

| Symptom | Cause | Response | Scope |
|---|---|---|---|
| Write fails partway through a multi-hour build | Destination token expired | Commit and reopen before expiry; check remaining lifetime before each batch | General concern, destination-specific refresh |
| `SessionError` / session refuses a write after a commit | An Icechunk session becomes read-only once committed | Always create a fresh writable session after `commit()` | General Icechunk rule |
| Read of a virtual array fails but metadata opens fine | The virtual chunk prefix was never authorized | Pass `authorize_virtual_chunk_access` for every prefix, including anonymous HTTP | General |
| Reader cannot find the virtual containers at all | Config was set but never persisted | Call `repo.save_config()` | General |
| References resolve to nothing | `url_prefix` does not match the reference URLs, or lacks a trailing `/` | Make the prefix an exact prefix ending in `/` | General |
| Metadata read takes minutes | One-element chunks on the combine coordinate, from appending one-time-step files | Set the loaded coordinate's chunking explicitly: `vds.vz.to_icechunk(session, encoding={"time": {"chunks": (len(vds.time),)}})`. This does not rechunk virtual science data | General |
| Commit fails serializing attributes | `NaN`/`Inf` in attributes cannot be JSON-encoded | Sanitize attributes and log what was removed | Dataset-specific |
| Coordinates are all zero or all NaN | Corrupt source files | Exclude the files or replace the grid from a trusted file — with owner confirmation — and record every omission | Dataset-specific |
| HTTP 403 from Python but the URL works in a browser | Server rejects the default Python User-Agent | Set a browser-like User-Agent for discovery and parser requests | Source-specific (CoastWatch); **not** a CORS finding |
| Point time series is far slower than expected | Native source chunks are large and contiguous; a point read fetches most of a field | Nothing metadata-only can fix this. Document the limitation, or materialize | General physics of virtual stores |
| Server returns HTTP 501 on an Icechunk operation | Destination lacks server-side copy | Retest on current Icechunk before adopting any patch | Historical, destination-specific |
| Root cause of a write failure is invisible | `try: Repository.create(...) except Exception: Repository.open(...)` swallows auth, network, and config errors | Handle only the "already exists" condition; let everything else raise | General |
| Store is published but unreadable | The validated destination and the published destination were different | Availability is unproven until a public read from the published URL succeeds | General |

## Outdated patterns

"Obsolete" means current official APIs give contrary guidance. The operational
lesson behind an obsolete call is often still valid.

| Old | Current |
|---|---|
| `.virtualize.to_icechunk` | `.vz.to_icechunk` (old name is a deprecated alias) |
| Implicit parser / storage guessing | Supply a parser and an `ObjectStoreRegistry` explicitly |
| Zarr-Python 2 `DirectoryStore`, `FSStore`, mutable mappings | `LocalStore`, `FsspecStore`, or the v3 async Store API |
| `zarr_version=` | `zarr_format=` |
| `_ARRAY_DIMENSIONS` as the dimension convention | Native `dimension_names` in Zarr v3; `_ARRAY_DIMENSIONS` is v2 |
| "Zarr v3 cannot use consolidated metadata" | It can, as an extension. Icechunk readers pass `consolidated=False`, which is correct here but is not a universal rule |
| Private patched Icechunk wheel for a destination workaround | Retest on the current release; do not carry a private patch |
| `pip install -U` at the top of a production notebook | Record a tested environment; the stack has real compatibility floors |
| Calling any HTTPS workaround "ERDDAP" or "CORS" | Neither has a validated example. Do not label unrelated behavior as either |

## Xarray read semantics worth getting right

`chunks={}` gives Dask arrays with the backend's preferred chunks — use it
before concatenating groups, so several GB do not materialize eagerly.
`chunks=None` gives no Dask, and values become NumPy arrays when accessed.
