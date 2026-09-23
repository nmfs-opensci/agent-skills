# Lesson from the CEFI audit, not yet in the skill (2026-09-23)

Written by the session that audited the CEFI regional MOM6 NetCDFs for
`noaa-nwfsc/cefi-icechunks` (issue #5, PR #7). The evidence is in `~/cefi-icechunks`:
- `audit/report.md` P2 (the full write-up)
- `audit/repro/02a_per_year_time_chunks.py` (concat refused)
- `audit/repro/02b_append_misplaces_data.py` (append misplaces data)
- `claude/notes/source-file-problems.md`

It's a candidate for a Learn pass: check it against the versions current then before
writing it in. Eli wants this taken to the skill as its own task, and isn't sure yet what
the recommended pattern should be.

## The finding: appending misaligned files silently misplaces data

- **Setup.** NEP daily 4-D variables come as one NetCDF per year, with HDF5 time chunk 100
  (365 or 366 days per file, so every year ends in a partial chunk of 65 or 66). HDF5
  stores that edge chunk at full size, padded with the fill value.
- **Concatenation refuses.** `xr.concat` of the virtual datasets raises *"Cannot
  concatenate arrays with partial chunks because only regular chunk grids are currently
  supported ... array length 365 ... not evenly divisible by chunk length 100."*
  Correct behavior.
- **Append accepts, and gets it wrong.** Writing year 1 and then each later year with
  `vds.vz.to_icechunk(store, append_dim="time")` (VirtualiZarr 2.7.3, Icechunk 2.2.2)
  raises nothing.
  - **Where each year lands:** it's written starting at chunk slot
    `floor(existing length / chunk)`, so 1994's first chunk lands at index 300, not 365.
    It overwrites the last 65 days of 1993; 1994 then sits 65 days early; the tail is
    empty.
  - **The time coordinate, written as a loaded variable, is correct.** So the store opens
    cleanly, with every value under the wrong date.
  - **Over 1993–2024:**
    - years labelled 0–96 days early
    - 717 days overwritten
    - 695 rows of padding (the fill value) exposed under ordinary dates
  - **Symptom:** the only one is `ds.chunks` raising "inconsistent chunks along dimension
    time".
- **Found in a real, public store.** Eli's Source Coop store
  `eeholmes/cefi/nepacific-icechunk` (`daily/raw/main`, `daily/regrid/main`) was built
  this way; issue #8 in `noaa-nwfsc/cefi-icechunks` tracks it. Earthmover's production
  build (Arraylake `NOAA-PMEL/cefi-nep-hindcast-daily`) avoided it only by leaving the
  per-year variables out.

## Where the skill touches this

- `references/current-workflow.md` (around line 43) and
  `references/smoke-test-notebook.md` (around line 41) recommend appending files or
  batches, with no check that each file's length along the append dimension is a
  multiple of its chunk.
- `references/known-issues.md` discusses append only for the one-element coordinate
  chunk problem.
- The HYCOM inbound note's "skeleton plus `region=` writes" pattern has the same exposure.
  A region write can only place whole chunks, so the same alignment rule applies.
  Unverified.

## Open questions for the Learn pass (Eli is undecided)

- **What to recommend:**
  - concat (which refuses correctly, but then the variable can't be built at all)
  - a pre-write guard that refuses append/region writes unless the existing length and
    each piece's length are multiples of the chunk (except the last)
  - variable-length (rectilinear) chunk grids, if Zarr and Icechunk support them for
    virtual refs by then
  - telling data providers to rechunk (time chunk 1, or fixed-length files)
- **Upstream:** should this be reported to VirtualiZarr? Append should probably run the
  same regular-chunk-grid check as concat. Not reported yet.
- **Placement in the skill:** "Known traps" in `SKILL.md`, a validation step (compare a
  few grid points with the source across file boundaries — that's how it was caught), or
  both.
