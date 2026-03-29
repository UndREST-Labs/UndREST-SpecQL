# Adding a New API Source

This guide explains how to extend SpeQL with a new API spec source beyond
`azure-rest-api-specs`.  The system is designed so that each additional
source requires only:

1. A JSON source config file in `config/sources/`
2. Optionally, platform-specific CodeQL queries in `queries/<platform>-security/`

No changes to core scripts are needed.

---

## Concepts

| Term | Meaning |
|------|---------|
| **Source** | An upstream repository of OpenAPI/Swagger spec files |
| **Source config** | A JSON file in `config/sources/` describing one source |
| **Specs dir** | The local directory where the source repo is cloned |
| **Database dir** | Where the CodeQL database for the source is stored |
| **Spec path** | A subdirectory within the specs dir used for partial indexing |
| **Query pack** | A directory of `.ql` files (with a `qlpack.yml`) targeting a platform |

---

## Step 1 — Create a source config file

Source configs live in `config/sources/` and follow this schema:

```json
{
  "id":                "my-platform",
  "name":              "My Platform REST API Specifications",
  "repo_url":          "https://github.com/MyOrg/my-platform-api-specs.git",
  "specs_dir":         "my-platform-api-specs",
  "database_dir":      "database/my-platform-api-db",
  "default_spec_path": "specification",
  "source_repo":       "MyOrg/my-platform-api-specs",
  "source_branch":     "main",
  "query_packs":       ["queries/my-platform-security"]
}
```

### Field reference

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `id` | Yes | — | Short identifier used in logs and filenames |
| `name` | Yes | — | Human-readable name displayed in CLI output |
| `repo_url` | Yes | — | Git URL of the upstream spec repository |
| `specs_dir` | Yes | — | Local directory where the repo is cloned |
| `database_dir` | Yes | — | Where to write the CodeQL database |
| `default_spec_path` | Yes | — | Default subdirectory within `specs_dir` to index |
| `source_repo` | No | `"unknown"` | `org/repo` identifier recorded in export metadata |
| `source_branch` | No | `"main"` | Branch name recorded in export metadata |
| `query_packs` | No | `["queries/azure-security"]` | List of query pack directories to run against this source's database |

Save the file as `config/sources/<id>.json`.

---

## Step 2 — Clone and refresh the spec repository

```bash
# Refresh (clone or update) using the new source config
python3 refresh_database.py --source-config config/sources/my-platform.json --all --skip-db-build

# Or with the bash script
./refresh-database.sh --source-config config/sources/my-platform.json --all --skip-db-build
```

The `--source-config` flag causes the scripts to read `repo_url`, `specs_dir`,
`database_dir`, and `default_spec_path` from the config file rather than using
the built-in Azure defaults.

All other flags (`--fresh`, `--path`, `--branch`, `--clean`, etc.) still work
as normal and override the config values when provided.

---

## Step 3 — Build a CodeQL database (optional)

If you want to run CodeQL security queries against the new source:

```bash
python3 refresh_database.py \
  --source-config config/sources/my-platform.json \
  --all
```

This clones the repo **and** builds the CodeQL database at the path specified
by `database_dir` in the config.

---

## Step 4 — Export the API inventory

```bash
python3 scripts/export/export_api_inventory.py \
  --source my-platform-api-specs/specification \
  --output-dir inventory/ \
  --source-repo MyOrg/my-platform-api-specs \
  --source-branch main \
  --sharded \
  --minified \
  --verbose
```

The `--source-repo` and `--source-branch` arguments are recorded in the export
metadata so that consumers of the index can trace the data back to its origin.
When omitted, the values are auto-detected from the git remote.

---

## Step 5 — Add platform-specific CodeQL queries (optional)

If you want to write CodeQL security queries tailored to the new platform:

1. Create a query pack directory:
   ```
   queries/my-platform-security/
   ├── qlpack.yml
   └── MyQuery.ql
   ```

2. `qlpack.yml` minimal template:
   ```yaml
   name: speql/my-platform-security
   version: 1.0.0
   dependencies:
     codeql/javascript-all: "~0.9.0"
   ```

3. Install the pack dependencies:
   ```bash
   cd queries/my-platform-security && codeql pack install && cd ../..
   ```

4. Reference the pack in the source config's `query_packs` field so that
   `run-queries.sh` picks it up automatically:
   ```json
   "query_packs": ["queries/my-platform-security"]
   ```

See `queries/azure-security/` for worked examples of query structure and
metadata annotations.

---

## Running queries

### Default (source config drives everything)

```bash
# Reads database_dir and query_packs from the source config
./run-queries.sh --source-config config/sources/my-platform.json
```

### Override the database (cross-source)

Run an existing query pack against a different source's database without
changing any config file:

```bash
# Run Azure queries against a second source's database
./run-queries.sh \
  --database database/my-platform-api-db \
  --queries queries/azure-security
```

### Run multiple query packs against one database

```bash
./run-queries.sh \
  --database database/azure-api-db \
  --queries queries/azure-security \
  --queries queries/my-platform-security
```

The `--queries` flag can be repeated any number of times.  When provided it
fully replaces the `query_packs` list from the source config.

---

## Step 6 — Use in CI (optional)

All three GitHub Actions workflows support a `source_config` input so that
you can target any registered source from the GitHub UI or a cron schedule:

**Manually trigger a security scan for a new source:**

1. Navigate to **Actions → SpeQL Security Scan**
2. Click **Run workflow**
3. Set `source_config` to `config/sources/my-platform.json`

**Manually trigger an export for a new source:**

1. Navigate to **Actions → Daily API Index Export (Sharded)**
2. Click **Run workflow**
3. Set `source_config` to `config/sources/my-platform.json`

**Add a dedicated scheduled run** by duplicating one of the existing workflow
files and hardcoding the `source_config` value in the schedule trigger.

---

## Source config registry

The `config/sources/` directory acts as the source registry.  The currently
registered sources are:

| File | Source | Query packs |
|------|--------|-------------|
| `azure.json` | `Azure/azure-rest-api-specs` — Microsoft Azure REST API Specifications | `queries/azure-security` |

Add your new file to this table when you create it.

---

## Tips

- **Sparse checkout**: For large repositories, keep `default_spec_path` narrow
  (e.g. `specification/compute`) to speed up cloning.  Use `--all` only when
  you need the full corpus.
- **Multiple sources in one workflow**: Run the refresh and export steps inside
  a matrix strategy, passing a different `source_config` to each matrix job.
- **Cross-source query runs**: Use `--database` and `--queries` on
  `run-queries.sh` to run any query pack against any database without touching
  the config files.  This is useful for applying a general-purpose pack (e.g.
  `queries/azure-security`) to a new source before building a dedicated pack.
- **Plane classification**: `normalize_api_inventory.py` classifies operations
  as `management`, `data`, or `unknown` based on host/path heuristics tuned for
  Azure.  If your source uses a different URL structure you can extend
  `classify_plane()` in `scripts/export/normalize_api_inventory.py` with
  additional host or path patterns.

