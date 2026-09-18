# Expanding the skill past NetCDF/HDF5 — where the material is

Eli decided on 2026-09-18: **not now, but later.** The skill's scope stays
NetCDF/HDF5 and its `description` still draws that line. This note is the
starting dossier for the session that does the work, so it does not begin by
re-reading someone else's repository.

## What "widening" would actually mean

The skill is organized by *workflow mode* and by *source/destination provider*.
Format is a third axis it does not have. Adding one means deciding where it
lives before writing any content:

- **A parser table in one new reference** (`references/format-parsers.md`), with
  the workflow unchanged. Cheapest, and probably right: the mode structure and
  every non-negotiable already apply to GRIB or TIFF without modification.
- **Per-format reference files**, mirroring earth-mover. More room, more upkeep,
  and their own repo shows the failure mode — see the caveat below.
- Either way, the `description` in `SKILL.md` needs widening too, or the skill
  will not trigger for a user holding GRIB. That is the real gate, not the
  content.

## The upstream source

Earthmover's own skill, `icechunk-datacube-ingestion`:
<https://github.com/earth-mover/agent-skills>, directory
`icechunk-datacube-ingestion/formats/`. It is the vendor's guidance, so it will
track Icechunk releases better than anything we write.

**Read it with your eyes open.** As of 2026-09-18 its `SKILL.md` links four
format files that do not exist (`NETCDF3.md`, `KERCHUNK.md`, `PARQUET.md`,
`UNSUPPORTED.md`), `formats/HDF5.md` is a zero-byte file linked from the
netCDF4 path — the most common case of all — and `formats/GRIB.md` ends
mid-sentence on the word "Opening". Do not assume a linked file has content.
That repo is also the argument for adding an internal-link check to our
`validate_skills.rb`, which today validates frontmatter and scans for secrets
but never follows a link.

## GRIB

Everything goes through **`gribberish`** (`mpiannucci/gribberish`), not cfgrib.

- Usage docs:
  <https://github.com/mpiannucci/gribberish/blob/main/python/README.md#usage>
- Virtual: `pip install "gribberish[virtualizarr]"`, then
  `from gribberish.virtualizarr import GribberishParser` passed as `parser=` to
  the usual `open_virtual_dataset(url=..., registry=...)`.
- Native, for comparison: `pip install "gribberish[xarray]"`, then
  `xr.open_datatree(url, engine="gribberish")`.
- **GRIB index files** (`.index` suffix) — pass `use_index=True` to the
  `GribberishParser` constructor for a significant parsing speedup. Worth
  checking whether the archive ships them before scaling up.
- GRIB's internal structure is messy enough that the result usually wants
  deliberate reorganization into a clean datacube rather than a literal
  translation.

**Version drift to check first.** Earthmover documents "v1.1.0 or later";
PyPI's current `gribberish` is **1.7.0** (`requires_python >=3.12`, checked
2026-09-18). Six minor versions is plenty of room for the parser API to have
moved, and their example is internally inconsistent already — it imports
`open_virtual_dataset` and then calls `open_virtual_datatree`. Verify against
gribberish's own docs before copying anything.

**GRIB will drag FMRC in with it.** Most GRIB people actually have is forecast
output, one run per file with a lead-time axis, which is exactly the shape
`icechunk-datacube-ingestion/FMRC.md` handles. The two decisions are separable
on paper and probably not in practice.

## TIFF / GeoTIFF / COG

- Virtual: the **`virtual-tiff`** package (PyPI `virtual-tiff`, currently
  **0.5.0**, `requires_python >=3.11`, released 2026-04-29). Import
  `from virtual_tiff import VirtualTIFF` and pass `parser=VirtualTIFF(ifd=0)`.
- `ifd` selects the image file directory. `0` is the full-resolution image; a
  COG's overviews are the later IFDs. That parameter is the whole multiscale
  story for TIFF, and it connects directly to the overview argument already in
  `references/browser-access.md` under "Chunk layout is the next obstacle".
- Native, for comparison: rasterio through xarray.

## Existing Zarr stores

- Virtual: `from virtualizarr.parsers import ZarrParser` — in VirtualiZarr
  itself, no extra package. Useful for referencing a Zarr store without copying
  it.
- Past ~50 million chunks, split the virtual dataset across several commits:
  <https://virtualizarr.readthedocs.io/en/stable/scaling.html#splitting-a-single-large-virtual-dataset-across-commits>.
  That threshold is already cited in `references/performance-tuning.md`.
- Native: `xr.open_zarr`.

## Formats with no parser at all

Earthmover's `UNSUPPORTED-FILE-FORMAT.md` has the right method, and it is worth
stealing even without widening scope: first check whether the format is secretly
a supported one wearing a different name — OME-Zarr *is* Zarr, `h5ad` *is* HDF5
— and only then search for a third-party reader (a custom xarray backend for
native, a custom VirtualiZarr parser for virtual). If neither exists, say so and
suggest an upstream issue rather than inventing a path.

## What each format needs on our side before it is guidance

The skill's own bar, from `references/learn-and-evolve.md`: one success is an
anecdote. So per format, expect to need

1. a real dataset and a **smoke test that actually runs** — none of the above is
   verified here, and the skill says to say so;
2. rows in `references/version-matrix.md` for the new packages, with the Python
   floor (gribberish is >=3.12, virtual-tiff >=3.11, so the stack floor stays
   3.12);
3. whatever `references/known-issues.md` entries the smoke test earns;
4. an eval scenario in `evals/virtual-icechunk/scenarios.md` plus its rubric
   entry, since `AGENTS.md` requires evaluations to be updated when behavior
   changes;
5. a decision on whether the source-side rules still hold — in particular
   whether `url_prefix`, per-prefix authorization and the two-host CORS model
   behave identically for a TIFF or GRIB source. There is no reason to expect
   otherwise, and no evidence either.

## Open questions for that session

- One parser table, or one file per format?
- Widen `SKILL.md`'s `description`, or keep the skill NetCDF/HDF5 and let the
  table only handle routing when a user turns up with something else?
- Is FMRC done at the same time as GRIB, or before it, or separately?
- Does `validate_skills.rb` grow an internal-link check first, given that adding
  cross-referenced files is exactly the change that would benefit?
