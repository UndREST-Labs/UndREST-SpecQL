# Database Refresh Guide

This guide explains how to build and refresh the SpeQL CodeQL database from the Azure REST API specifications repository.

## Overview

SpeQL analyzes Azure REST API specifications from Microsoft's [azure-rest-api-specs](https://github.com/Azure/azure-rest-api-specs) repository. The database refresh functionality allows you to:

- Build a fresh database from the latest Azure specifications
- Update an existing database with new changes
- Target specific Azure services for analysis
- Customize which specifications to include

## Prerequisites

### Required Tools

1. **Git**: For cloning and updating the Azure repository
   ```bash
   # Check if git is installed
   git --version
   ```

2. **CodeQL CLI** (Version 2.20.x required): Required for building the database (optional for repository updates)
   
   **Important**: CodeQL version 2.23.x and newer have compatibility issues with JSON-only database creation. Use version 2.20.1 or 2.20.2.
   
   ```bash
   # Download CodeQL 2.20.2
   wget https://github.com/github/codeql-cli-binaries/releases/download/v2.20.2/codeql-linux64.zip
   unzip codeql-linux64.zip
   export PATH="$PATH:$(pwd)/codeql"
   
   # Verify installation (should show 2.20.x)
   codeql version
   ```

3. **Python 3** (for Python script): Already available on most systems
   ```bash
   python3 --version
   ```

### Optional but Recommended

- **Sufficient disk space**: 
  - Minimal (Logic Apps only): ~500 MB
  - Full repository: ~5-10 GB
- **Good internet connection**: For cloning the Azure repository

## Quick Start

### Using Bash Script (Recommended for Linux/Mac)

```bash
# Default: Update/clone Logic Apps specs and build database
./refresh-database.sh

# Show all options
./refresh-database.sh --help
```

### Using Python Script (Cross-platform)

```bash
# Default: Update/clone Logic Apps specs and build database
python3 refresh_database.py

# Show all options
python3 refresh_database.py --help
```

![Database Refresh Demo](../demos/02-database-refresh.gif)

## Usage Examples

### Basic Operations

#### 1. Initial Setup
First time setting up the database:
```bash
./refresh-database.sh --fresh
```

#### 2. Regular Updates
Update to the latest specifications:
```bash
./refresh-database.sh --update
```

#### 3. Complete Rebuild
Clean rebuild of the database:
```bash
./refresh-database.sh --fresh --clean
```

### Targeting Specific Azure Services

#### Analyze Logic Apps (Default)
```bash
./refresh-database.sh --path specification/logic
```

#### Analyze Key Vault
```bash
./refresh-database.sh --path specification/keyvault --fresh
```

#### Analyze Azure Compute
```bash
./refresh-database.sh --path specification/compute --fresh
```

#### Analyze Multiple Services
Rebuild for different service by specifying the path:
```bash
# First analyze Key Vault
./refresh-database.sh --path specification/keyvault --fresh

# Later switch to Logic Apps
./refresh-database.sh --path specification/logic --fresh
```

#### Analyze All Azure Services
⚠️ **Warning**: This downloads and processes the entire repository (~5-10 GB)
```bash
./refresh-database.sh --all --fresh
```

### Advanced Usage

#### Update Repository Without Rebuilding Database
Useful when CodeQL is not available or you want to defer the build:
```bash
./refresh-database.sh --skip-db-build
```

Then later, when ready:
```bash
./refresh-database.sh
```

#### Use a Specific Branch
```bash
./refresh-database.sh --branch main --fresh
```

#### Clean Build with Custom Path
```bash
./refresh-database.sh --path specification/storage --fresh --clean
```

## Command-Line Options

### Common Options

| Option | Short | Description |
|--------|-------|-------------|
| `--help` | `-h` | Show help message |
| `--fresh` | `-f` | Perform fresh clone (removes existing repository) |
| `--update` | `-u` | Update existing clone (default) |
| `--path PATH` | `-p PATH` | Specify Azure spec path to include |
| `--all` | `-a` | Include all Azure specifications |
| `--branch BRANCH` | `-b BRANCH` | Specify branch to use (default: main) |
| `--skip-db-build` | - | Skip CodeQL database build |
| `--clean` | - | Clean existing database before rebuild |

