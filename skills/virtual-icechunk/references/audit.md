# Audit mode

Use when asked to review, compare, or modernize an existing virtual Icechunk
workflow. **Produce an upgrade plan first. Do not rewrite the workflow as part
of the audit**, and never run the existing build against its production
repository to "check" it.

## Procedure

1. Read the repository's notebooks, scripts, README, issues, and commit
   messages. Issues usually explain choices better than the README does.
2. Record the workflow's source access, destination, parser, discovery method,
   groups, batching, validation, and recorded package versions.
3. Compare against `current-workflow.md`, `source-patterns.md`,
   `destination-patterns.md`, and `known-issues.md`.
4. Run the design table in `performance-tuning.md` over the workflow. Unchunked
   loaded coordinates, unsplit manifests, and needless group or repository
   splits are common in older builds and are among the few findings worth a
   rebuild on their own.
5. Check the claims that the repository makes about itself. A build that was
   never verified from the published URL, or a source list longer than the
   committed coordinate, is a finding.
6. Check the current official documentation for anything version-sensitive
   before calling an API obsolete.

## Classify every difference

| Category | Meaning | Default action |
|---|---|---|
| Should be updated | Diverges from current practice with no good reason | Propose the change |
| Intentionally source-specific | Required by the provider | Keep; document why |
| Intentionally destination-specific | Required by the object store | Keep; document why |
| Dataset-specific | A real repair or split for this data | Keep; make sure it is documented |
| Obsolete | Current APIs give contrary guidance | Propose the replacement, preserving the operational lesson |
| Uncertain | Needs an experiment or an owner decision | Raise it; do not guess |

An old API call and a bad idea are different findings. A workflow can be fully
obsolete in its API surface and still be the best available evidence about a
provider's behavior.

## Output

An upgrade plan containing: what the workflow does today; the classified
differences; what a rebuild would cost; what would be lost; the experiments
needed to resolve the uncertain items; and a recommendation on whether to
rebuild, patch, or leave alone. Ask before acting on it.

## Common findings in older workflows

- `.virtualize.to_icechunk` instead of `.vz.to_icechunk`.
- Implicit parser/storage guessing, which VirtualiZarr V2 no longer supports.
- `try: create except Exception: open`, hiding auth and network errors.
- An operator-entered `start_index` as the only resume mechanism.
- Unpinned `pip install -U` cells with no recorded tested environment.
- A private patched wheel kept for a destination bug that may be fixed.
- Source file counts that do not reconcile with the committed coordinate.
- A README that does not state the source-versus-destination credential split,
  or any region restriction.
- A store whose metadata is slow to open because its coordinates or manifests
  were never chunked or split.
