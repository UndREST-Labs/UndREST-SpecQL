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
Add a safe lightweight test command and CI workflow for SpecQL tests that do not
require CodeQL, `azure-rest-api-specs`, or a built database.

## Contract status
active

## Non-goals
- Do not refactor product code or change query logic.
- Do not run or add CodeQL database build steps.
- Do not touch `queries/`, generated inventory output, `database/`, `results/`, or `azure-rest-api-specs/`.
- Do not add Python packages to `requirements.txt` unless explicitly required.

## Carry-forward rules
The following constraints from this PR are promoted to durable invariants and must persist into all future PRs:
- Always pin CodeQL CLI to 2.20.1 or 2.20.2 (JSON-only database compatibility).
- Do not commit `database/`, `results/`, `azure-rest-api-specs/`, or generated inventory JSON files.
- `requirements.txt` lists only runtime-required Python packages; pytest is documented separately.
- `carl doctor` must remain healthy after any changes to `.github/carl/` artefacts.

## Approved scope
- Add/update lightweight test command documentation.
- Add a dedicated GitHub Actions workflow for lightweight pytest checks only.
- Update cARL durable docs/memory only if canonical validation or workflow truth changes.

## Intentional amendments
- Supersedes the previous cARL-install-only scope in this file.
- Allows `.github/workflows/` updates for the lightweight-test workflow only.

## Forbidden scope
- Modifying product behaviour in `SpeQL.py`, `analyze.py`, `refresh_database.py`, `run-queries.sh`, or export logic.
- Modifying CodeQL queries under `queries/`.
- Modifying source configs under `config/sources/`.
- Adding/removing/changing Python packages in `requirements.txt` without explicit approval.
- Touching generated artefact directories (`database/`, `results/`, `inventory/*.json`, `azure-rest-api-specs/`).

## Architectural constraints
- SpeQL architecture and product behaviour must remain identical before and after this PR.
- Lightweight tests must remain independent from CodeQL and database/spec clone prerequisites.
- `requirements.txt` remains runtime-focused; pytest is installed in CI as a test tool.

## Security constraints
- No secrets, tokens, or credentials may be committed.
- No new external network dependencies are introduced.
- Workflow permissions must stay least-privilege.

## Files expected to change
- `.github/carl/current-pr-contract.md` — amended scope for this PR
- `README.md` and/or `CONTRIBUTING.md` — lightweight test entry-point documentation
- `.github/workflows/lightweight-tests.yml` — new CI workflow for lightweight pytest suite
- `.github/carl/memory.md` — workflow inventory/canonical command reconciliation (if needed)

## Tests / validation
- Install runtime deps: `pip3 install -r requirements.txt`
- Install test tool explicitly: `pip3 install pytest`
- Run lightweight tests: `python3 -m pytest tests/test_api_inventory_export.py tests/test_api_inventory_normalization.py -v`
- Confirm no generated artefact churn in `git status`

## Stop conditions
- Any change that alters product script or CodeQL query behaviour.
- Any generated database, inventory, or results file appearing in git status.
- Any secret detected in changed files.

## Escalation triggers
- If requested workflow scope expands beyond lightweight pytest tests.
- If changes require touching queries, generated artefacts, or dependency policy.

## Context reset notes
This contract covers adding a lightweight test entry point and CI workflow only. Close/reset after merge.
