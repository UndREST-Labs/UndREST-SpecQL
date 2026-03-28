# SpeQL Analysis Example Output

This document shows example output from running the SpeQL Python analyzer on Azure REST API specifications.

## Running the Python Analyzer

The Python analyzer (analyze.py) detects security vulnerabilities in API schema files without requiring CodeQL.

```bash
$ python3 analyze.py
════════════════════════════════════════════════════════════
  SpeQL - API Spec Query Analyser
  Identifying SilentReaper vulnerabilities in Azure REST API
════════════════════════════════════════════════════════════

Analyzing 309 JSON files...

✗ Found 16 security issue(s):

Errors: 16
[ERROR] Sensitive Operation Without Authentication
  File: c/GitHub/azure-rest-api-specs/specification/logic/resource-manager/Microsoft.Logic/preview/2015-08-01-preview/logic.json
  Sensitive operation 'IntegrationAccounts_CreateOrUpdate' missing security requirements

[ERROR] Sensitive Operation Without Authentication
  File: c/GitHub/azure-rest-api-specs/specification/logic/resource-manager/Microsoft.Logic/preview/2015-08-01-preview/logic.json
  Sensitive operation 'IntegrationAccounts_Delete' missing security requirements

[ERROR] Key Vault Without Network Restrictions
  File: c/GitHub/azure-rest-api-specs/specification/logic/resource-manager/Microsoft.Logic/preview/2018-07-01-preview/examples/IntegrationAccounts_ListKeyVaultKeys.json
  Key Vault configuration missing network restrictions, allowing access from any network

════════════════════════════════════════════════════════════
Total issues: 16
════════════════════════════════════════════════════════════
```

## Issue Categories Found

### 1. Missing Authentication on Sensitive Operations (13 issues)

These are critical issues where API operations that modify or delete resources lack security requirements. This allows unauthorized users to perform destructive actions.

**Affected Operations:**
- IntegrationAccounts_CreateOrUpdate
- IntegrationAccounts_Update
- IntegrationAccounts_Delete
- IntegrationAccountSchemas_CreateOrUpdate
- IntegrationAccountSchemas_Delete
- IntegrationAccountMaps_CreateOrUpdate
- IntegrationAccountMaps_Delete
- IntegrationAccountPartners_CreateOrUpdate
- IntegrationAccountPartners_Delete
- IntegrationAccountAgreements_CreateOrUpdate
- IntegrationAccountAgreements_Delete
- IntegrationAccountCertificates_CreateOrUpdate
- IntegrationAccountCertificates_Delete

**Security Impact:**
- Unauthorized resource creation/modification
- Potential data loss through unauthorized deletions
- Bypass of authentication requirements
- Related to **CWE-862: Missing Authorization**

### 2. Key Vault Without Network Restrictions (3 issues)

Key Vault configurations that don't restrict network access, potentially allowing attackers to enumerate or access secrets from any location.

**Affected Files:**
- IntegrationAccounts_ListKeyVaultKeys.json (multiple API versions)

**Security Impact:**
- Secrets accessible from any network
- Increased attack surface for credential theft
- No defense against network-based attacks
- Related to **Azure Vault Recon** vulnerability pattern
- Related to **CWE-284: Improper Access Control**

## Remediation Recommendations

### For Missing Authentication Issues:

Add security requirements to sensitive operations in the Swagger specification:

```json
{
  "paths": {
    "/resource/{id}": {
      "delete": {
        "operationId": "Resource_Delete",
        "security": [
          {
            "azure_auth": ["user_impersonation"]
          }
        ]
      }
    }
  }
}
```

### For Key Vault Network Restrictions:

Configure network ACLs for Key Vaults:

```json
{
  "properties": {
    "networkAcls": {
      "defaultAction": "Deny",
      "bypass": "AzureServices",
      "ipRules": [
        {"value": "trusted-ip-range"}
      ],
      "virtualNetworkRules": [
        {"id": "/subscriptions/.../virtualNetworks/.../subnets/..."}
      ]
    },
    "publicNetworkAccess": "Disabled"
  }
}
```

## Continuous Integration

Use SpeQL in your CI/CD pipeline:

```yaml
# .github/workflows/security-scan.yml
name: Security Scan

on: [push, pull_request]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run SpeQL Security Analysis
        run: python3 analyze.py
```

The script exits with code 1 if issues are found, causing the build to fail.

## CodeQL Query: SasUriInResponse

In addition to the Python analyzer, SpeQL includes a CodeQL query specifically for detecting SAS URIs in API example response files:

```bash
# Run the CodeQL query
./run-queries.sh
```

This query is particularly useful because:
- API schema files don't contain actual SAS URIs with signature tokens
- Only API example response files contain real SAS URIs
- CodeQL database scanning is ideal for finding these in example outputs

Example findings would show locations of SAS URIs like:
```
https://example.blob.core.windows.net/container/file?sig=SIGNATURE&se=EXPIRY&sp=PERMISSIONS
```

## References

- SilentReaper Vulnerability: APIs emitting SAS URIs in responses with improper RBAC or inadequate control/data plane isolation
- Azure Vault Recon: Key Vault enumeration attacks
- CWE-306: Missing Authentication for Critical Function
- CWE-862: Missing Authorization
- CWE-284: Improper Access Control
- CWE-522: Insufficiently Protected Credentials
- CWE-200: Exposure of Sensitive Information to an Unauthorized Actor
- CWE-359: Exposure of Private Personal Information to an Unauthorized Actor
