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
Harden generated artefact boundaries so generated databases, cloned spec corpora,
SARIF/results, exported inventory, and local-only cache/env files cannot be
accidentally committed.

## Contract status
active

## Non-goals
- Do not refactor product code or change query logic.
- Do not regenerate inventory, database, SARIF, or shard outputs.
- Do not modify workflows or CodeQL queries.
- Do not add Python packages to `requirements.txt`.

## Carry-forward rules
The following constraints from this PR are promoted to durable invariants and must persist into all future PRs:
- Always pin CodeQL CLI to 2.20.1 or 2.20.2 (JSON-only database compatibility).
- Do not commit `database/`, `results/`, `azure-rest-api-specs/`, or generated inventory exports.
- `requirements.txt` lists only runtime-required Python packages; pytest is documented separately.
- `carl doctor` must remain healthy after any changes to `.github/carl/` artefacts.

## Approved scope
- Update `.gitignore` to ignore generated/heavy/local artefacts and add ownership comments.
- Remove already tracked generated inventory ZIP exports if needed to make the ignore boundary effective.
- Update `README.md` or `CONTRIBUTING.md` only if artefact ownership needs clarification.
- Update `.github/carl/memory.md` only if generated artefact boundaries or canonical operating assumptions change.
- Update this contract to match the approved scope and validation for this PR.

## Intentional amendments
- Supersedes the previous lightweight-test workflow scope in this file.
- Allows tracked generated inventory ZIP removals as part of repository-boundary hardening.

## Forbidden scope
- Modifying product behaviour in `SpeQL.py`, `analyze.py`, `refresh_database.py`, `run-queries.sh`, or export logic.
- Modifying CodeQL queries under `queries/`.
- Modifying workflows under `.github/workflows/`.
- Modifying source configs under `config/sources/`.
- Adding/removing/changing Python packages in `requirements.txt`.
- Regenerating or editing generated database, SARIF, JSON inventory, or shard contents.

## Architectural constraints
- SpeQL architecture and product behaviour must remain identical before and after this PR.
- `.gitignore` should document which script or pipeline owns each generated artefact area.
- Generated inventory boundaries must cover flat, grouped, sharded, and packaged export outputs.
- `requirements.txt` remains runtime-focused; pytest is installed separately as a test tool.

## Security constraints
- No secrets, tokens, or credentials may be committed.
- No new external network dependencies or dependencies in-repo may be introduced.
- Ignore rules must not accidentally hide committed source files outside the intended generated/local artefact boundaries.

## Files expected to change
- `.github/carl/current-pr-contract.md` — amended scope for this PR
- `.gitignore` — hardened generated/local artefact boundaries
- `inventory/api-index-23389057738.zip` — remove tracked generated export if confirmed in scope
- `inventory/api-index-sharded-23390552485.zip` — remove tracked generated export if confirmed in scope
- `README.md` and/or `CONTRIBUTING.md` — ownership clarification only if needed
- `.github/carl/memory.md` — durable generated-artefact boundary reconciliation (if needed)

## Tests / validation
- Install runtime deps: `pip3 install -r requirements.txt`
- Install test tool explicitly: `pip3 install pytest`
- Run lightweight tests: `python3 -m pytest tests/test_api_inventory_export.py tests/test_api_inventory_normalization.py -v`
- Confirm `git status` contains only intended `.gitignore`, docs, cARL, and generated ZIP removal changes
- Confirm no generated artefacts are newly added

## Stop conditions
- Any change that alters product script or CodeQL query behaviour.
- Any generated database, SARIF, JSON inventory, or shard file appearing in git status as a new addition.
- Any secret detected in changed files.

## Escalation triggers
- If hardening requires modifying workflows, product code, or query logic.
- If additional tracked generated artefacts outside the approved scope need deletion.
- If ignore patterns would overlap committed source files or docs unexpectedly.

## Context reset notes
This contract covers generated-artefact boundary hardening only. Close/reset after merge.
