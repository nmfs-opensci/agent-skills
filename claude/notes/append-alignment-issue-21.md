# Append alignment (issue #21)

The CEFI audit found that `vz.to_icechunk(append_dim=...)` silently misplaces data when
a file's length along the append axis is not a multiple of its chunk (CEFI NEP daily:
365/366 days per file, time chunk 100). Evidence is in `noaa-nwfsc/cefi-icechunks`:
`audit/report.md` P2 and `audit/repro/02a`, `02b`. Eli's public store
`eeholmes/cefi/nepacific-icechunk` is affected (cefi-icechunks #8).

## Decisions (Eli, 2026-09-24)

- **Recommend a guard, not a workaround.** Before any append or region write, refuse
  unless the existing length and every piece except the last are whole multiples of the
  chunk along that axis. When sources fail it, the honest options are: leave those
  variables out and say so (what Earthmover did for CEFI), keep one array per file,
  materialize, or ask the provider for a chunk that divides every file's length (for
  daily files with 365 and 366 days, only chunk 1 does that).
- **Variable-length (rectilinear) chunks are "watch", not an option.** zarr-python and
  Icechunk 2.x support rectilinear grids, but VirtualiZarr does not yet (#12, PR #954
  open). More fundamentally, zarr-extensions#74 (opened 2026-09-18, open) shows the spec
  cannot express a *padded* edge chunk in the middle of an array: the chunk's size is
  both its decoded extent and the next chunk's offset. HDF5 pads edge chunks to full size,
  and CEFI's are zlib-compressed, so there is no prefix trick. Spec maintainers lean
  toward a separate concatenation or array-domain convention instead.
- **Placement in the skill:** a short known trap in `SKILL.md`; the guard in
  `references/current-workflow.md` step 9 and `references/smoke-test-notebook.md` step 8;
  a row in `references/known-issues.md`; a check in `references/validation.md` that
  compares source values on both sides of every file boundary (how the audit caught it).
- **Report upstream** to VirtualiZarr. Eli posts it; the draft and repro are in
  `~/tmp/claude-1000/` (see the handoff for the command). Cite the issue in the skill.

## Verified by running (2026-09-24)

Clean venv (`/srv/conda/bin/python3.12 -m venv`), VirtualiZarr 2.7.3, Icechunk 2.2.2,
zarr 3.4.0, xarray 2026.7.0. Two synthetic local NetCDF files, 365 steps each, HDF5
chunk 100, values equal to their intended position:

- `xr.concat` refuses ("Cannot concatenate arrays with partial chunks ...").
- append accepts; 430 of 730 values wrong. The second file starts at index 300; indices
  665–699 expose HDF5 fill padding; 700–729 have no chunk.
- `region={"time": slice(365, 730)}` refuses ("not aligned to whole chunks of size 100").
  So the HYCOM skeleton-plus-`region=` pattern is protected by VirtualiZarr itself.

## Why append misbehaves (code, v2.7.3 = `main` on 2026-09-24)

`virtualizarr/writers/icechunk.py`: the append branch of
`write_virtual_variable_to_icechunk` offsets new chunks by `num_chunks()` =
`shape[axis] // chunks[axis]`. `check_compatible_arrays` checks dtype, codecs, chunk
shape and ndim, not length alignment. The `region=` branch does check
`start % chunk_size`.
