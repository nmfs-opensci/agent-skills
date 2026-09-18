# Version matrix

The virtual-Icechunk stack moves fast and carries real compatibility floors.
Record the versions you actually ran, and re-check the current releases before
trusting any guidance in this skill.

## Checked releases

Verified against PyPI on 2026-09-03:

| Package | Version | Requires Python |
|---|---|---|
| icechunk | 2.2.0 | >=3.12 |
| virtualizarr | 2.7.3 | >=3.12 |
| xarray | 2026.7.0 | >=3.11 |
| zarr | 3.3.0 | >=3.12 |
| obstore | 0.11.1 | >=3.10 |
| obspec-utils | 0.9.0 | >=3.11 |
| earthaccess | 0.18.0 | >=3.12 |

The effective Python floor for the stack is 3.12.

## Official documentation to check

Pin the version in the URL so you are reading the docs for the release you have.

- Icechunk — storage, configuration and virtual credentials, virtual datasets,
  version control: <https://icechunk.io/en/v2.2.0/>
- VirtualiZarr — API and the V2 migration guide:
  <https://virtualizarr.readthedocs.io/en/stable/>
- Xarray — `open_zarr`, `to_zarr`, and the Zarr encoding specification:
  <https://docs.xarray.dev/en/v2026.07.0/>
- Zarr-Python — storage, performance, and the v3 migration guide:
  <https://zarr.readthedocs.io/en/stable/>
- VirtualiZarr's scaling guide, for large builds specifically:
  <https://virtualizarr.readthedocs.io/en/stable/scaling.html>
- Earthmover's own Agent Skill, `icechunk-datacube-ingestion`:
  <https://github.com/earth-mover/agent-skills>. Vendor guidance, so it tracks
  Icechunk releases. Wider than this skill in scope (materialized as well as
  virtual, organized by file format) and much thinner on two-host credentials,
  CORS, and read performance. Worth checking for parser and format questions;
  do not assume its Arraylake-centric access model transfers to another
  destination.

## Recording an environment

Every project gets a `requirements.txt` or `environment.yml` with the versions
that were actually tested, published next to the Icechunk store. Do not put
`pip install -U` in a production notebook: it makes the notebook unreproducible
and silently changes the API surface between runs.

## Version-sensitive behavior

Before calling any of these settled, confirm against the docs for your installed
version: VirtualiZarr's parser and registry requirements; Icechunk's virtual
container and credential API; Xarray's `chunks` semantics; Zarr v3 consolidated
metadata support; and any destination-specific workaround.
