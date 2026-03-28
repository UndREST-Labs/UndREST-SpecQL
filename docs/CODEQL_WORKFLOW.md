# CodeQL Workflow Guide

## Overview

This guide explains how to use SpeQL for CodeQL-based analysis across different Azure services. The key is to build the database with the specifications you want to analyze, then run CodeQL queries against that database.

## Two Analysis Approaches

SpeQL supports two analysis approaches:

### 1. Python Analyzer (`analyze.py`)
- Fast, lightweight analysis
- No CodeQL required
- Can analyze any directory with `--source`
- Best for: Quick scans, CI/CD pipelines

### 2. CodeQL Queries (`run-queries.sh`)
- Advanced pattern matching
- Custom query language
- Requires CodeQL database
- Best for: Custom queries, complex patterns, research

## CodeQL Workflow

### Step 1: Build Database with Desired Scope

The database determines what CodeQL will analyze. Build it with the specifications you need:

#### For Key Vault Analysis
```bash
python3 refresh_database.py --path specification/keyvault --fresh
```

#### For Compute (VMs, etc.)
```bash
python3 refresh_database.py --path specification/compute --fresh
```

#### For Storage
```bash
python3 refresh_database.py --path specification/storage --fresh
```

#### For All Azure Services (Comprehensive)
```bash
python3 refresh_database.py --all --fresh
```
⚠️ **Warning**: This creates a large database (~5-10 GB) and takes time.

#### For Multiple Specific Services
If you need multiple services but not all, you can specify a parent path:
```bash
# This will include keyvault, compute, storage, etc.
python3 refresh_database.py --path specification --fresh
```

### Step 2: Run CodeQL Queries

After building the database, run your queries:

#### Run All Built-in Queries
```bash
./run-queries.sh
```

This runs:
- SasUriInResponse.ql (detects SAS URIs in API example responses)

#### Run Custom Query
```bash
codeql database analyze database/azure-api-db \
    queries/azure-security/YourCustomQuery.ql \
    --format=sarif-latest \
    --output=results/custom-results.sarif
```

#### Run Query Suite
```bash
codeql database analyze database/azure-api-db \
    queries/azure-security/ \
    --format=sarif-latest \
    --output=results/all-results.sarif
```

### Step 3: View Results

Results are saved in SARIF format in the `results/` directory:
- View in VS Code with SARIF Viewer extension
- Upload to GitHub Advanced Security
- Process with SARIF tools

## Complete Examples

### Example 1: Security Audit of Key Vault Specifications

```bash
# 1. Build database with Key Vault specs
python3 refresh_database.py --path specification/keyvault --fresh

# 2. Run CodeQL security queries
./run-queries.sh

# 3. Check results
ls -lh results/
```

### Example 2: Comprehensive Azure Security Scan

```bash
# 1. Build database with all Azure specs (takes time!)
python3 refresh_database.py --all --fresh

# 2. Run all security queries
./run-queries.sh

# 3. Also run Python analyzer for quick checks
python3 analyze.py

# 4. Review results
cat results/*.sarif | jq '.runs[].results | length'
```

### Example 3: Switching Between Services

```bash
# Analyze Key Vault
python3 refresh_database.py --path specification/keyvault --fresh
./run-queries.sh
mv results results-keyvault

# Analyze Compute
python3 refresh_database.py --path specification/compute --fresh
./run-queries.sh
mv results results-compute

# Compare results
diff -u results-keyvault results-compute
```

### Example 4: Continuous Integration

```yaml
# .github/workflows/security-scan.yml
name: Azure Security Scan

on: [push, pull_request]

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Install CodeQL
        run: |
          wget https://github.com/github/codeql-cli-binaries/releases/latest/download/codeql-linux64.zip
          unzip codeql-linux64.zip
          echo "$PWD/codeql" >> $GITHUB_PATH
      
      - name: Build Database (Key Vault)
        run: python3 refresh_database.py --path specification/keyvault --fresh
      
      - name: Run Security Queries
        run: ./run-queries.sh
      
      - name: Upload SARIF
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: results/
```

## Python Analyzer as Complement

You can also use the Python analyzer alongside CodeQL:

```bash
# Build database for CodeQL
python3 refresh_database.py --path specification/keyvault --fresh

# Run CodeQL queries
./run-queries.sh

# Also run Python analyzer (uses same database)
python3 analyze.py

# Or analyze additional specs not in database
python3 analyze.py --source azure-rest-api-specs/specification/compute
```

## Key Points

1. **Database Scope**: The database determines what CodeQL analyzes
2. **Build First**: Always build/refresh database before running CodeQL queries
3. **Path Matters**: Use `--path` to target specific services
4. **Use --all Carefully**: Only use `--all` when you need comprehensive analysis
5. **Results Format**: CodeQL produces SARIF, Python analyzer uses console output

## Troubleshooting

### "Database not found"
```bash
# Build the database first
python3 refresh_database.py --fresh
```

### "No files to analyze"
```bash
# Make sure the path exists in azure-rest-api-specs
ls azure-rest-api-specs/specification/
```

### "Query failed"
```bash
# Rebuild database with --clean
python3 refresh_database.py --clean --fresh
```

### "Out of disk space"
```bash
# Use specific path instead of --all
python3 refresh_database.py --path specification/keyvault --fresh
```

## Performance Tips

- **Small Databases**: Use specific paths for faster builds and queries
- **Incremental Updates**: Use `--update` instead of `--fresh` when possible
- **Parallel Analysis**: Run Python analyzer while CodeQL queries execute
- **Cache Results**: Keep results directories organized by date/service

## Further Reading

- `DATABASE_REFRESH.md`: Detailed database refresh documentation
- `../README.md`: General usage guide
- `QUICK_REFERENCE.md`: Quick command reference
