# SpeQL Quick Reference Guide

## 🚀 Quick Start

```bash
# Run security analysis (Python - no dependencies!)
python3 analyze.py

# Expected output: List of security vulnerabilities found
# Exit code: 0 = no issues, 1 = issues found
```

## 🎯 Analysis Modes

### Database Mode (Default - Fastest)
```bash
# Analyze from pre-built database (~309 files for Logic Apps)
python3 analyze.py

# Show detailed diagnostics
python3 analyze.py --verbose
```

### Direct Repository Analysis
```bash
# Analyze full Azure specifications (~253,543 files)
python3 analyze.py --source azure-rest-api-specs/specification

# Analyze specific service
python3 analyze.py --source azure-rest-api-specs/specification/keyvault
python3 analyze.py --source azure-rest-api-specs/specification/compute

# Analyze custom directory
python3 analyze.py --source /path/to/specs
```

**Note**: First clone the repository to analyze it directly:
```bash
python3 refresh_database.py --all --skip-db-build
```

## 🔄 Database Refresh

```bash
# Update database with latest Azure specs
./refresh-database.sh --update

# Fresh clone and rebuild
./refresh-database.sh --fresh

# Build for specific service (e.g., Key Vault)
./refresh-database.sh --path specification/keyvault --fresh

# Build for all Azure services (for comprehensive CodeQL analysis)
./refresh-database.sh --all --fresh

# See DATABASE_REFRESH.md for detailed documentation
```

## 🔍 CodeQL Workflow

**For running custom CodeQL queries**, build the database with your desired scope:

```bash
# 1. Build database with the service you want to analyze
python3 refresh_database.py --path specification/keyvault --fresh

# 2. Run CodeQL queries against that database
./run-queries.sh

# 3. (Optional) Also run Python analyzer
python3 analyze.py
```

The database path matters for CodeQL! Build it with the specifications you want to query.

## 🎯 What Does SpeQL Detect?

### Python Analyzer (analyze.py)
The Python analyzer detects the following vulnerability types in API schema files:

### 1. Insecure Logic App Trigger Patterns
**Issue**: Logic App triggers without proper authentication
**Risk**: Unauthorized workflow execution
**Example**: HTTP triggers with missing or weak authentication

### 2. Azure Vault Recon Vulnerabilities
**Issue**: Key Vault misconfigurations
**Risk**: Secret enumeration and unauthorized access
**Example**: Key Vaults without network restrictions

### 3. Missing Access Control
**Issue**: API endpoints lacking authentication
**Risk**: Unauthorized resource operations
**Example**: DELETE/CREATE operations without security

### 4. Insecure Credentials
**Issue**: Hardcoded secrets in configurations
**Risk**: Credential exposure and theft
**Example**: Connection strings with embedded passwords

### CodeQL Queries (run-queries.sh)

### 5. SAS URI Exposure (`SasUriInResponse.ql`) — SilentReaper Vulnerability Indicator
**Issue**: Azure SAS tokens exposed in API example responses
**Risk**: Unauthorized data-plane access and data exfiltration
**Example**: Response URIs containing signature parameters (sig, se, sp)
**Note**: This query scans API example files where actual SAS URIs appear, not schema definitions

### 6. Exposed SAS Tokens (`ExposedSasTokens.ql`)
**Issue**: Pre-authenticated SAS URIs or tokens in example payloads
**Risk**: Unauthorized access to Azure resources via leaked signature material
**Example**: JSON strings containing `sig=` and `sv=` parameters

### 7. Proxy and Dynamic Invocation (`ProxyAndDynamicInvocation.ql`)
**Issue**: Bridge endpoints in management-plane specs enabling arbitrary proxying
**Risk**: Unauthorized cross-service access bypassing intended isolation
**Example**: Management APIs with backend proxy affordances

### 8. Missing Logic App Secure Data (`MissingLogicAppSecureData.ql`)
**Issue**: Logic App workflows without `runtimeConfiguration.secureData`
**Risk**: Secrets exposed in run history and execution logs
**Example**: Logic App actions passing credentials without secure data settings

### 9. Hardcoded Secrets in ARM (`HardcodedSecretsInArm.ql`)
**Issue**: ARM `securestring` parameters with plaintext default values
**Risk**: Credentials stored in cleartext in deployment logs and template history
**Example**: `"defaultValue": "MyPassword123"` on a securestring parameter

### 10. Sensitive Data in GET Response (`SensitiveDataInGetResponse.ql`)
**Issue**: GET operations returning credential properties without `x-ms-secret: true`
**Risk**: Unintended exposure of secrets, keys, or tokens via read operations
**Example**: GET response schema with `password`, `key`, or `token` properties

### 11. Control-Plane Bypass (`ControlPlaneBypass.ql`)
**Issue**: Resource management operations exposed on data-plane paths
**Risk**: Unauthorized resource lifecycle control bypassing management-plane controls
**Example**: Data-plane specs defining deployment or account creation endpoints