### Path Examples

The `--path` option accepts any path within the Azure specifications repository:

- `specification/logic` - Logic Apps APIs
- `specification/keyvault` - Azure Key Vault APIs
- `specification/compute` - Azure Compute (VMs, etc.)
- `specification/storage` - Azure Storage APIs
- `specification/network` - Azure Networking APIs
- `specification/web` - Azure App Service APIs
- `specification` - All specifications (same as `--all`)

## Workflow Examples

### Scenario 1: Weekly Security Scan

Schedule regular updates to catch new vulnerabilities:

```bash
#!/bin/bash
# weekly-scan.sh

# Update database
./refresh-database.sh --update

# Run analysis
python3 analyze.py

# Run CodeQL queries
./run-queries.sh
```

### Scenario 2: Continuous Integration

Integrate into CI/CD pipeline:

```yaml
# GitHub Actions example
name: Azure Security Scan
on:
  schedule:
    - cron: '0 0 * * 0'  # Weekly
  workflow_dispatch:

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
      
      - name: Refresh Database
        run: ./refresh-database.sh --update
      
      - name: Run Security Analysis
        run: python3 analyze.py
```

### Scenario 3: Multi-Service Analysis

Analyze multiple Azure services sequentially:

```bash
#!/bin/bash
# multi-service-scan.sh

services=(
  "specification/logic"
  "specification/keyvault"
  "specification/compute"
)

for service in "${services[@]}"; do
  echo "Analyzing $service..."
  ./refresh-database.sh --path "$service" --fresh
  python3 analyze.py > "results/$(basename $service)-results.txt"
done
```

## Understanding the Database Build Process

### What Happens During Refresh

1. **Repository Management**
   - Clones or updates the Azure REST API specs repository
   - Uses sparse checkout for specific paths (efficient)
   - Fetches latest changes from the specified branch

2. **Database Creation**
   - Extracts JSON files from the specified path
   - Creates CodeQL database with JavaScript language extractor
   - Uses `--codescanning-config=config/SpeQL.yml` to specify JSON file patterns
   - Allows autobuild to run naturally (which indexes the JSON files)
   - A warning "Only found JavaScript or TypeScript files that were empty..." is expected but harmless
   - The database should finalize successfully despite the warning
   - Indexes all JSON files for query execution

3. **Compatibility Setup**
   - Creates `src.zip` for `analyze.py` compatibility
   - Maintains database metadata in `codeql-database.yml`
   - Stores diagnostic information in log files

### Time Estimates

Operation times (approximate):

- **First clone (Logic Apps)**: 2-5 minutes
- **Update existing clone**: 30-60 seconds
- **Database build (Logic Apps)**: 1-3 minutes
- **Full repository clone**: 15-30 minutes
- **Full database build**: 10-20 minutes

### Disk Space Requirements

- **Logic Apps only**: ~500 MB
- **Single service**: ~1-2 GB
- **Full repository**: ~5-10 GB
- **CodeQL CLI**: ~500 MB

## Troubleshooting

### Problem: "CodeQL not found"

**Solution 1**: Install CodeQL
```bash
wget https://github.com/github/codeql-cli-binaries/releases/latest/download/codeql-linux64.zip
unzip codeql-linux64.zip
export PATH="$PATH:$(pwd)/codeql"
```

**Solution 2**: Update repository only (defer database build)
```bash
./refresh-database.sh --skip-db-build
```

### Problem: "git clone failed" or timeout

**Solutions**:
- Check internet connection
- Use `--path` to target smaller specification set
- Try again (network issues are often transient)
- Use existing clone with `--update` instead of `--fresh`

### Problem: "Out of disk space"

**Solutions**:
- Use `--path` to target specific services
- Avoid `--all` option
- Clean old databases: `rm -rf database/azure-api-db`
- Remove Azure repo: `rm -rf azure-rest-api-specs`

### Problem: "Database build failed"

