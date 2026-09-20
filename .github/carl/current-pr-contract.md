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
Add deterministic, offline-capable Microsoft Graph OpenAPI ingestion from the authoritative `microsoftgraph/msgraph-metadata` repository, pinned by commit SHA, and produce an APISpy-compatible grouped/sharded export without committing generated artifacts.

## Contract status
active

## Non-goals
- Do not change CodeQL queries or analyser behaviour.
- Do not alter workflow schedules, permissions beyond what publication already requires, or retention periods.
- Do not commit inventory, database, SARIF, shard, packaged outputs, or the cloned Graph source repository.
- Do not change flat inventory schema 2.1.0 or grouped/sharded schema 3.2.0.
- Do not resolve remote references, retain examples/descriptions, infer vulnerabilities, or add model/runtime-network functionality.
- Do not schedule automatic Graph publication or modify APISpy generated data in this SpecQL phase.

## Carry-forward rules
The following constraints from this PR are promoted to durable invariants and must persist into all future PRs:
- Always pin CodeQL CLI to 2.20.1 or 2.20.2 (JSON-only database compatibility).
- Do not commit `database/`, `results/`, `azure-rest-api-specs/`, or generated inventory exports.
- `requirements.txt` lists only runtime-required Python packages; pytest is documented separately.
- `carl doctor` must remain healthy after any changes to `.github/carl/` artefacts.

## Approved scope
- Register `microsoftgraph/msgraph-metadata` as an authoritative source pinned to commit `b8cbef92f6959dca8150bf3edcc650863765e529`.
- Extend source refresh configuration with optional exact-commit checkout support.
- Add safe YAML ingestion using `yaml.safe_load`; PyYAML is justified because the authoritative 44–70 MB OpenAPI documents are YAML and the standard library has no YAML parser.
- Auto-select a bounded `microsoft-graph` export profile from the authoritative source repository identifier, while retaining an explicit CLI override.
- Include OpenAPI server base paths (`/v1.0` and `/beta`) in exported route templates, classify the exact Graph host as data plane, and group Graph operations into one `Microsoft.Graph` shard compatible with APISpy's fail-closed host routing.
- Preserve OData parameter names, local-reference-only schema summarisation, deterministic ordering, existing schemas, and all Azure behaviour.
- Add focused fixtures/tests, source and export documentation, and durable cARL notes.
- Generate a local ignored candidate export for validation; do not commit it.
- Compute a semantic content hash that excludes volatile `generated_at` metadata.
- Restore the last changed-export hash from a tiny Actions cache and upload export artifacts only when semantic content changed.
- Serialize per-source workflow runs to prevent duplicate publication races; only sources explicitly configured for APISpy publication may replace the stable release asset and dispatch updates.

## Intentional amendments
- Supersedes the completed SpecQL 3.2.0 family/lineage phase.
- User approval to “do it” explicitly authorises this bounded source-config, exporter, dependency, documentation, and local candidate-generation work.
- APISpy bundling remains a subsequent separately governed phase after the candidate export is validated.

## Forbidden scope
- Modifying CodeQL queries, analyser behaviour, workflow schedules, or generated committed artifacts.
- Committing the cloned Graph metadata repository or generated inventory output.
- Breaking flat 2.1.0 or existing grouped/sharded route and version fields.
- Exporting raw examples, descriptions, defaults, credentials, or unrestricted schema content.
- Fetching remote `$ref` content or deriving routes from anything except the pinned authoritative OpenAPI documents.
- Adding speculative vulnerability labels or Graph endpoint metadata not present in the source.

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
- `.github/carl/plans/microsoft-graph-authoritative-export.md`
- `.gitignore`
- `requirements.txt`
- `config/sources/microsoft-graph.json`
- `config/sources/azure.json`
- `refresh_database.py`
- `refresh-database.sh`
- `scripts/export/export_api_inventory.py`
- `scripts/export/hash_inventory.py`
- `scripts/export/normalize_api_inventory.py`
- `.github/workflows/daily-api-index-export.yml`
- `.github/workflows/daily-api-index-export-sharded.yml`
- `tests/test_api_inventory_export.py`
- `tests/test_api_inventory_normalization.py`
- `tests/test_refresh_database.py`
- `tests/test_inventory_hash.py`
- `docs/ADDING_API_SOURCES.md`
- `docs/inventory/API_INDEX_SCHEMA.md`
- `docs/inventory/EXPORT_PIPELINE.md`
- `README.md`

## Tests / validation
- `python3 -m pytest tests/test_api_inventory_export.py tests/test_api_inventory_normalization.py tests/test_refresh_database.py tests/test_inventory_hash.py -v`
- `python3 -m pytest -q`
- `bash -n refresh-database.sh`
- Parse both modified workflow YAML files.
- Confirm identical semantic exports with different timestamps hash equally and changed routes hash differently.
- Confirm artifact upload, shard release publication, and APISpy dispatch are all gated by the content-change output.
- Confirm JSON/Azure behavior remains unchanged and schemas remain 2.1.0/3.2.0.
- Confirm YAML uses safe loading and fails clearly when PyYAML is unavailable.
- Confirm Graph host, `/v1.0` and `/beta` prefixes, preview classification, OData parameters, fixed provider namespace, deterministic shard name, and pinned provenance.
- Generate a local ignored Graph candidate and inspect route/provider/version counts without committing artifacts.
- Run `python3 -m compileall` on changed Python files, `git diff --check`, protected-path checks, and `carl doctor`.

## Stop conditions
- The pinned authoritative source is unavailable or its license/provenance cannot be verified.
- Existing Azure route identity, matching keys, or schemas regress.
- YAML parsing requires unsafe loading or remote-reference resolution.
- Generated inventory, database, source clone, SARIF, or shard artifacts become tracked.
- A secret or raw example/default value would be retained.

## Escalation triggers
- Any need to modify workflows, CodeQL queries, or analyser logic.
- Any need for a breaking schema version or multiple Graph shards unsupported by APISpy routing.
- Any source other than the pinned official Microsoft Graph metadata repository is required.

## Context reset notes
This contract covers authoritative Microsoft Graph source acquisition and SpecQL export only. APISpy generated-pack integration begins only after this phase produces and validates a local candidate.
