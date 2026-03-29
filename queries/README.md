# Queries

This directory contains CodeQL queries organised by API platform.

Each platform gets its own subdirectory and `qlpack.yml` so that queries can
be installed, versioned, and executed independently.

## Current platforms

| Directory | Platform | Description |
|-----------|----------|-------------|
| [`azure-security/`](azure-security/) | Microsoft Azure | 8 queries targeting Azure REST API spec patterns (SAS URI exposure, Key Vault misconfigs, Logic App secure data, hardcoded ARM secrets, etc.) |

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
5. Reference the new query directory in your `run-queries.sh` invocation or
   create a dedicated script.

See [docs/ADDING_API_SOURCES.md](../docs/ADDING_API_SOURCES.md) for the full
guide on adding a new API source, including source configs, database refresh,
and the export pipeline.
