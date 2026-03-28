# SARIF Analysis Scripts for Threat Hunting

This directory contains specialized scripts for analyzing SARIF output files from Azure REST API security scans. These tools are designed for threat hunting, focusing on SilentReaper vulnerabilities - where APIs emit SAS URIs in responses combined with improper RBAC or inadequate control plane/data plane isolation.

## Overview

The scripts help security researchers and threat hunters to:
- **Deduplicate** results by product and operation, ignoring API versions
- **Parse** SARIF files to extract structured API endpoint data
- **Prioritize** findings based on control plane/data plane isolation risks
- **Analyze** patterns across multiple API versions to identify systemic issues

## Scripts

### 1. deduplicate-by-product-operation.sh

Removes duplicate findings across different API versions to identify unique vulnerable patterns.

**Purpose:** API vulnerabilities often exist across multiple versions. This script helps identify the unique product+operation combinations that have issues, regardless of version.

**Usage:**
```bash
# Basic deduplication
./deduplicate-by-product-operation.sh results/SasUriInResponse-results.sarif

# Save to file with statistics
./deduplicate-by-product-operation.sh -v -o deduplicated.txt results/SasUriInResponse-results.sarif

# Show grouped results by product
./deduplicate-by-product-operation.sh -f grouped results/SasUriInResponse-results.sarif

# Show summary statistics only
./deduplicate-by-product-operation.sh -f summary results/SasUriInResponse-results.sarif
```

**Output Formats:**
- `unique` (default): List of unique product/operation combinations
- `grouped`: Results grouped by product with operations listed
- `summary`: Statistical summary with counts

**Example Output:**
```
Microsoft.Storage/blob
Microsoft.Storage/queue
Microsoft.Logic/workflows
Microsoft.Compute/virtualmachines
```

### 2. parse-sarif-endpoints.sh

Extracts detailed API endpoint information from SARIF files in multiple formats.

**Purpose:** Convert SARIF results into structured data for further analysis, reporting, or integration with other tools.

**Usage:**
```bash
# Display as table (default)
./parse-sarif-endpoints.sh results/SasUriInResponse-results.sarif

# Export to CSV for Excel/spreadsheet analysis
./parse-sarif-endpoints.sh -f csv -o endpoints.csv results/SasUriInResponse-results.sarif

# Export to JSON for automation
./parse-sarif-endpoints.sh -f json -o endpoints.json results/SasUriInResponse-results.sarif

# Include line numbers and messages
./parse-sarif-endpoints.sh --include-lines --include-messages results/SasUriInResponse-results.sarif

# Process multiple SARIF files
for file in results/*.sarif; do
    ./parse-sarif-endpoints.sh -f csv "$file" >> all-endpoints.csv
done
```

**Output Formats:**
- `table`: Human-readable formatted table
- `csv`: Comma-separated values for spreadsheet tools
- `json`: Structured JSON for automation/scripting

**Example CSV Output:**
```csv
Product,Operation,Version,Stability,File
Microsoft.Storage,blob,2021-09-01,stable,specification/storage/.../blob.json
Microsoft.Storage,queue,2021-09-01,stable,specification/storage/.../queue.json
```

### 3. prioritize-threats.sh

Analyzes and prioritizes findings based on control plane/data plane isolation risks.

**Purpose:** Focus on the most critical vulnerabilities first. Identifies SilentReaper vulnerabilities where control plane APIs expose data plane access credentials (SAS URIs in responses with improper RBAC or inadequate control/data plane isolation).

**Usage:**
```bash
# Show all prioritized results
./prioritize-threats.sh results/SasUriInResponse-results.sarif

# Show only critical and high priority
./prioritize-threats.sh --threshold high results/SasUriInResponse-results.sarif

# Generate markdown threat report
./prioritize-threats.sh -f markdown -o threat-report.md results/SasUriInResponse-results.sarif

# Analyze with detailed statistics
./prioritize-threats.sh -v results/SasUriInResponse-results.sarif
```

**Priority Levels:**

| Level | Description | Examples |
|-------|-------------|----------|
| **CRITICAL** | Direct SAS token exposure in control plane APIs | Storage management APIs exposing blob SAS tokens; Logic Apps management exposing workflow tokens |
| **HIGH** | Control plane APIs with data plane access patterns | ARM APIs for Compute, KeyVault, or Storage that may leak credentials |
| **MEDIUM** | APIs with potential isolation issues | Data plane APIs with token/credential exposure |
| **LOW** | General security concerns requiring review | Other findings not matching high-risk patterns |

**Output Formats:**
- `table`: Color-coded priority table
- `json`: Structured JSON with priority and threat descriptions
- `markdown`: Detailed threat hunting report

**Example Output:**
```
═══════════════════════════════════════════════════════════════════════════════════════════
Priority    Product                Operation        Version          Threat Pattern
───────────────────────────────────────────────────────────────────────────────────────────
CRITICAL    Microsoft.Storage      blob             2021-09-01       Control plane API exposes SAS tokens
HIGH        Microsoft.Logic        workflows        2019-05-01       Control plane API may expose tokens
MEDIUM      Microsoft.Compute      disks            2021-12-01       Potential credential exposure
═══════════════════════════════════════════════════════════════════════════════════════════
```

## Common Workflows

### Threat Hunting Workflow

1. **Run CodeQL Analysis:**
   ```bash
   ./run-queries.sh
   ```

