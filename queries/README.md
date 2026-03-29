# Queries

This directory contains CodeQL queries organised by API platform.

Each platform gets its own subdirectory and `qlpack.yml` so that queries can
be installed, versioned, and executed independently.

## Current platforms

| Directory | Platform | Description |
|-----------|----------|-------------|
| [`azure-security/`](azure-security/) | Microsoft Azure | 8 queries targeting Azure REST API spec patterns (SAS URI exposure, Key Vault misconfigs, Logic App secure data, hardcoded ARM secrets, etc.) |

## Query pack ↔ API source mapping

Each source config in `config/sources/` declares which query packs should run
against its database via the `query_packs` field:

```json
{
  "database_dir": "database/azure-api-db",
  "query_packs":  ["queries/azure-security"]
}
```

`run-queries.sh` reads this field automatically when `--source-config` is
passed, so there is no separate mapping file to maintain.

A single query pack can be run against multiple API sources using the
`--database` flag, and multiple packs can target the same database using
repeated `--queries` flags:

```bash
# Run the Azure pack against a second source's database (cross-source)
./run-queries.sh \
  --database database/other-source-db \
  --queries queries/azure-security

# Run two packs against one database
./run-queries.sh \
  --database database/azure-api-db \
  --queries queries/azure-security \
  --queries queries/my-platform-security
```

## Adding queries for a new platform

1. Create a new subdirectory: `queries/<platform>-security/`
2. Add a `qlpack.yml` declaring the pack name and dependencies:
   ```yaml
   name: speql/<platform>-security
   version: 1.0.0
   dependencies:
     codeql/javascript-all: "~0.9.0"
   ```
3. Add your `.ql` query files.  Follow the conventions in
   `queries/azure-security/` for metadata annotations
   (`@id`, `@name`, `@description`, `@kind`, `@problem.severity`, etc.).
4. Install the pack:
   ```bash
   cd queries/<platform>-security && codeql pack install && cd ../..
   ```
5. Add the pack to the source config's `query_packs` list:
   ```json
   "query_packs": ["queries/<platform>-security"]
   ```

See [docs/ADDING_API_SOURCES.md](../docs/ADDING_API_SOURCES.md) for the full
guide on adding a new API source, including source configs, database refresh,
and the export pipeline.

