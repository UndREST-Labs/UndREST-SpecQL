<!-- version: 1.2.0 -->
# Durable Architectural Truth Cache

This cache stores durable project truths that should persist beyond a
single task. Update it only when a stable fact, decision, invariant, or
unresolved question should carry forward.

## Project purpose
UndREST-SpecQL (SpeQL) is an API Spec Query Engine that scans Azure REST API
specifications for security vulnerabilities using CodeQL queries and a built-in
Python analyser. It is the engine that feeds UndREST-APISpy by exporting a
structured JSON index of every Azure REST API operation, which APISpy uses for
real-time request classification in the browser extension.

## Non-goals
- Do not refactor product code or change query behaviour.
- Do not rebuild the CodeQL database or regenerate inventory/shard artefacts.
- Do not vendor external dependencies (azure-rest-api-specs is cloned by refresh scripts, never committed).
- Do not add Python dependencies beyond requirements.txt without explicit justification.

## Architecture summary

SpeQL is a Python + CodeQL analysis pipeline targeting Azure REST API JSON specs (OpenAPI/Swagger 2.0 and OpenAPI 3.x).

### Entry points and scripts

| Script | Purpose |
|---|---|
| `SpeQL.py` | Interactive CLI menu (pyfiglet ASCII logo, all-in-one navigation) |
| `analyze.py` | Python security analyser — no CodeQL required; detects Logic App triggers, Key Vault misconfigs, missing access control, hardcoded credentials |
| `refresh_database.py` / `refresh-database.sh` | Clone azure-rest-api-specs and build CodeQL database |
| `run-queries.sh` | Execute CodeQL queries against the built database; includes smart memory management |
| `scripts/export/export_api_inventory.py` | Walk spec corpus, produce structured JSON index for APISpy |
| `scripts/export/normalize_api_inventory.py` | Normalisation helpers used by the export pipeline |

### CodeQL queries (queries/azure-security/)

8 CodeQL queries detecting:
- `SasUriInResponse.ql` — SAS URIs in API example responses (SilentReaper class)
- `ExposedSasTokens.ql` — pre-authenticated SAS tokens in example payloads
- `ProxyAndDynamicInvocation.ql` — bridge endpoints enabling cross-service access bypass
- `MissingLogicAppSecureData.ql` — Logic App workflows without secure data runtime config
- `HardcodedSecretsInArm.ql` — ARM securestring params with plaintext defaults
- `SensitiveDataInGetResponse.ql` — GET responses returning unprotected credential properties
- `ControlPlaneBypass.ql` — management ops exposed on data-plane paths
- `Base64EncodedSecrets.ql` — obfuscated secrets encoded as base64

### Key directories

| Directory | Status | Notes |
|---|---|---|
| `database/` | Generated; not committed | Built by refresh scripts from azure-rest-api-specs |
| `results/` | Generated; gitignored | SARIF output from CodeQL queries |
| `inventory/` | Generated; only `.gitkeep` tracked | Exported API index artefacts (`.json`, `.min.json`, `shards/`, and packaged `.zip` outputs are gitignored) |
| `azure-rest-api-specs/` | Cloned externally; gitignored | Source spec corpus managed by refresh scripts |
| `queries/azure-security/` | Committed | CodeQL query pack with `qlpack.yml` |
| `config/sources/` | Committed | One JSON per spec source (currently `azure.json`) |
| `scripts/export/` | Committed | Export pipeline Python modules |
| `scripts/sarif-analysis/` | Committed | SARIF threat hunting shell scripts |
| `tests/` | Committed | Unit tests for export pipeline (120 tests; run without CodeQL or DB) |

### Multi-source architecture

Scripts accept `--source-config config/sources/<platform>.json` to support any OpenAPI/Swagger spec corpus.
Adding a new source requires only a source config JSON and optionally a platform-specific query directory.

### Export pipeline

`scripts/export/export_api_inventory.py` walks the spec corpus and produces:
- `api-index.json` — flat index of every operation
- `api-index-grouped.json` — nested by provider/host/route (with `--grouped`)
- `shards/<provider>.json` — per-provider shards (with `--sharded`)
- Minified variants (`*.min.json`) with `--minified`
- Packaged sharded export ZIPs for release publication

Published to UndREST-APISpy via GitHub Releases.

### GitHub Actions workflows

