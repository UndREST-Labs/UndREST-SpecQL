# Export Pipeline Guide

This document explains how to generate the SpecRecon API Inventory Index from the
Azure REST API spec corpus.

---

## What the Export Is For

The export pipeline produces a machine-readable JSON index that catalogues every
HTTP operation defined in the
[Azure REST API Specifications](https://github.com/Azure/azure-rest-api-specs)
repository.

Two complementary formats are produced:

- **`api-index.json`** — flat array, one entry per HTTP operation (schema `2.1.0`).
  Suitable for tooling that iterates over every operation individually.
- **`api-index-grouped.json`** — grouped/deduplicated structure (schema `3.0.0`).
  Routes are nested by provider namespace → host → route → version, so shared
  fields are stored only once.  This is the preferred format for size-sensitive
  consumers such as the future **APISpy** browser extension.

---

## Prerequisites

The export works from the local checkout of `azure-rest-api-specs/` that is
already managed by the existing SpecRecon refresh workflow.

**Step 1: Clone / update the spec corpus**

```bash
# Clone the specs and update (skips the CodeQL database build, which is not needed)
python3 refresh_database.py --all --skip-db-build
```

This clones `https://github.com/Azure/azure-rest-api-specs` into the
`azure-rest-api-specs/` directory at the repository root.

If you already have the directory, the command will pull the latest changes.

**Step 2: Verify the specs directory exists**

```bash
ls azure-rest-api-specs/specification/ | head -10
```

---

## Generating the Index Manually

```bash
python3 scripts/export/export_api_inventory.py
```

This uses the defaults:
- Source: `azure-rest-api-specs/specification`
- Output: `inventory/`
- No minified file, no grouped file

For a full run with all options including the grouped format:

```bash
python3 scripts/export/export_api_inventory.py \
    --source azure-rest-api-specs/specification \
    --output-dir inventory/ \
    --grouped \
    --minified \
    --verbose
```

---

## CLI Options

| Option          | Default                                | Description                                    |
|-----------------|----------------------------------------|------------------------------------------------|
| `--source`      | `azure-rest-api-specs/specification`   | Path to the specifications directory to walk   |
| `--output-dir`  | `inventory/`                           | Directory where output files are written       |
| `--minified`    | _(off)_                                | Also write minified variants (no indentation)  |
| `--grouped`     | _(off)_                                | Also write grouped/deduplicated `api-index-grouped.json` (schema 3.0.0) |
| `--verbose`     | _(off)_                                | Print per-file progress messages               |

---

## Output Files

| File                              | Requires     | Description |
|-----------------------------------|--------------|-------------|
| `inventory/api-index.json`        | _(always)_   | Flat pretty-printed index (schema 2.1.0, human-readable) |
| `inventory/api-index.min.json`    | `--minified` | Flat minified index (same data, no indentation) |
| `inventory/api-index-grouped.json`    | `--grouped`  | Grouped/deduplicated index (schema 3.0.0, recommended for runtime consumers) |
| `inventory/api-index-grouped.min.json` | `--grouped --minified` | Grouped minified index |

All files are listed in `.gitignore` and are not committed to the repository.
They are produced as build artifacts by the CI workflow and uploaded as GitHub
Actions artifacts.

See [API_INDEX_SCHEMA.md](./API_INDEX_SCHEMA.md) for a full description of every
field in the output.

---

## How It Differs from SpeQL Security Analysis

| Aspect              | SpeQL / `analyze.py`                        | Export pipeline                                |
|---------------------|---------------------------------------------|------------------------------------------------|
| **Goal**            | Find security vulnerabilities in Azure APIs | Build a complete operation inventory           |
| **Output**          | SARIF findings, security reports            | Normalized JSON index of all known operations  |
| **Scope**           | Focused queries (e.g. SAS URI exposure)     | All operations across the entire spec corpus   |
| **Consumer**        | Security engineers, CodeQL analysis         | APISpy extension, runtime comparison tools     |
| **CodeQL required** | Yes                                         | No — pure Python, stdlib only                  |
| **Run frequency**   | On demand / weekly                          | Daily (scheduled CI)                           |

---

## Scheduled / CI Generation

A GitHub Actions workflow at `.github/workflows/daily-api-index-export.yml`
runs the export automatically every day at 04:00 UTC and uploads the result as
a build artifact.

To trigger the workflow manually from the GitHub UI:
1. Navigate to **Actions → Daily API Index Export**
2. Click **Run workflow**
3. Optionally set `spec_scope` (default: `specification`)

---

## Running Tests

```bash
python3 -m pytest tests/test_api_inventory_export.py tests/test_api_inventory_normalization.py -v
```

These tests use synthetic in-memory spec objects and do not require the
`azure-rest-api-specs/` checkout to be present.
