# Microsoft Graph Authoritative Export Plan

## Status
Active — user-approved implementation.

## Source

- Repository: `https://github.com/microsoftgraph/msgraph-metadata.git`
- Revision: `b8cbef92f6959dca8150bf3edcc650863765e529`
- License: MIT
- Inputs:
  - `openapi/v1.0/openapi.yaml`
  - `openapi/beta/openapi.yaml`

The repository is Microsoft's canonical Graph metadata/OpenAPI source. The exact
commit is recorded in source configuration and checked out detached for
reproducibility.

## Implementation

1. Add a Microsoft Graph source config with exact-commit pinning.
2. Extend Python source refresh to honor an optional `source_commit` after clone
   or fetch. Do not alter unrelated workflows.
3. Add safe YAML discovery/loading to the exporter. Use `yaml.safe_load`; never
   resolve remote references.
4. Auto-select a `microsoft-graph` profile for the official source repository,
   with an explicit `--source-profile` override for local fixtures.
5. For that profile only:
   - use exact host `graph.microsoft.com`;
   - prepend the OpenAPI server base path (`/v1.0` or `/beta`) to route paths;
   - classify the plane as `data`;
   - group all routes under the single provider namespace `Microsoft.Graph` so
     APISpy's existing exact-host single-shard fallback remains fail-closed and
     deterministic;
   - preserve source path templates, operation IDs, OData parameter names, and
     bounded local-reference research metadata.
6. Add focused fixtures/tests for JSON compatibility, YAML safety, v1.0/beta,
   route-key normalisation, provider grouping, and dependency failure.
7. Update source/export/schema documentation and durable cARL memory.
8. Clone the pinned source locally, generate an ignored candidate export, inspect
   counts and provenance, and do not commit generated output or the source clone.
9. Compute deterministic semantic hashes with volatile export timestamps removed.
   Export workflows restore the last changed hash from a tiny Actions cache and
   only upload artifacts, publish the shard release, or dispatch APISpy when the
   new hash differs.

## Validation

- Targeted export and normalization tests.
- Full pytest suite.
- Python compile checks.
- Candidate export inspection for one provider shard, exact host, both versions,
  and pinned source commit.
- `git diff --check`, generated-artifact/source-clone tracking checks, and
  `carl doctor`.

## Stop conditions

- Upstream revision or license cannot be verified.
- Safe YAML parsing cannot be used.
- Azure output changes unexpectedly.
- A breaking schema change or speculative route derivation is required.
- Generated artifacts or source clones become tracked.
