# API Index Schema Reference

This document describes the files produced by `scripts/export/export_api_inventory.py`.

Two formats are available:

| File | Schema version | Flag | Description |
|------|---------------|------|-------------|
| `api-index.json` / `api-index.min.json` | `2.1.0` | _(default)_ | Flat array — one entry per HTTP operation found |
| `api-index-grouped.json` / `api-index-grouped.min.json` | `3.2.0` | `--grouped` | Grouped/deduplicated — routes nested by provider → host → route → version |
| `shards/{Provider.Namespace}.json` / `shards/{Provider.Namespace}.min.json` | `3.2.0` | `--sharded` | Per-provider shard — same grouped structure scoped to one provider namespace |

> **Why the grouped format?**
> The flat format repeats `host`, `provider_namespace`, `method`, `path_template`,
> and the spec file path for every version of a route.  For the full Azure REST API
> spec corpus this produces a file that exceeds 100 MB even when minified — too large
> for any runtime consumer.  The grouped format stores these shared fields **once**
> per route and nests version-specific detail underneath, achieving significant size
> reduction through structural deduplication rather than field dropping.

---

## Flat Format — `api-index.json` (schema `2.1.0`)

### Top-Level Structure

```json
{
  "metadata": { ... },
  "operations": [ ... ],
  "summary": { ... }
}
```

### `metadata` Block

```json
{
  "generated_at": "2026-03-21T04:00:00Z",
  "source_repo": "Azure/azure-rest-api-specs",
  "source_branch": "main",
  "source_commit": "a1b2c3d4e5f6...",
  "export_scope": "specification",
  "tool_name": "SpecRecon",
  "tool_component": "SpeQL",
  "schema_version": "2.1.0"
}
```

| Field            | Type   | Description |
|------------------|--------|-------------|
| `generated_at`   | string | ISO 8601 UTC timestamp of when the export was produced |
| `source_repo`    | string | The upstream Azure REST API specs repository (`Azure/azure-rest-api-specs`) |
| `source_branch`  | string | The branch used (always `main` for the daily export) |
| `source_commit`  | string | Git commit SHA of the specs checkout, or `"unknown"` if unavailable |
| `export_scope`   | string | The directory name passed as `--source` (typically `"specification"`) |
| `tool_name`      | string | Always `"SpecRecon"` |
| `tool_component` | string | Always `"SpeQL"` |
| `schema_version` | string | `"2.1.0"` — increment when the schema changes |

### `operations` Array — Entry Fields

Each element represents one HTTP operation (method + path) found in a spec file.

```json
{
  "host": "management.azure.com",
  "method": "GET",
  "path_template": "/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/Microsoft.Storage/storageAccounts/{accountName}",
  "operation_id": "StorageAccounts_GetProperties",
  "api_versions": ["2023-01-01"],
  "spec_file": "storage/resource-manager/Microsoft.Storage/stable/2023-01-01/storage.json",
  "source_kind": "paths",
  "plane": "management",
  "is_preview": false,
  "lookup_key": "management.azure.com|GET|/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/Microsoft.Storage/storageAccounts/{accountName}"
}
```

| Field           | Type    | Description |
|-----------------|---------|-------------|
| `host`          | string  | Hostname (lowercased): `"management.azure.com"`, `"myvault.vault.azure.net"`, or `"unknown"` |
| `method`        | string  | HTTP method (uppercase): `GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `HEAD`, `OPTIONS`, `TRACE` |
| `path_template` | string  | URL path template with `{paramName}` placeholders |
| `operation_id`  | string  | `operationId` from the spec, or `""` when absent |
| `api_versions`  | array   | API version strings for this operation (derived from the file path) |
| `spec_file`     | string  | Relative path to the source spec file (forward slashes) |
| `source_kind`   | string  | Which paths block the operation came from: `"paths"`, `"x-ms-paths"`, or `"other"` |
| `plane`         | string  | `"management"`, `"data"`, or `"unknown"` |
| `is_preview`    | boolean | `true` when the operation is from a preview spec or has a preview API version |
| `lookup_key`    | string  | `"<host>|<METHOD>|<path_template>"` — pre-computed for fast runtime matching |

### `summary` Block (flat)

```json
{
  "total_operations": 12345,
  "total_spec_files": 678,
  "providers": ["Microsoft.Compute", "Microsoft.Network", "Microsoft.Storage"],
  "planes": { "management": 10000, "data": 2000, "unknown": 345 },
  "errors": 0
}
```

---

## Grouped Format — `api-index-grouped.json` (schema `3.2.0`)

### Top-Level Structure

```json
{
  "metadata": { ... },
  "providers": { ... },
  "summary": { ... }
}
```

### `metadata` Block (grouped)

Same fields as the flat metadata, with two additions:

```json
{
  "schema_version": "3.2.0",
  "export_format": "grouped"
}
```

### `providers` Map

```
providers
  └─ provider_namespace         (e.g. "Microsoft.Storage", "unknown")
       └─ hosts
            └─ host             (e.g. "management.azure.com")
                 └─ routes
                      └─ route_key  ("METHOD path_template")
                           ├─ [shared route fields]
                           └─ versions
                                └─ api_version  (e.g. "2023-01-01")
                                     └─ [version-specific fields]
