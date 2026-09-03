# Research and plan

Read this before writing any code for a new dataset. The goal of this mode is a
written plan and a list of decisions, not an implementation.

## 1. Separate the two configurations

Virtual Icechunk always involves two independent systems. Keep them apart in
your notes, your code, and your credentials.

| | Source | Destination |
|---|---|---|
| What it is | Where the NetCDF/HDF5 bytes stay | Where the Icechunk metadata repository is written |
| Decides | Discovery, authentication, parser, the URLs embedded in virtual references | Storage class, write credentials, public read URL |
| Example | `s3://ob-cumulus-prod-public/...` (NASA OBDAAC) | `https://data.source.coop/<account>/<prefix>` |

A reader of the finished store needs credentials for **both**, and they are
usually different credentials. Never let one imply the other.

## 2. Inspect the source service

- How are files listed? Provider API (`earthaccess.search_data`), provider CLI
  (`copernicusmarine get --create-file-list`), an S3 listing, or HTML directory
  scraping. See `source-patterns.md`.
- Does discovery need authentication even when reading does not, or the reverse?
- What URL scheme will be embedded in the references — `s3://`, `https://`, or a
  rewritten host? Is that URL reachable by the intended consumers, or only from
  one cloud region?
- Are the URLs stable, or do they carry expiring query parameters? Signed URLs
  cannot be stored as virtual references.

## 3. Inspect representative files

Do not inspect only the first file. Inspect a file from **each side of every
suspected transition**: format changes, instrument changes, reprocessing
boundaries, grid changes, the earliest file, the most recent file.

For each file record:

- format (NetCDF3 vs NetCDF4/HDF5 — they need different parsers);
- dimensions, shape, and the intended combine dimension;
- coordinate variables, their values, dtype, and whether they are correct;
- data variables and their dtypes;
- native chunk shape and codecs (including endianness);
- fill/missing-value encoding and attributes;
- how many steps of the combine dimension are in one file;
- whether the variables are split across separate files. If they are, they
  merge into one dataset rather than concatenating along the combine
  dimension — prefer one store with many variables over many stores.

Confirm byte-range reads work before anything else. For HTTPS sources, a range
request must return HTTP 206 and the expected leading bytes (the format's magic
number). If range requests are not honored, virtualization is impossible.

## 4. Partition into compatible groups

A single virtual Zarr array cannot span files whose encodings differ, because no
data is rewritten. Files may be combined only when they agree on:

dimensions · shape (apart from the combine dimension) · chunk grid · dtype ·
codecs and endianness · the meaningful variable schema.

Where they disagree, you must choose a partition. Prefer, in order:

1. **One repository, one group, many variables.** Best consumer experience.
2. **One repository, several groups**, when encodings are incompatible but the
   groups clearly belong to the same product and a reader would concatenate
   them.
3. **Separate repositories**, when the products are independent.

Record why each boundary exists so the project README can explain it and a later
audit does not "fix" a deliberate split. See `validation.md` for the checks that
prove a partition is really homogeneous.

## 5. Look for known problems

Real archives contain broken files. Check explicitly for:

- coordinate variables that are all zero, all NaN, or missing;
- attributes that cannot be serialized as JSON (bare `NaN`, `Inf`);
- time values that must be derived from the filename because the file is wrong;
- off-cadence or duplicated time steps — model the real cadence (for example an
  8-day product that resets each year) before calling a gap an error;
- one-time-step-per-file products, which produce one-element chunks and very
  slow metadata reads unless the loaded coordinate is chunked deliberately.

Every repair is dataset-specific. Write down what you changed, why, and which
source files you excluded. See `known-issues.md`.

## 6. Find the closest existing examples

Consult all four of these and combine them; do not clone whichever is newest:

1. the newest applicable **general** pattern;
2. the closest **source-specific** pattern (same provider or same access style);
3. the closest **destination-specific** pattern (same object store);
4. **current official documentation** for the installed versions.

Reference implementations, newest first — each is a snapshot of practice at its
date, not a standard:

- NOAA CoastWatch OHC — <https://github.com/fish-pace/icechunks>
- Copernicus GlobColour — <https://github.com/fish-pace/globcolour-Icechunks>
- NASA PACE OCI — <https://github.com/fish-pace/pace-icechunks>
- Annotated outline — `docs/example-virtual-icechunk-pipeline.ipynb` in this
  repository.

## 7. Record versions

Note the installed versions of icechunk, virtualizarr, xarray, zarr, obstore,
and any provider client, plus the Python version. These packages move fast and
carry compatibility floors. See `version-matrix.md`.

## 8. Deliverable

The output of this mode is a short written plan covering: source access,
destination, parser choice, discovery method, proposed groups and why, known
bad files and the proposed handling, the loaded-versus-virtual variable list,
uncertainties, and the questions that need a human decision. Get that reviewed
before writing the smoke test.
