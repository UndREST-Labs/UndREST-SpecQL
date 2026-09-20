<!-- version: 1.1.0 -->
# Current PR Contract

This contract constrains implementation scope for the active PR. Update
it when scope is explicitly amended. If a requested action falls outside
approved scope, stop and escalate before proceeding.

Use this contract to distinguish active PR constraints, completed PR
constraints, durable invariants, and intentional amendments. Completed
PR constraints are historical evidence unless they are explicitly
promoted to durable invariants.

## Goal
Add bounded, deterministic API-family/resource-hierarchy and version-lineage metadata to grouped and sharded API inventory exports so APISpy can correlate sibling operations and API-version relationships without receiving prose, examples, raw schemas, or live observations.

## Contract status
active

## Non-goals
- Do not change CodeQL queries, analyser behaviour, workflows, dependencies, or source configuration.
- Do not regenerate or commit inventory, database, SARIF, shard, or packaged outputs.
- Do not change flat inventory schema 2.1.0.
- Do not resolve remote references, retain examples/descriptions, infer vulnerabilities, or add model/network functionality.

## Carry-forward rules
The following constraints from this PR are promoted to durable invariants and must persist into all future PRs:
- Always pin CodeQL CLI to 2.20.1 or 2.20.2 (JSON-only database compatibility).
- Do not commit `database/`, `results/`, `azure-rest-api-specs/`, or generated inventory exports.
- `requirements.txt` lists only runtime-required Python packages; pytest is documented separately.
- `carl doctor` must remain healthy after any changes to `.github/carl/` artefacts.

## Approved scope
- Add compact API-family/resource-hierarchy metadata to grouped/sharded route entries derived from normalised route template segments, provider namespace, and bounded resource-type paths.
- Add compact version-lineage metadata to grouped/sharded route entries derived from deterministic ordering of version keys and preview/stable classification when derivable from version strings.
- Preserve the existing bounded auth, parameter-name, request-schema, and response-schema summaries on grouped/sharded version entries.
- Bump grouped/sharded schema from additive 3.1.0 to additive 3.2.0 while preserving existing fields and route keys.
- Add focused exporter compatibility, hierarchy, lineage, truncation, omission, and flat-schema tests.
- Update schema documentation, consumer guidance, export guide, README version references if present, and durable cARL architecture notes.

## Intentional amendments
- Supersedes the completed generated-artefact-boundary hardening scope.
- User-approved continuation of the UndREST research-platform implementation permits this bounded exporter change.

## Forbidden scope
- Modifying CodeQL queries, analyser/runtime entry points, workflows, source configs, or dependencies.
- Regenerating or editing generated database, SARIF, JSON inventory, shard, or packaged artefacts.
- Breaking flat 2.1.0 or existing grouped/sharded route and version fields.
- Exporting raw examples, descriptions, defaults, credentials, or unrestricted schema content.
- Adding speculative vulnerability labels or API-specific hard-coding.

## Architectural constraints
- Static API knowledge remains owned by SpecQL; observations and findings remain owned by APISpy.
- Metadata extraction must be deterministic, bounded, provider-neutral, and derived only from OpenAPI/Swagger structure.
- Existing 3.1.0 consumers must continue to function by ignoring additive 3.2.0 fields.
- Local `$ref` cycles and malformed schemas must fail safely without aborting export.
- Export pipeline output remains deterministic for identical input.

## Security constraints
- No secrets, tokens, credentials, examples, or sensitive default values may be copied into metadata.
- Security metadata describes documented mechanisms only; it must not imply effective authorization or vulnerability status.
- Fingerprints must represent schema structure, not raw payload content.
- No external network or model dependencies may be introduced.

## Files expected to change
- `.github/carl/current-pr-contract.md`
- `.github/carl/memory.md`
- `scripts/export/export_api_inventory.py`
- `tests/test_api_inventory_export.py`
- `tests/test_api_inventory_normalization.py`
- `docs/inventory/API_INDEX_SCHEMA.md`
- `docs/inventory/CONSUMER_GUIDE.md`
- `docs/inventory/EXPORT_PIPELINE.md`
- `README.md` if it states grouped/sharded schema version

## Tests / validation
- `python3 -m pytest tests/test_api_inventory_export.py tests/test_api_inventory_normalization.py -v`
- Confirm flat output remains schema 2.1.0 and does not contain new grouped-only metadata.
- Confirm grouped and sharded output use schema 3.2.0 with optional bounded metadata.
- Confirm malformed/cyclic local references do not fail export.
- Confirm API-family/resource-hierarchy metadata, version-lineage ordering, preview/stable classification, truncation markers, omission when empty, and flat-output stability.
- Confirm no generated artefacts appear in git status.
- Run `python3 -m compileall` on changed Python files, `git diff --check`, and `carl doctor` when available.

## Stop conditions
- Metadata requires remote reference fetching or new dependencies.
- Existing route identity, matching keys, or flat output would need a breaking change.
- Generated inventory, database, SARIF, or shard artefacts appear in git status.
- A secret or raw example/default value would be retained.

## Escalation triggers
- Any need to modify workflows, CodeQL queries, analyser logic, dependencies, or source configs.
- Any proposed metadata whose semantics cannot be derived deterministically from the specification.
- Any need for a breaking grouped/sharded schema version.

## Context reset notes
This contract covers the additive SpecQL 3.2.0 sibling-correlation metadata phase for SpecQL exports only. APISpy consumption is out of scope for this phase.
