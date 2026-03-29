# Quick Start Guide for SpeQL CodeQL Queries

## Prerequisites

- Java Development Kit (JDK) 11 or newer
- CodeQL CLI 2.20.2
- Internet connection for downloading dependencies

## Installation (3 Steps)

### Step 1: Clone the Repository
```bash
git clone https://github.com/SpeQLSec/SpeQL.git
cd SpeQL
```

### Step 2: Run Setup Script
```bash
./setup.sh
```

![Setup and Installation Demo](../demos/01-setup.gif)

The script will:
- Install CodeQL CLI if not present
- Download all required query pack dependencies
- Automatically handle SSL certificate errors if they occur
- Verify the installation

**Note**: If you encounter SSL certificate errors, the script will automatically fall back to manual library installation.

### Step 3: Verify Installation
```bash
# Check CodeQL is installed
codeql version

# Check JavaScript libraries are installed
ls ~/.codeql/packages/codeql/javascript-all/
```

## Running Queries

### Option 1: Run All Queries (using CodeQL)
```bash
./run-queries.sh
```

![CodeQL Security Queries Demo](../demos/04-codeql-queries.gif)

### Option 2: Run Python Analyzer (no CodeQL needed)
```bash
python3 analyze.py
```

![Python Security Analyzer Demo](../demos/03-python-analyzer.gif)

## Understanding the Queries

### What Do These Queries Detect?

**Python Analyzer (analyze.py)** - Detects multiple vulnerability types in API schemas:
- Insecure Logic App triggers (missing or weak authentication)
- Key Vault misconfigurations (Azure Vault Recon)
- Missing access control on API endpoints
- Hardcoded credentials and secrets

**CodeQL Queries (`run-queries.sh`)** - Detects security issues across all Azure REST API specs:

1. **SasUriInResponse.ql** — Detects Azure SAS URIs in API example response files. A SilentReaper vulnerability occurs when an API emits a SAS URI in its response, which becomes dangerous with improper RBAC or inadequate control/data plane isolation.
2. **ExposedSasTokens.ql** — Detects pre-authenticated SAS URIs or tokens found in example payloads or JSON strings that contain sensitive signature material (`sig`, `sv`).
3. **ProxyAndDynamicInvocation.ql** — Identifies "bridge" endpoints in management-plane specs that allow callers to proxy arbitrary requests to backend services.
4. **MissingLogicAppSecureData.ql** — Detects Logic App workflow definitions where sensitive inputs or outputs are not secured via `runtimeConfiguration.secureData`.
5. **HardcodedSecretsInArm.ql** — Detects ARM template parameters typed as `securestring` that include a plaintext default value.
6. **SensitiveDataInGetResponse.ql** — Flags GET operations that return credential-named properties (keys, tokens, secrets) not annotated with `x-ms-secret: true`.
7. **ControlPlaneBypass.ql** — Scans data-plane specs for resource management operations that should be restricted to the management plane.
8. **Base64EncodedSecrets.ql** — Searches for high-entropy strings or fields formatted as base64-encoded bytes that may mask obfuscated secrets.

### Query Output

The CodeQL queries produce SARIF format output in the `results/` directory:
```bash
results/
  ├── SasUriInResponse-results.sarif
  ├── ExposedSasTokens-results.sarif
  ├── ProxyAndDynamicInvocation-results.sarif
  ├── MissingLogicAppSecureData-results.sarif
  ├── HardcodedSecretsInArm-results.sarif
  ├── SensitiveDataInGetResponse-results.sarif
  ├── ControlPlaneBypass-results.sarif
  └── Base64EncodedSecrets-results.sarif
```

## Troubleshooting

### Issue: "Could not create access credentials" (SSL Error)

**IMPORTANT**: Do NOT use manual library download! It causes compatibility issues.

**The only reliable solution is to fix SSL certificates:**

```bash
# Solution 1: Update system certificates
sudo update-ca-certificates

# Solution 2: Use newer Java with updated certificates
sudo apt-get install openjdk-17-jdk

# Solution 3: Configure proxy if needed
export HTTPS_PROXY=http://proxy.example.com:8080

# Then retry installation
cd queries/azure-security
codeql pack install .
```

The setup script may offer manual download, but **decline it** (`N`) and fix SSL issues instead.

### Issue: "token recognition error at: '?'"

This means incompatible library versions were installed (usually from manual download).

**Solution:**
```bash
# 1. Remove incompatible libraries
rm -rf ~/.codeql/packages

# 2. Fix SSL certificates (see above)

# 3. Reinstall properly
cd queries/azure-security
codeql pack install .
```

**Root cause**: Libraries from GitHub main branch contain newer syntax (like `?` optional chaining) that CodeQL 2.20.2 cannot parse. This only happens with manual installation.

### Issue: Database not found

This typically indicates a database issue. Ensure:
- Database was created with CodeQL 2.20.x (not 2.23.x or newer)
- JSON files are well-formed
- You've run `./setup.sh` successfully

### Issue: "Could not resolve library path"

Run:
```bash
cd queries/azure-security
codeql pack install .
```

If SSL errors occur, the setup script handles this automatically.

### Issue: Database not found

Create a database first:
```bash
./refresh-database.sh --path specification/logic
```

Or use the Python analyzer which doesn't require a database:
```bash
python3 analyze.py
```

## Advanced Usage

### Running Individual Queries

```bash
cd queries/azure-security
codeql query run SasUriInResponse.ql
```

### Analyzing Specific Azure Services

```bash
# Analyze Logic Apps only
./refresh-database.sh --path specification/logic

# Analyze Key Vault only
./refresh-database.sh --path specification/keyvault

# Analyze all services (takes longer)
./refresh-database.sh --all
```

### Customizing Queries

Queries are located in `queries/azure-security/`. You can:
- Modify existing queries to adjust detection patterns
- Add new predicates for additional checks
- Change severity levels in query metadata

## Getting Help

1. Check the main [README.md](../README.md) for detailed information
2. See troubleshooting section in [README.md](../README.md#troubleshooting)
3. Open an issue on GitHub for bugs or questions

## Common Workflows

### Workflow 1: Quick Analysis with Python
```bash
python3 analyze.py
```
No setup required! Works with existing `src.zip` database.

### Workflow 2: Full CodeQL Analysis
```bash
./setup.sh                    # One-time setup
./refresh-database.sh         # Build database (if needed)
./run-queries.sh             # Run all queries
```

### Workflow 3: Continuous Integration
```bash
# In CI pipeline
./setup.sh
./refresh-database.sh --path specification/logic
./run-queries.sh
# Exit code 1 if issues found
```

## What's Next?

- Review the detected issues in `results/` directory
- Examine false positives and adjust queries if needed
- Integrate into your security scanning pipeline
- Contribute improvements back to the project

## Important Notes

- CodeQL 2.20.x is recommended (2.23.x+ has compatibility issues with JSON-only databases)
- Internet connection required for initial setup
- Approximately 500MB disk space needed for CodeQL and libraries
- Setup script handles most common issues automatically

## Version Information

- **CodeQL CLI**: 2.20.2 (recommended)
- **JavaScript Library**: 0.9.4 (compatible with CodeQL 2.20.2)
- **Query Pack Version**: 1.0.0

For more details, see the full documentation in [README.md](../README.md).