| Workflow | Schedule | Purpose |
|---|---|---|
| `lightweight-tests.yml` | PRs, pushes to `main`, manual | Install runtime deps + pytest, run lightweight export/normalization unit tests (no CodeQL/DB/spec clone) |
| `speql-security-scan.yml` | Daily 06:00 UTC | Clone specs, build DB, run CodeQL queries, upload SARIF |
| `daily-api-index-export.yml` | Daily 04:00 UTC | Clone specs, export flat + grouped + sharded JSON index |
| `daily-api-index-export-sharded.yml` | Daily | Sharded export variant |

## CodeQL compatibility constraint

**Use CodeQL CLI 2.20.1 or 2.20.2.** CodeQL 2.23.x+ has a known compatibility
issue with JSON-only databases (the type of database SpeQL builds from OpenAPI
JSON specs). This is a hard version pin, not a preference.

## Python dependencies

`requirements.txt` currently lists only `pyfiglet>=0.8.0` (for the ASCII art logo).

Hidden runtime dependencies not in requirements.txt:
- `pytest` — test runner; installed separately by CI workflows and docs
- `json`, `pathlib`, `sys`, `subprocess` — stdlib only; no additional packages needed for core analysis

Do not add packages to requirements.txt without justification. If a new script
requires a package, document it explicitly rather than silently adding.

## Canonical validation commands

- Run lightweight unit tests (no CodeQL/DB required): `python3 -m pytest tests/test_api_inventory_export.py tests/test_api_inventory_normalization.py -v`
- Install test runner: `pip3 install pytest`
- Install runtime deps: `pip3 install -r requirements.txt`
- Run Python analyser: `python3 analyze.py`
- Run interactive CLI: `python3 SpeQL.py`
- Run CodeQL queries (requires CodeQL CLI 2.20.1/2.20.2 and a built database): `./run-queries.sh`

**Tests that require CodeQL CLI, azure-rest-api-specs clone, or a built database should not be run in CI without confirming external dependencies are available.**

## Security invariants

- SAS URI patterns (`sig`, `se`, `sp`, `sv` query params) in response examples are treated as SilentReaper vulnerability indicators.
- The "SilentReaper" vulnerability class = API emits SAS URI in response + improper RBAC or inadequate control/data plane isolation.
- CodeQL queries operate on the read-only spec corpus; they do not execute API calls or touch live Azure resources.
- No Azure credentials or tokens are committed. Workflow auth is via GitHub Actions OIDC or Secrets.

## Ecosystem context

- **APISpy** (UndREST-Labs/UndREST-APISpy): browser extension that consumes SpeQL's exported JSON index for real-time request classification.
- **azure-rest-api-specs** (Azure/azure-rest-api-specs): upstream spec corpus; cloned by refresh scripts, never vendored.

## cARL installation

- Initial install: cARL CLI v0.4.2 used to run `carl init` on 2026-06-30 (37 artefacts).
- Runtime version: 1.0.0 from goldjg/cARL @ v1.0.0.
- `carl doctor` reports: healthy.
- **Ongoing install guidance:** Always install the latest CLI release from https://github.com/goldjg/cARL/releases/latest. See the [cARL QuickStart](https://github.com/goldjg/cARL#quickstart) for platform-specific instructions. Do not hardcode v0.4.2 for new installs.
- Then from repo root: `carl init`

## Core invariants

- Do not commit database/, results/, azure-rest-api-specs/, or generated inventory exports (JSON, shards, or packaged ZIPs).
- Always pin CodeQL CLI to 2.20.1 or 2.20.2 in setup, docs, and CI.
- requirements.txt lists only runtime-required Python packages; test tools (pytest) are documented separately.
- Export pipeline output is deterministic given the same spec corpus input.
- SpeQL product code changes must not alter the export pipeline's JSON schema without updating APISpy consumers.

## Known sharp edges

- CodeQL 2.23.x+ breaks JSON-only database builds — do not upgrade CodeQL without validating against the Azure spec corpus first.
- The export pipeline depends on `azure-rest-api-specs` being cloned at a predictable path; this path is not committed and must be set up before running exports.
- `pyfiglet` is listed as a hard dependency in requirements.txt but the CLI falls back gracefully if it is missing (ASCII art only).
- Tests under `tests/test_json_file_count_fix.sh` and `tests/test_memory_management.sh` are shell scripts that may require a local CodeQL database or specific OS tools; they are not part of the lightweight test suite.
- VHS demo GIFs under `demos/` and `tests/vhs/` are committed binaries for documentation purposes.

## Open questions

<!-- Populate with unresolved questions that should persist into future work. -->

## Last updated
2026-06-30 — cARL installation; initial SpecQL-specific memory populated.