2. **Identify Unique Vulnerable Patterns:**
   ```bash
   ./scripts/sarif-analysis/deduplicate-by-product-operation.sh \
       -f grouped results/SasUriInResponse-results.sarif
   ```

3. **Prioritize Critical Threats:**
   ```bash
   ./scripts/sarif-analysis/prioritize-threats.sh \
       --threshold high -v results/SasUriInResponse-results.sarif
   ```

4. **Generate Detailed Report:**
   ```bash
   ./scripts/sarif-analysis/prioritize-threats.sh \
       -f markdown -o threat-report.md results/SasUriInResponse-results.sarif
   ```

### Bulk Analysis Workflow

Analyze multiple SARIF files and consolidate results:

```bash
# Create output directory
mkdir -p analysis-output

# Process each SARIF file
for sarif in results/*.sarif; do
    name=$(basename "$sarif" .sarif)
    
    # Extract unique patterns
    ./scripts/sarif-analysis/deduplicate-by-product-operation.sh \
        -o "analysis-output/${name}-unique.txt" "$sarif"
    
    # Parse to CSV
    ./scripts/sarif-analysis/parse-sarif-endpoints.sh \
        -f csv -o "analysis-output/${name}-endpoints.csv" "$sarif"
    
    # Prioritize threats
    ./scripts/sarif-analysis/prioritize-threats.sh \
        -f json -o "analysis-output/${name}-priorities.json" "$sarif"
done

# Combine all unique patterns
cat analysis-output/*-unique.txt | sort -u > analysis-output/all-unique-patterns.txt

# Generate combined threat report
./scripts/sarif-analysis/prioritize-threats.sh \
    -f markdown results/*.sarif > analysis-output/combined-threat-report.md
```

### Cross-Version Analysis

Compare findings across different API versions:

```bash
# Extract unique patterns (version-agnostic)
./scripts/sarif-analysis/deduplicate-by-product-operation.sh \
    results/SasUriInResponse-results.sarif > unique-patterns.txt

# Extract detailed endpoint data (version-specific)
./scripts/sarif-analysis/parse-sarif-endpoints.sh \
    -f csv results/SasUriInResponse-results.sarif > all-versions.csv

# Compare: How many versions have the same issue?
awk -F',' 'NR>1 {count[$1"/"$2]++} END {for (k in count) print k, count[k]}' \
    all-versions.csv | sort -k2 -rn
```

## Dependencies

All scripts require:
- **jq** (>= 1.6): JSON processor for parsing SARIF files
  ```bash
  # Install on Ubuntu/Debian
  sudo apt-get install jq
  
  # Install on macOS
  brew install jq
  
  # Install on Windows (WSL)
  sudo apt-get install jq
  ```

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Threat Hunting Analysis

on:
  schedule:
    - cron: '0 0 * * 0'  # Weekly
  workflow_dispatch:

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Run CodeQL Queries
        run: ./run-queries.sh
      
      - name: Prioritize Threats
        run: |
          ./scripts/sarif-analysis/prioritize-threats.sh \
            --threshold high \
            -f markdown \
            -o threat-report.md \
            results/SasUriInResponse-results.sarif
      
      - name: Upload Threat Report
        uses: actions/upload-artifact@v3
        with:
          name: threat-report
          path: threat-report.md
```

### Jenkins Pipeline Example

```groovy
pipeline {
    agent any
    
    stages {
        stage('Run Security Analysis') {
            steps {
                sh './run-queries.sh'
            }
        }
        
        stage('Threat Hunting') {
            steps {
                sh '''
                    mkdir -p reports
                    ./scripts/sarif-analysis/prioritize-threats.sh \
                        -f markdown \
                        -o reports/threat-report.md \
                        results/*.sarif
                '''
            }
        }
        
        stage('Publish Reports') {
            steps {
                publishHTML([
                    reportDir: 'reports',
                    reportFiles: 'threat-report.md',
                    reportName: 'Threat Hunting Report'
                ])
            }
        }
    }
}
```

## Understanding SARIF Files

SARIF (Static Analysis Results Interchange Format) is a standard format for static analysis tools. The structure relevant to these scripts:

```json
{
  "runs": [{
    "results": [{
      "ruleId": "azure/sas-uri-in-response",
      "message": {"text": "Found SAS URI..."},
      "locations": [{
        "physicalLocation": {
          "artifactLocation": {
            "uri": "specification/storage/.../blob.json"
          },
          "region": {"startLine": 100}
        }
      }]
    }]
  }]
}
```

## Threat Hunting Tips

1. **Focus on Critical Findings First:** Use `--threshold critical` to identify the most severe issues
2. **Look for Patterns:** Deduplicate to find systemic issues across API versions
3. **Cross-Reference:** Compare findings across different Azure services
4. **Version Analysis:** Check if issues persist in newer API versions
5. **Control Plane Focus:** Prioritize ARM/management APIs that expose data plane tokens

## Contributing

When adding new analysis capabilities:
1. Follow the existing script structure and argument patterns
2. Add comprehensive help text with examples
3. Support multiple output formats (json, csv, table, markdown)
4. Include verbose mode for debugging
5. Handle edge cases gracefully
6. Update this README with new functionality

## References

- [Azure SilentReaper Vulnerability](https://cirriustech.co.uk/blog/azure-silent-reaper/)
- [SARIF Specification](https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html)
- [Azure REST API Specifications](https://github.com/Azure/azure-rest-api-specs)
- [jq Manual](https://jqlang.github.io/jq/manual/)

## License

See the main LICENSE file in the repository root.