**Solutions**:
- Check CodeQL version: `codeql version` (requires 2.0+)
- Verify source files exist: `ls azure-rest-api-specs/specification/logic`
- Check build logs in `database/azure-api-db/log/`
- Try `--clean` to remove corrupted database first

### Note: CodeQL Database Creation Process

**The scripts use codescanning config to index JSON files**:
- Uses `--codescanning-config=config/SpeQL.yml` to specify JSON file patterns (`**/*.json`)
- Autobuild runs naturally and indexes the JSON files specified in the config
- A warning "Only found JavaScript or TypeScript files that were empty or contained syntax errors" is **expected and harmless**
- This warning appears because JSON files are not executable JavaScript, but they are still indexed correctly
- The codescanning config is essential for JSON file indexing in JavaScript language databases
- The database creation completes successfully and can be queried normally

### Problem: "analyze.py can't find files"

**Solution**: Ensure `src.zip` was created
```bash
# Manually create src.zip if needed
cd database/azure-api-db
zip -r src.zip src/
cd ../..
```

### Problem: Script permission denied

**Solution**: Make scripts executable
```bash
chmod +x refresh-database.sh
chmod +x refresh_database.py
```

## Best Practices

### 1. Start Small
Begin with a single service before attempting full repository analysis:
```bash
./refresh-database.sh --path specification/logic
```

### 2. Regular Updates
Update weekly or before important security reviews:
```bash
# Add to crontab
0 0 * * 0 cd /path/to/SpeQL && ./refresh-database.sh --update
```

### 3. Version Control
Don't commit the full database or azure-rest-api-specs to your repository. The `.gitignore` is already configured appropriately.

### 4. Incremental Analysis
Focus on specific services relevant to your security requirements rather than analyzing everything.

### 5. Keep Tools Updated
Regularly update CodeQL CLI to the latest version for best performance and accuracy.

### 6. Monitor Disk Usage
Large databases can consume significant space. Clean up periodically:
```bash
# Remove old database
rm -rf database/azure-api-db

# Remove Azure specs clone
rm -rf azure-rest-api-specs

# Rebuild fresh
./refresh-database.sh --fresh
```

## Integration with Analysis Tools

After refreshing the database, use these tools for analysis:

### 1. Python Analyzer (No CodeQL needed)
```bash
python3 analyze.py
```

### 2. CodeQL Queries (Requires CodeQL)
```bash
./run-queries.sh
```

### 3. Custom Queries
```bash
codeql database analyze database/azure-api-db \
    queries/azure-security/YourCustomQuery.ql \
    --format=sarif-latest \
    --output=results/custom.sarif
```

## FAQ

**Q: Do I need to rebuild the database every time I update the repository?**

A: If you want to analyze the latest specifications, yes. However, you can update the repository without rebuilding (`--skip-db-build`) and defer the rebuild.

**Q: Can I analyze multiple Azure services simultaneously?**

A: No, but you can build the database with all services (`--all`) or specific multiple services by choosing a parent path (e.g., `specification`).

**Q: How often should I refresh the database?**

A: Depends on your security requirements. Weekly updates are reasonable for most use cases. Critical infrastructure might require more frequent updates.

**Q: What's the difference between `--fresh` and `--update`?**

A: `--fresh` removes the existing repository clone and starts over. `--update` keeps the existing clone and pulls latest changes (faster and more efficient).

**Q: Can I use this offline?**

A: Once cloned, you can rebuild the database offline. However, updating requires internet access to fetch latest changes.

**Q: Does this work on Windows?**

A: The bash script requires WSL or Git Bash on Windows. The Python script (`refresh_database.py`) works natively on Windows.

## Additional Resources

- [Azure REST API Specs Repository](https://github.com/Azure/azure-rest-api-specs)
- [CodeQL CLI Documentation](https://codeql.github.com/docs/codeql-cli/)
- [SpeQL Main Documentation](../README.md)
- [Contributing Guide](../CONTRIBUTING.md)

## Support

For issues or questions:
1. Check this guide's troubleshooting section
2. Review the main [README.md](../README.md)
3. Open an issue on GitHub
4. Check existing issues for similar problems