```

#### Route Entry (shared fields — stored once per route)

```json
"GET /subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/Microsoft.Storage/storageAccounts/{accountName}": {
  "method": "GET",
  "path_template": "/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/Microsoft.Storage/storageAccounts/{accountName}",
  "provider_namespace": "Microsoft.Storage",
  "plane": "management",
  "lookup_key": "management.azure.com|GET|/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/Microsoft.Storage/storageAccounts/{accountName}",
  "api_family": {
    "family_key": "Microsoft.Storage/storageAccounts",
    "provider_namespace": "Microsoft.Storage",
    "resource_type_path": ["storageAccounts"],
    "resource_key": "Microsoft.Storage/storageAccounts",
    "resource_depth": 1
  },
  "versions": { ... },
  "version_lineage": {
    "ordered_versions": [
      {
        "api_version": "2022-01-01",
        "stability": "stable",
        "next_version": "2023-01-01"
      },
      {
        "api_version": "2023-01-01",
        "stability": "stable",
        "previous_version": "2022-01-01"
      }
    ]
  }
}
```

| Field                | Type   | Description |
|----------------------|--------|-------------|
| `method`             | string | HTTP method (uppercase) |
| `path_template`      | string | URL path template with `{paramName}` placeholders |
| `provider_namespace` | string | E.g. `"Microsoft.Storage"`, source-profile namespace `"Microsoft.Graph"`, or `"unknown"` |
| `plane`              | string | `"management"`, `"data"`, or `"unknown"` |
| `lookup_key`         | string | `"<host>|<METHOD>|<path_template>"` for fast exact matching |
| `api_family`         | object | Optional bounded structural family/hierarchy metadata derived from the normalized route template and provider namespace |
| `versions`           | object | Map of `api_version → version entry` (see below) |
| `version_lineage`    | object | Optional bounded ordered version list and previous/next links derived from this route's version keys |

#### Route `api_family` object

```json
{
  "family_key": "Microsoft.Storage/storageAccounts",
  "provider_namespace": "Microsoft.Storage",
  "resource_type_path": ["storageAccounts", "blobServices", "containers"],
  "resource_key": "Microsoft.Storage/storageAccounts/blobServices/containers",
  "resource_depth": 3,
  "parent_resource_type_path": ["storageAccounts", "blobServices"],
  "parent_resource_key": "Microsoft.Storage/storageAccounts/blobServices"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `family_key` | string | Provider namespace plus top-level resource type. Sibling operations on the same top-level resource family share this key. |
| `provider_namespace` | string | Provider namespace used to derive the family. |
| `resource_type_path` | array | Bounded ordered resource-type segments after `/providers/{namespace}`. Template parameters and Azure singleton `default` name segments are excluded. |
| `resource_key` | string | Provider namespace plus the full bounded `resource_type_path`. |
| `resource_depth` | integer | Number of derived resource-type segments before bounding. |
| `parent_resource_type_path` | array | Optional bounded parent resource-type path, present only for nested resources. |
| `parent_resource_key` | string | Optional provider namespace plus `parent_resource_type_path`. |
| `resource_type_path_truncated` | boolean | Present and `true` when the route contains more resource-type segments than the exporter cap. |

`api_family` is omitted when a route has no provider namespace or no structural
resource-type path. It is structural only: descriptions, tags, operation names,
examples, and inferred product semantics are not used.

For the `microsoft-graph` source profile, canonical `/v1.0` and `/beta` paths are
grouped under the fixed source namespace `Microsoft.Graph`. Graph routes do not
receive ARM-specific `api_family` metadata because they have no
`/providers/{namespace}` structure.

#### Route `version_lineage` object

```json
{
  "ordered_versions": [
    {
      "api_version": "2022-01-01",
      "stability": "stable",
      "next_version": "2023-01-01-preview"
    },
    {
      "api_version": "2023-01-01-preview",
      "stability": "preview",
      "previous_version": "2022-01-01"
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `ordered_versions` | array | Bounded list of version entries sorted deterministically by date-like prefix and then lexically. |
| `versions_truncated` | boolean | Present and `true` when more version keys exist than the exporter cap. |

Each `ordered_versions` item contains:

| Field | Type | Description |
|-------|------|-------------|
| `api_version` | string | Version key from the route's `versions` object. |
| `stability` | string | `"preview"` when the version string contains `preview`, `"stable"` for bare `YYYY-MM-DD`, otherwise `"unknown"`. |
| `previous_version` | string | Previous version in the bounded ordered list; omitted for the first item. |
| `next_version` | string | Next version in the bounded ordered list; omitted for the last item. |

`version_lineage` is omitted when a route has no known version keys other than
`"unknown"`.

#### Version Entry (version-specific fields)

```json
"2023-01-01": {
  "is_preview": false,
  "spec_files": ["storage/resource-manager/Microsoft.Storage/stable/2023-01-01/storage.json"],
  "operation_ids": ["StorageAccounts_GetProperties"],
  "source_kinds": ["paths"],
  "auth": {
    "status": "required",
    "requirements": [{"azure_auth": ["user_impersonation"]}],
    "schemes": [{"name": "azure_auth", "type": "oauth2"}]
  },
  "parameters": {
    "path": ["accountName", "resourceGroupName", "subscriptionId"],
    "query": ["api-version"]
  },
  "request_schemas": [],
  "response_schemas": [
    {
      "fingerprint": "sha256:0123456789abcdef01234567",
      "type": "object",
      "top_level_fields": [{"name": "id", "type": "string", "required": false}],
      "status_codes": ["200"]
    }
  ]
}
```

| Field          | Type    | Description |
|----------------|---------|-------------|
| `is_preview`   | boolean | `true` when this version is from a preview spec or has a preview version string |
| `spec_files`   | array   | Relative paths to all spec files that define this route at this version |
| `operation_ids`| array   | `operationId` values found at this version (deduplicated) |
| `source_kinds` | array   | Which paths blocks contributed: `"paths"`, `"x-ms-paths"` (deduplicated) |
| `auth` | object | Documented auth status (`required`, `optional_or_anonymous`, `unspecified`, or `mixed`), requirement alternatives, and referenced scheme descriptors |
| `parameters` | object | Bounded parameter-name arrays grouped by location (`query`, `path`, `header`, `cookie`) |
| `request_schemas` | array | Deduplicated bounded request-body schema summaries with structural fingerprints |
| `response_schemas` | array | Deduplicated bounded response schema summaries with status codes and content types |

These additive fields are omitted when the specification provides no corresponding metadata. Schema fingerprints are SHA-256 hashes of a canonical, bounded structural shape. The shape includes types, formats, required-property state, property names, arrays, object additional-property structure, and composition keywords. Top-level field summaries union `allOf` fields and conservatively include fields from `oneOf`/`anyOf` alternatives to avoid false undocumented-field signals. Descriptions, examples, defaults, enum values, and raw schema documents are excluded. Only local JSON references are resolved; external or cyclic references are represented by safe marker types.

> **Size win:** a route that appears in 10 spec versions goes from 10 flat entries
> (each repeating host, method, path_template, spec_file, plane, …) to 1 route
> entry with 10 compact version sub-entries.

### `summary` Block (grouped)

```json
{
  "total_routes": 5000,
  "total_versions": 18000,
  "total_spec_files": 678,
  "providers": ["Microsoft.Compute", "Microsoft.Network", "Microsoft.Storage"],
  "planes": { "management": 4500, "data": 400, "unknown": 100 },
  "errors": 0
}
```

| Field            | Type    | Description |
|------------------|---------|-------------|
| `total_routes`   | integer | Total distinct routes (unique method + path_template per host) |
| `total_versions` | integer | Total version entries across all routes |
| `total_spec_files` | integer | Number of JSON files inspected |
| `providers`      | array   | Sorted list of distinct provider namespaces (excludes `"unknown"`) |
| `planes`         | object  | Count of routes per plane |
| `errors`         | integer | Files that could not be parsed (skipped with a warning) |

---

## Classification Rules

**`plane` (in priority order):**
1. Host is `management.azure.com` or `management.core.windows.net` → `"management"`
2. Host ends with a known data-plane suffix (`.blob.core.windows.net`, `.vault.azure.net`, etc.) → `"data"`
3. Path contains `/providers/` or `/subscriptions/` → `"management"`
4. Otherwise → `"unknown"`

**`is_preview` / stability:**
1. Spec file path contains a `preview/` directory → preview
2. Spec file path contains a `stable/` directory → stable
3. API version string contains `preview` (case-insensitive) → preview
4. API version string is a bare `YYYY-MM-DD` date → stable
5. Otherwise → `"unknown"`

---

## Matching Semantics

Given an observed API call, three matching modes are supported with the grouped format:

### Exact match (host + method + path_template + api-version)

Build the lookup key and find the route, then verify the api-version is in `versions`:

```python
lookup_key = f"{host}|{method}|{path_template}"
# traverse: providers → namespace → hosts → host → routes → route_key → versions → api_version
```

Possible outcomes:

| Outcome | Meaning |
|---------|---------|
| Route found, version present, `is_preview: false` | Stable, fully documented |
| Route found, version present, `is_preview: true` | Documented but preview-only |
| Route found, version **not** present | Version mismatch — call uses an undocumented version |
| Route **not** found, but provider namespace matches | Provider known, route unknown — possible private/sub-resource path |
| No match | Undocumented call — potential shadow API or private endpoint |

### Route-only match (host + method + path_template, any version)

Look up the route entry and read all available versions from the `versions` map.
This supports "is this route known at all?" without caring about the specific version.

### Provider match (fallback)

Navigate to `providers[provider_namespace]` to confirm the provider is known even when
the exact route cannot be matched.

---

## Sharded Format — `shards/{Provider.Namespace}.json` (schema `3.2.0`)

When `--sharded` is used, the exporter writes one JSON file per provider namespace
into a `shards/` subdirectory.  Each shard uses the same schema version (`3.2.0`) as
the grouped format but scopes the content to a single provider.

### File naming

The provider namespace is used as-is as the filename; characters that are illegal on
common file systems (`/`, `\`) are replaced with `_`.  The `unknown` namespace
(for routes without a `/providers/` segment) is written as `unknown.json`.

### Top-Level Structure

```json
{
  "metadata": { ... },
  "provider_namespace": "Microsoft.Storage",
  "hosts": { ... },
  "summary": { ... }
}
```

### `metadata` Block (sharded)

Same fields as the grouped metadata, with `export_format` set to `"sharded"` and an
additional `provider_namespace` field:

```json
{
  "schema_version": "3.2.0",
  "export_format": "sharded",
  "provider_namespace": "Microsoft.Storage"
}
```

### `hosts` Map

Identical structure to `providers[provider_namespace]["hosts"]` in the grouped format:

```
hosts
  └─ host             (e.g. "management.azure.com")
       └─ routes
            └─ route_key  ("METHOD path_template")
                 ├─ [shared route fields]
                 └─ versions
                      └─ api_version
                           └─ [version-specific fields]
```

### `summary` Block (sharded)

```json
{
  "total_routes": 120,
  "total_versions": 450,
  "total_spec_files": 678,
  "planes": { "management": 115, "data": 5 },
  "errors": 0
}
```

The sharded summary omits the `providers` list (it is always a single provider).

> **Use case:** Consumers that only care about one provider namespace (e.g. the APISpy
> extension checking `Microsoft.KeyVault` calls) can load a much smaller shard file
> instead of the full grouped index.

---

## Minified Files

The minified files (`*.min.json`) contain identical data serialized without indentation:

```json
{"metadata":{...},"providers":{...},"summary":{...}}
```

> **Note:** The minified grouped export is the intended input format for a future
> runtime-optimized artifact (e.g. APISpy browser extension).  A separate
> runtime-specific distribution format may be introduced later if further size
> reduction is needed, but the minified grouped export is the canonical reference
> in the meantime.

---

## Schema Evolution

`schema_version` follows [Semantic Versioning](https://semver.org/):

- **Patch** (`x.x.z`): bug fixes, documentation only
- **Minor** (`x.y.0`): new fields added (backwards-compatible)
- **Major** (`z.0.0`): fields removed or renamed (breaking)

Consumers should check `schema_version` before processing.

### Changelog

| Version | Format | Changes |
|---------|--------|---------|
| `3.2.0` | grouped / sharded | Added bounded route-level `api_family` and `version_lineage` metadata so consumers can correlate sibling operations, parent/child resource hierarchy, ordered API versions, and deterministically derived preview/stable version classes. Existing 3.1.0 fields are unchanged. |
| `3.1.0` | grouped / sharded | Added bounded `auth`, parameter-name, request-schema, and response-schema summaries to version entries. Local schema references are resolved for structural fingerprints; descriptions, examples, defaults, and remote references are not exported. Existing 3.0.0 fields are unchanged. |
| `3.0.0` | grouped / sharded | **New format.** Providers → hosts → routes → versions hierarchy. Replaces the flat operations array for size-sensitive consumers. `export_format: "grouped"` in metadata. The `--sharded` flag uses the same schema but scopes each file to one provider namespace (`export_format: "sharded"`). |
| `2.1.0` | flat | Added `source_kind` field to each operation entry (which paths block the operation came from: `"paths"` or `"x-ms-paths"`). |
| `2.0.0` | flat | **Breaking**: removed `provider_namespace`, `resource_provider_family`, `stable_versions`, `preview_versions`, `source_kind`, `tags`, `parameter_names`, `required_query_parameters`, and `has_api_version_parameter`. |
| `1.0.0` | flat | Initial schema release. |
