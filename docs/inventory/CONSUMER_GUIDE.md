# Consumer Guide — Using the API Inventory Index

This guide is for developers who want to consume `api-index-grouped.json` produced by the
SpecRecon export pipeline, for example to build the **APISpy** browser extension
or any other tool that performs "spec vs reality" comparison of Azure REST API calls.

---

## Overview

The export pipeline produces two formats:

| File | Schema | Best for |
|------|--------|----------|
| `api-index.json` | `2.1.0` | Tooling that processes every operation individually (analysis scripts, grep, jq) |
| `api-index-grouped.json` | `3.0.0` | Runtime consumers that need compact, pre-grouped data (browser extensions, proxies) |

This guide focuses on the **grouped format** (`api-index-grouped.json`), which is
the recommended format for size-sensitive consumers.  The flat format is documented
in [API_INDEX_SCHEMA.md](./API_INDEX_SCHEMA.md) for reference.

---

## Grouped Format Overview

```
providers
  └─ provider_namespace
       └─ hosts
            └─ host
                 └─ routes
                      └─ "METHOD path_template"   ← route_key
                           ├─ method
                           ├─ path_template
                           ├─ provider_namespace
                           ├─ plane
                           ├─ lookup_key           ← "host|METHOD|path_template"
                           └─ versions
                                └─ api_version
                                     ├─ is_preview
                                     ├─ spec_files
                                     ├─ operation_ids
                                     └─ source_kinds
```

See [API_INDEX_SCHEMA.md](./API_INDEX_SCHEMA.md) for a complete field reference.

---

## Questions the Index Can Answer

Given an observed API call (intercepted by a browser extension or proxy), the
index can answer:

| Question | How to answer |
|----------|---------------|
| Is this API call documented in the specs? | Find the route via `lookup_key` |
| What operation is this call? | Read `operation_ids` from the matching version entry |
| Is the call using a preview API version? | Check `is_preview` in the version entry |
| Is there a version mismatch? | Check whether the observed api-version key exists in `versions` |
| Is this operation preview-only? | If all version entries have `is_preview: true` |
| Which Azure service owns this path? | Read `provider_namespace` from the route |
| Is this a management-plane or data-plane call? | Read `plane` from the route |

---

## Matching Algorithm (grouped format)

Given an observed request, follow these steps:

### Step 1 — Normalize the observed call

```
host        = observed host, lowercased     (e.g. "management.azure.com")
method      = observed HTTP method, uppercase (e.g. "GET")
path        = observed URL path, without query string
              (concrete values, e.g. /subscriptions/abc-123/providers/Microsoft.Storage/…)
api_version = extracted from the "api-version" query parameter
```

### Step 2 — Identify the provider namespace

```python
from scripts.export.normalize_api_inventory import extract_provider_namespace
provider_ns = extract_provider_namespace(path)  # e.g. "Microsoft.Storage"
```

### Step 3 — Narrow the candidate set

Use the provider namespace and host to retrieve the subset of routes to match
against, avoiding a full-index scan:

```python
host_entry = index["providers"].get(provider_ns, {}).get("hosts", {}).get(host, {})
routes = host_entry.get("routes", {})  # dict of route_key → route
```

### Step 4 — Template matching (the common case)

Because observed URLs contain concrete parameter values (GUIDs, resource names),
match the observed path against each route's `path_template` by converting
`{paramName}` placeholders to a single-segment regex:

```python
import re

def match_route(host, method, observed_path, index):
    from scripts.export.normalize_api_inventory import extract_provider_namespace
    provider_ns = extract_provider_namespace(observed_path)

    # Check the identified provider first, fall back to "unknown"
    for ns in (provider_ns, "unknown"):
        host_data = index["providers"].get(ns, {}).get("hosts", {}).get(host, {})
        for route_key, route in host_data.get("routes", {}).items():
            if route["method"] != method:
                continue
            # re.escape escapes braces; un-escape {param} placeholders → [^/]+
            pattern = re.sub(r"\\{[^}]+\\}", r"[^/]+", re.escape(route["path_template"]))
            if re.fullmatch(pattern, observed_path):
                return route
    return None
```

### Step 5 — Version check

Once a route is matched, check the version:

```python
def check_version(route, observed_api_version):
    versions = route.get("versions", {})
    if observed_api_version in versions:
        ver = versions[observed_api_version]
        return "exact_match", ver["is_preview"]
    elif versions:
        return "version_mismatch", None
    else:
        return "route_match_no_versions", None
```

---

## "Spec vs Reality" Matching Outcomes

| Outcome | Meaning |
|---------|---------|
| Route found, version present, `is_preview: false` | Stable, fully documented call |
| Route found, version present, `is_preview: true` | Documented but preview-only |
| Route found, version **not** present | Version mismatch — undocumented version |
| Provider namespace matches but route not found | Provider known, route unknown — possible private/sub-resource path |
| No match at all | Undocumented call — potential shadow API or private endpoint |

---

## Loading the Index

### JavaScript (browser extension / Node.js)

```javascript
// In a service worker or background script:
const response = await fetch(chrome.runtime.getURL("api-index-grouped.min.json"));
const index = await response.json();

// Build a fast lookup map: lookup_key → route
const byLookupKey = {};
for (const [ns, prov] of Object.entries(index.providers)) {
  for (const [host, hostData] of Object.entries(prov.hosts)) {
    for (const [routeKey, route] of Object.entries(hostData.routes)) {
      byLookupKey[route.lookup_key] = route;
    }
  }
}
```

### Python

```python
import json
from pathlib import Path

index = json.loads(Path("inventory/api-index-grouped.json").read_text())

# Build a lookup map for O(1) route access by lookup_key
by_key = {}
for ns, prov in index["providers"].items():
    for host, host_data in prov["hosts"].items():
        for route_key, route in host_data["routes"].items():
            by_key[route["lookup_key"]] = route
```

---

## Versioning and Freshness

- `metadata.generated_at` — when the index was produced
- `metadata.source_commit` — the exact Azure REST API specs commit used
- `metadata.schema_version` — `"3.0.0"` for the grouped format; check before processing
- `metadata.export_format` — `"grouped"` (distinguishes from flat format files)

The index is regenerated daily by the SpecRecon CI workflow.

---

## Future Distribution Format

The minified grouped export (`api-index-grouped.min.json`) is the recommended
input for runtime consumers today.  A separate, more compact runtime-distribution
artifact (e.g. pre-indexed by lookup key, binary format) may be introduced later
if further size or lookup-speed improvements are needed, but this is a non-goal
for the current release.

---

## Future Enrichment

The grouped schema supports future enrichment without breaking changes:

- **SpeQL findings overlay** — security findings (SAS URI exposure, missing auth)
  could be attached to matching routes as an additional `findings` array.
- **Deprecation signals** — Azure deprecation notices could populate a
  `deprecated` field per version entry.
- **Cross-version delta** — comparing two index snapshots can surface new,
  changed, or removed routes between spec versions.