### 12. Base64-Encoded Secrets (`Base64EncodedSecrets.ql`)
**Issue**: High-entropy or base64-encoded strings that may mask obfuscated secrets
**Risk**: Credential exposure hidden by encoding
**Example**: Fields explicitly typed as base64-encoded bytes in API examples or schemas

## 📊 Understanding the Output

### Error Severity Levels

```
[ERROR]   - Critical security issue requiring immediate attention
[WARNING] - Potential security concern requiring review
```

### Sample Output

```
[ERROR] Sensitive Operation Without Authentication
  File: logic.json
  Sensitive operation 'Resource_Delete' missing security requirements
```

## 🔧 Usage Scenarios

### Local Development
```bash
# Check your API specs before committing
python3 analyze.py
```

### CI/CD Pipeline
```yaml
# GitHub Actions
- name: Security Scan
  run: python3 analyze.py
```

### Pre-commit Hook
```bash
#!/bin/bash
cd /path/to/SpeQL
python3 analyze.py || exit 1
```

## 🛠️ Advanced Usage

### CodeQL Analysis (requires CodeQL CLI)
```bash
# Run all security queries
./run-queries.sh

# Run specific query
codeql database analyze database/azure-api-db \
    queries/azure-security/SasUriInResponse.ql \
    --format=sarif-latest \
    --output=results/output.sarif
```

### Filtering Results
```bash
# Show only errors (not warnings)
python3 analyze.py 2>&1 | grep "\[ERROR\]"

# Count issues found
python3 analyze.py 2>&1 | grep -c "\[ERROR\]"
```

## 📋 Common Issues and Solutions

### Issue: "Azure API specifications not found"
**Solution**: Run from the SpeQL root directory where `database/` exists

### Issue: "Permission denied"
**Solution**: Make scripts executable
```bash
chmod +x analyze.py run-queries.sh
```

### Issue: False positives detected
**Solution**: Review the specific file and location. The tool follows security best practices - if authentication is truly not needed, document the exception.

## 🔍 Interpreting Results

### Sensitive Operations Without Authentication
- **What**: API operations that modify data lack auth requirements
- **Why it matters**: Allows unauthorized users to alter/delete resources
- **Fix**: Add security requirements to the Swagger spec

### Key Vault Without Network Restrictions
- **What**: Key Vault accessible from any network
- **Why it matters**: Increases attack surface for secret theft
- **Fix**: Configure network ACLs with defaultAction: Deny

### Hardcoded Credentials
- **What**: Passwords/keys stored in config files
- **Why it matters**: Credentials may be exposed in source control
- **Fix**: Use Key Vault references instead

### SAS URI Exposure
- **What**: Azure Shared Access Signature tokens in API responses
- **Why it matters**: Grants time-limited access to Azure resources, enabling data exfiltration
- **Fix**: Avoid exposing SAS tokens in control-plane API responses

## 📚 Related CWE Standards

- **CWE-306**: Missing Authentication for Critical Function
- **CWE-862**: Missing Authorization
- **CWE-284**: Improper Access Control
- **CWE-522**: Insufficiently Protected Credentials
- **CWE-798**: Use of Hard-coded Credentials
- **CWE-200**: Exposure of Sensitive Information to an Unauthorized Actor
- **CWE-359**: Exposure of Private Personal Information to an Unauthorized Actor

## 🔗 Additional Resources

- [Azure SilentReaper Vulnerability](https://cirriustech.co.uk/blog/azure-silent-reaper/)
- [Azure Vault Recon Blog](https://cirriustech.co.uk/blog/azure-vault-recon/)
- [Azure Security Best Practices](https://docs.microsoft.com/en-us/azure/security/)
- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)

## 💡 Tips

1. **Run regularly**: Integrate into your development workflow
2. **Review false positives**: Not all findings may apply to your context
3. **Document exceptions**: If authentication isn't needed, document why
4. **Update regularly**: Pull latest queries for new vulnerability patterns
5. **Combine with other tools**: Use alongside Azure Security Center, Defender

## ❓ Getting Help

- Check EXAMPLE_OUTPUT.md for detailed examples
- Review README.md for comprehensive documentation
- Open an issue on GitHub for bugs or feature requests

---

## 🔭 APISpy — DevTools Extension

### Load the extension

1. Open **chrome://extensions** (or **edge://extensions**) and enable **Developer mode**.
2. Click **Load unpacked** and select `apispy/extension/`.
3. Open DevTools (**F12**) on any page — look for the **APISpy** tab.

### Run APISpy tests
```bash
# From the repository root (Node.js required, no extra packages)
node apispy/tests/test_filters.js
node apispy/tests/test_normalizer.js
node apispy/tests/test_matcher.js
```

### Re-bundle provider shards
```bash
# Populate from a SpecRecon zip export (all shards, no size limit)
python3 apispy/scripts/prepare_data.py --zip inventory/api-index-sharded-<run-id>.zip

# Optional: exclude shards larger than N KB
python3 apispy/scripts/prepare_data.py --zip inventory/api-index-sharded-<run-id>.zip --size-limit 100
```

Reload the unpacked extension in Chrome after re-bundling to pick up new data.  
See [apispy/extension/README.md](../apispy/extension/README.md) for full details.
