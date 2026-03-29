<img src="https://raw.githubusercontent.com/UndREST-Labs/.github/main/profile/UndREST-Labs.PNG" alt="UndREST Labs" width="600"/>

<img src="https://raw.githubusercontent.com/UndREST-Labs/.github/main/profile/UndREST-SpeQL.PNG" alt="SpeQL" width="600"/>

# UndREST-SpecQL — API Spec Query Engine

**SpeQL** is an API Spec Query Analyser that uses CodeQL and a built-in Python analyzer to scan Azure REST API specifications for security vulnerabilities — including SAS URI exposure, Key Vault misconfigurations, missing access control, and exposed credentials.

SpeQL is the engine that feeds **[APISpy](https://github.com/UndREST-Labs/UndREST-APISpy)** — it exports a structured index of every Azure REST API operation, which APISpy uses for real-time request classification in the browser.

> **SilentReaper** is a vulnerability class characterized by an API emitting a SAS URI in its response, which becomes dangerous when combined with improper RBAC or inadequate control/data plane isolation.

## Table of Contents

- [Quick Start with CLI Menu](#quick-start-with-cli-menu)
- [Tools Overview](#tools-overview)
- [Vulnerabilities Detected](#vulnerabilities-detected)
- [Repository Structure](#repository-structure)
- [Multi-Source Architecture](#multi-source-architecture)
- [Smart Memory Management](#smart-memory-management)
- [Installation](#installation)
- [Usage](#usage)
- [Database Management](#database-management)
- [Export Pipeline](#export-pipeline)
- [Query Details](#query-details)
- [Ecosystem](#ecosystem)
- [Contributing](#contributing)
- [License](#license)

## Quick Start with CLI Menu

```bash
# Install dependencies
pip3 install -r requirements.txt

# Launch the interactive CLI menu
python3 SpeQL.py
```

![SpeQL Interactive CLI Menu Demo](demos/05-cli-menu.gif)

The CLI menu provides:
- **Intuitive navigation** - Browse all actions organised by category
- **Interactive prompts** - Step-by-step guidance for complex operations
- **ASCII art logo** - SpeQL branding via figlet (falls back gracefully if not installed)
- **Comprehensive coverage** - Access to all scripts and tools
- **Smart memory management** - Automatic CodeQL memory optimisation for large databases

### CLI Menu Structure

- 📊 **Security Analysis** - Run security scans on Azure API specifications
- 🗄️ **Database Management** - Clone, update, and rebuild the CodeQL database
- 🔍 **CodeQL Security Queries** - Execute CodeQL queries and view results
- 📈 **SARIF Analysis Tools** - Analyse SARIF output for threat hunting
- ⚙️ **Setup and Installation** - Automated setup and dependency management
- 📚 **Documentation and Help** - Access guides and documentation
- ℹ️ **About SpeQL** - Learn about the tool and its capabilities

### Alternative: Direct Command-Line Usage

For automation or scripting, use the individual scripts directly:

```bash
python3 analyze.py          # Run security analysis
python3 refresh_database.py # Update database
./run-queries.sh            # Run CodeQL queries
```

## Tools Overview

| Tool | Entry Point | Description |
|------|-------------|-------------|
| **Interactive CLI** | `SpeQL.py` | Menu-driven interface for all SpeQL actions |
| **Python Security Analyzer** | `analyze.py` | Standalone scanner; no CodeQL required; detects insecure Logic App triggers, Key Vault misconfigs, missing access control, hardcoded credentials |
| **CodeQL Queries** | `queries/azure-security/` | 8 queries detecting SAS URI exposure, exposed tokens, proxy invocation, Logic App secrets, hardcoded ARM secrets, sensitive GET responses, control-plane bypass, and obfuscated secrets |
| **Database Refresh** | `refresh-database.sh` · `refresh_database.py` | Clone and build a CodeQL database from the Azure REST API spec corpus |
| **SARIF Analysis Tools** | `scripts/sarif-analysis/` | Shell scripts for deduplicating, parsing, and prioritising CodeQL findings |
| **Export Pipeline** | `scripts/export/export_api_inventory.py` | Walks the spec corpus and produces a structured JSON index of every Azure REST API operation, published to APISpy via GitHub Releases |

## Vulnerabilities Detected

### 1. Insecure Logic App Trigger

Detects Logic App HTTP triggers that can be invoked without authentication:
- Missing authentication configuration
- Weak authentication (None/Anonymous)
- Public HTTP endpoints without access control

**CWE References**: CWE-306 (Missing Authentication), CWE-862 (Missing Authorization)

### 2. Insecure Key Vault Configuration

Identifies Key Vault misconfigurations that expose secrets:
- Missing network restrictions
- Public network access enabled
- Overly permissive access policies
- Embedded secrets instead of Key Vault references

**CWE References**: CWE-284 (Improper Access Control), CWE-522 (Insufficiently Protected Credentials)

### 3. Missing Access Control

Finds API endpoints without proper security:
- Sensitive operations (DELETE, CREATE, UPDATE) without authentication
- Endpoints with empty security arrays
- Public workflow access without restrictions

**CWE References**: CWE-284, CWE-862

### 4. Insecure Credentials

Locates hardcoded credentials and secrets:
- Connection strings with embedded passwords
- Hardcoded API keys and secrets
- Basic authentication with visible passwords
- Secure strings with default values

**CWE References**: CWE-798 (Hardcoded Credentials), CWE-259 (Hard-coded Password)

### 5. SAS URI Exposure in API Responses (CodeQL) — SilentReaper

The CodeQL query (`SasUriInResponse.ql`) detects Azure Shared Access Signature (SAS) URIs in API example responses:
- SAS tokens in response bodies (`inputsLink`, `outputsLink`, etc.)
- URIs containing signature parameters (`sig`, `se`, `sp`, `sv`)
- Control-plane APIs exposing data-plane access credentials

**Security Impact**: SAS URIs grant time-limited access to Azure resources. When exposed in control-plane API responses with improper RBAC or inadequate control/data plane isolation, they can enable unauthorised data-plane access and data exfiltration. This is the defining characteristic of a SilentReaper vulnerability.

**CWE References**: CWE-200 (Exposure of Sensitive Information), CWE-359

### 6. Exposed SAS Tokens (CodeQL)

The CodeQL query (`ExposedSasTokens.ql`) detects pre-authenticated SAS URIs or tokens in example payloads or JSON strings containing signature material (`sig`, `sv`).

**CWE References**: CWE-200, CWE-522

### 7. Proxy and Dynamic Invocation (CodeQL)

The CodeQL query (`ProxyAndDynamicInvocation.ql`) identifies bridge endpoints in management-plane specs that allow callers to proxy arbitrary requests to backend services, bypassing intended isolation.

**CWE References**: CWE-441, CWE-610

### 8. Missing Logic App Secure Data (CodeQL)

The CodeQL query (`MissingLogicAppSecureData.ql`) detects Logic App workflow definitions where sensitive inputs or outputs are not secured via `runtimeConfiguration.secureData`.

**CWE References**: CWE-312, CWE-532

### 9. Hardcoded Secrets in ARM Templates (CodeQL)

The CodeQL query (`HardcodedSecretsInArm.ql`) detects ARM template parameters typed as `securestring` that include a plaintext default value.

**CWE References**: CWE-312, CWE-798

### 10. Sensitive Data in GET Responses (CodeQL)

The CodeQL query (`SensitiveDataInGetResponse.ql`) flags GET operations that return credential-named properties without `x-ms-secret: true`.

**CWE References**: CWE-200, CWE-359

### 11. Control-Plane Bypass (CodeQL)

The CodeQL query (`ControlPlaneBypass.ql`) scans data-plane specs for resource management operations that should be restricted to the management plane.

**CWE References**: CWE-284, CWE-269

### 12. Base64-Encoded Secrets (CodeQL)

The CodeQL query (`Base64EncodedSecrets.ql`) searches for high-entropy or base64-encoded strings that may mask obfuscated secrets in API examples or schema definitions.

**CWE References**: CWE-312, CWE-522

## Repository Structure

```
UndREST-SpecQL/
├── README.md
├── CONTRIBUTING.md
├── LICENSE
├── SpeQL.py                     # Interactive CLI menu entry point
├── setup.sh                     # Automated setup script
├── refresh-database.sh          # Bash script to refresh/clone a spec source and build the DB
├── refresh_database.py          # Python script (same, cross-platform)
├── analyze.py                   # Python-based security analyzer (no CodeQL required)
├── run-queries.sh               # CodeQL query execution script
├── config/
│   ├── SpeQL.yml               # CodeQL database configuration
│   └── sources/                # Source registry — one JSON file per API spec source
│       └── azure.json          # Azure REST API Specifications source definition
├── database/                   # CodeQL database(s) (generated)
│   └── azure-api-db/
├── demos/                      # Demo GIFs (01–07)
├── docs/                       # Documentation
│   ├── ADDING_API_SOURCES.md   # Guide for adding new API spec sources
│   ├── CODEQL_WORKFLOW.md
│   ├── DATABASE_REFRESH.md
│   ├── EXAMPLE_OUTPUT.md
│   ├── MEMORY_MANAGEMENT.md
│   ├── QUICKSTART.md
│   ├── QUICK_REFERENCE.md
│   ├── REPOSITORY_STRUCTURE.md
│   ├── SARIF_ANALYSIS_QUICKSTART.md
│   └── inventory/
│       ├── API_INDEX_SCHEMA.md
│       ├── CONSUMER_GUIDE.md
│       └── EXPORT_PIPELINE.md
├── inventory/                  # Export artifacts (generated)
│   └── api-index-sharded-<run-id>.zip
├── queries/                    # CodeQL queries — one subdirectory per platform
│   ├── README.md               # How to add queries for a new platform
│   └── azure-security/
│       ├── SasUriInResponse.ql          # Detects SAS URIs in API example responses
│       ├── ExposedSasTokens.ql          # Detects pre-authenticated SAS tokens in example payloads
│       ├── ProxyAndDynamicInvocation.ql # Identifies bridge endpoints enabling cross-service access
│       ├── MissingLogicAppSecureData.ql # Detects Logic App workflows without secure data settings
│       ├── HardcodedSecretsInArm.ql     # Detects securestring ARM params with plaintext defaults
│       ├── SensitiveDataInGetResponse.ql # Flags GET responses returning unprotected credential properties
│       ├── ControlPlaneBypass.ql        # Detects management ops exposed on data-plane paths
│       ├── Base64EncodedSecrets.ql      # Detects obfuscated secrets encoded as base64
│       └── qlpack.yml
├── results/                    # Analysis results (generated)
├── scripts/
│   ├── export/                 # API inventory export pipeline
│   │   ├── export_api_inventory.py
│   │   └── normalize_api_inventory.py
│   └── sarif-analysis/         # SARIF analysis and threat hunting tools
│       ├── deduplicate-by-product-operation.sh
│       ├── parse-sarif-endpoints.sh
│       ├── prioritize-threats.sh
│       └── README.md
├── tests/
│   ├── test_api_inventory_export.py
│   ├── test_api_inventory_normalization.py
│   ├── test_json_file_count_fix.sh
│   ├── test_memory_management.sh
│   └── vhs/                    # VHS tape recordings for animated GIF demos (01–07)
└── utils/
    └── memory_utils.sh         # Memory management utilities
```

## Multi-Source Architecture

SpeQL is designed to work with any OpenAPI/Swagger spec corpus, not just
`azure-rest-api-specs`.  Adding support for a new API platform requires only:

1. **A source config file** (`config/sources/<platform>.json`) — declares the
   upstream repository URL, local directory names, and metadata.
2. **Optionally, platform-specific CodeQL queries** (`queries/<platform>-security/`).

All scripts and workflows accept a `--source-config` flag:

```bash
# Refresh using a custom source
python3 refresh_database.py --source-config config/sources/my-platform.json --all --skip-db-build

# Export API inventory for a custom source
python3 scripts/export/export_api_inventory.py \
  --source my-platform-api-specs/specification \
  --source-repo MyOrg/my-platform-api-specs
```

See [docs/ADDING_API_SOURCES.md](docs/ADDING_API_SOURCES.md) for the complete guide.



SpeQL includes intelligent memory management for CodeQL query execution.

- **Automatic Detection**: Detects total system memory on Linux and macOS
- **Smart Optimisation**: Applies memory limits (90% of total RAM) for databases with >50K JSON files
- **Manual Override**: Set custom limits via `CODEQL_MEMORY_LIMIT` environment variable

```bash
./run-queries.sh                          # Automatic
export CODEQL_MEMORY_LIMIT=4096 && ./run-queries.sh  # Manual
```

For detailed information, see [docs/MEMORY_MANAGEMENT.md](docs/MEMORY_MANAGEMENT.md).

## Installation

### Quick Setup (Recommended)

```bash
./setup.sh
```

![Setup and Installation Demo](demos/01-setup.gif)

This installs Java Development Kit, CodeQL CLI 2.20.2, and all required CodeQL query pack dependencies.

### Manual Installation

#### 1. Java Development Kit (JDK)

```bash
# Ubuntu/Debian
sudo apt-get install openjdk-17-jdk
java -version
```

#### 2. CodeQL CLI

> **Important**: CodeQL 2.23.x+ has compatibility issues with JSON-only databases. Use **2.20.1 or 2.20.2**.

```bash
wget https://github.com/github/codeql-cli-binaries/releases/download/v2.20.2/codeql-linux64.zip
unzip codeql-linux64.zip
export PATH="$PATH:$(pwd)/codeql"

# Install query pack dependencies
cd queries/azure-security && codeql pack install && cd ../..

codeql version
./run-queries.sh
```

#### 3. Python Dependencies

```bash
pip3 install -r requirements.txt
```

## Usage

### Python Analyzer

```bash
python3 analyze.py
```

![Python Security Analyzer Demo](demos/03-python-analyzer.gif)

```bash
# Verbose mode
python3 analyze.py --verbose

# Specific Azure service
python3 analyze.py --source azure-rest-api-specs/specification/keyvault

# All Azure services (after cloning with --all)
python3 analyze.py --source azure-rest-api-specs/specification
```

### CodeQL Queries

![CodeQL Security Queries Demo](demos/04-codeql-queries.gif)

```bash
# Build database then run queries
python3 refresh_database.py --path specification/keyvault --fresh
./run-queries.sh
```

Results are saved in SARIF format in `results/` and can be viewed in VS Code (SARIF Viewer extension) or uploaded to GitHub Advanced Security.

### SARIF Analysis for Threat Hunting

![SARIF Analysis Tools Demo](demos/06-sarif-analysis.gif)

```bash
# Deduplicate findings
./scripts/sarif-analysis/deduplicate-by-product-operation.sh results/SasUriInResponse-results.sarif

# Extract structured endpoint data as CSV
./scripts/sarif-analysis/parse-sarif-endpoints.sh -f csv results/SasUriInResponse-results.sarif

# Prioritise by severity
./scripts/sarif-analysis/prioritize-threats.sh --threshold high results/SasUriInResponse-results.sarif
```

See [scripts/sarif-analysis/README.md](scripts/sarif-analysis/README.md) for full documentation.

## Database Management

```bash
# Update and rebuild (default: Azure Logic Apps)
./refresh-database.sh

# Use a specific source config
./refresh-database.sh --source-config config/sources/azure.json

# Fresh clone
./refresh-database.sh --fresh

# Specific service path within the source
./refresh-database.sh --path specification/keyvault

# All specifications in the source
./refresh-database.sh --all

# Repo only (no CodeQL build)
./refresh-database.sh --skip-db-build
```

![Database Refresh Demo](demos/02-database-refresh.gif)

For full documentation, see [docs/DATABASE_REFRESH.md](docs/DATABASE_REFRESH.md).
To add a new API source, see [docs/ADDING_API_SOURCES.md](docs/ADDING_API_SOURCES.md).

## Export Pipeline

The export pipeline walks any OpenAPI/Swagger spec directory and produces a structured JSON index of every REST API operation.

```bash
# Azure (default)
python3 scripts/export/export_api_inventory.py \
  --source azure-rest-api-specs/specification \
  --output-dir inventory/ \
  --sharded --minified --verbose

# Custom source
python3 scripts/export/export_api_inventory.py \
  --source my-platform-api-specs/specification \
  --source-repo MyOrg/my-platform-api-specs \
  --output-dir inventory/ \
  --sharded --minified --verbose
```

**Output formats:**
- `api-index.json` — Flat pretty-printed index
- `api-index-grouped.json` — Grouped/deduplicated (schema 3.0.0)
- `shards/{Provider.Namespace}.min.json` — Per-provider shards for APISpy

**Cross-repo pipeline:** The `daily-api-index-export-sharded.yml` workflow runs nightly, publishes the sharded zip to the `shards-latest` GitHub Release, and triggers [UndREST-APISpy](https://github.com/UndREST-Labs/UndREST-APISpy) to update its extension shard data automatically.

See [docs/inventory/EXPORT_PIPELINE.md](docs/inventory/EXPORT_PIPELINE.md) for the full schema and consumer guide.

## Query Details

### SasUriInResponse.ql

| Attribute | Value |
|-----------|-------|
| **ID** | `azure/sas-uri-in-response` |
| **Severity** | Error |
| **Security Severity** | 8.5 |
| **Precision** | High |
| **CWE** | CWE-200, CWE-359 |

Detects API specs that emit Azure Shared Access Signature (SAS) URIs in API responses. SAS URIs contain sensitive tokens granting time-limited access to Azure resources. This is the defining characteristic of a SilentReaper vulnerability — an API emitting a SAS URI in its response, which becomes dangerous with improper RBAC or inadequate control/data plane isolation.

### ExposedSasTokens.ql

| Attribute | Value |
|-----------|-------|
| **ID** | `azure/exposed-sas-tokens` |
| **Severity** | Error |
| **Security Severity** | 8.5 |
| **Precision** | High |
| **CWE** | CWE-200, CWE-522 |

Detects pre-authenticated SAS URIs or tokens found in example payloads or JSON strings. These contain sensitive signature material (`sig`, `sv`) along with scope or expiry parameters that, if exposed, can grant unauthorized access to Azure resources.

### ProxyAndDynamicInvocation.ql

| Attribute | Value |
|-----------|-------|
| **ID** | `azure/proxy-dynamic-invocation` |
| **Severity** | Warning |
| **Security Severity** | 7.5 |
| **Precision** | Medium |
| **CWE** | CWE-441, CWE-610 |

Identifies "bridge" endpoints in management-plane specs that allow callers to proxy arbitrary requests to backend services, potentially bypassing intended isolation and enabling unauthorized cross-service access.

### MissingLogicAppSecureData.ql

| Attribute | Value |
|-----------|-------|
| **ID** | `azure/missing-logic-app-secure-data` |
| **Severity** | Error |
| **Security Severity** | 7.0 |
| **Precision** | Medium |
| **CWE** | CWE-312, CWE-532 |

Detects Logic App workflow definitions where sensitive inputs or outputs are not secured via `runtimeConfiguration.secureData`, potentially exposing secrets in run history and execution logs.

### HardcodedSecretsInArm.ql

| Attribute | Value |
|-----------|-------|
| **ID** | `azure/hardcoded-secrets-arm` |
| **Severity** | Error |
| **Security Severity** | 9.0 |
| **Precision** | High |
| **CWE** | CWE-312, CWE-798 |

Detects ARM template parameters typed as `securestring` that inadvertently include a plaintext default value. Such defaults are stored in cleartext in deployment logs and template history, defeating the purpose of the secure type.

### SensitiveDataInGetResponse.ql

| Attribute | Value |
|-----------|-------|
| **ID** | `azure/sensitive-data-in-get-response` |
| **Severity** | Error |
| **Security Severity** | 8.0 |
| **Precision** | Medium |
| **CWE** | CWE-200, CWE-359 |

Flags GET operations that return properties whose names suggest credentials (keys, tokens, secrets, passwords, connection strings) but are not annotated with the mandatory `x-ms-secret: true` extension, risking unintended exposure of sensitive data.

### ControlPlaneBypass.ql

| Attribute | Value |
|-----------|-------|
| **ID** | `azure/control-plane-bypass` |
| **Severity** | Warning |
| **Security Severity** | 7.0 |
| **Precision** | Low |
| **CWE** | CWE-284, CWE-269 |

Scans data-plane specifications for resource management operations (e.g., creating deployments, accounts, or configurations) that should typically be restricted to the management plane. Such paths may enable unauthorized resource lifecycle control.

### Base64EncodedSecrets.ql

| Attribute | Value |
|-----------|-------|
| **ID** | `azure/base64-encoded-secret` |
| **Severity** | Warning |
| **Security Severity** | 6.5 |
| **Precision** | Low |
| **CWE** | CWE-312, CWE-522 |

Searches for high-entropy strings or fields explicitly formatted as base64-encoded bytes that may mask obfuscated secrets within API examples or schema definitions.

## Ecosystem

SpeQL is part of the [UndREST Labs](https://github.com/UndREST-Labs) ecosystem:

| Project | Repo | Description |
|---------|------|-------------|
| **SpeQL** | *(this repo)* | Query and reason about API behaviour; the engine that feeds APISpy |
| **APISpy** | [UndREST-APISpy](https://github.com/UndREST-Labs/UndREST-APISpy) | Real-time visibility into API calls in the browser; powered by SpeQL exports |
| **Atlas** | *(future)* | Mapping API ecosystems at scale |

> **Observe → Understand → Map → Evolve**

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on adding new security queries, improving existing ones, and contributing to the export pipeline.

For APISpy (extension, portal sweep, shard preparation), see [UndREST-APISpy](https://github.com/UndREST-Labs/UndREST-APISpy).

## License

See [LICENSE](LICENSE).
