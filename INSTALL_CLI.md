# SpeQL CLI Menu System - Installation and Usage

## Overview

The SpeQL CLI menu system (`SpeQL.py`) provides an interactive command-line interface for navigating and executing all SpeQL API spec query analysis actions. SpeQL is an API Spec Query Analyser that currently supports the Azure REST API and is designed to identify APIs that might be vulnerable to SilentReaper. This document provides installation instructions and basic usage information.

For the **APISpy** browser extension and portal sweep tool, see [UndREST-APISpy](https://github.com/UndREST-Labs/UndREST-APISpy).

## Installation

### Step 1: Install Python Dependencies

The CLI menu requires Python 3.6+ and the `pyfiglet` package for rendering the ASCII art logo.

```bash
# Install from requirements.txt (recommended)
pip3 install -r requirements.txt

# Or install pyfiglet directly
pip3 install pyfiglet
```

**Note:** If pyfiglet is not installed, the CLI will still work using a fallback ASCII logo.

### Step 2: Verify Installation

```bash
# Check that Python 3 is installed
python3 --version

# Verify SpeQL.py is executable
ls -l SpeQL.py

# If not executable, make it executable
chmod +x SpeQL.py
```

## Quick Start

### Launching the CLI Menu

```bash
# Navigate to the SpeQL repository root
cd /path/to/SpeQL

# Launch the interactive menu
python3 SpeQL.py

# Or run directly if executable
./SpeQL.py
```

### First Time Setup Workflow

If this is your first time using SpeQL, follow this workflow:

1. **Check Prerequisites**
   ```
   Main Menu → 5 (Setup and Installation) → 4 (Check Prerequisites)
   ```
   This verifies that Python, Git, Java, and CodeQL are installed.

2. **Run Automated Setup** (if needed)
   ```
   Main Menu → 5 (Setup and Installation) → 1 (Run Automated Setup)
   ```
   This installs Java, CodeQL CLI, and all dependencies.

3. **Update Database**
   ```
   Main Menu → 2 (Database Management) → 1 (Update Repository and Rebuild)
   ```
   This clones Azure API specs and builds the CodeQL database.

4. **Run Analysis**
   ```
   Main Menu → 1 (Security Analysis) → 1 (Analyze from Database)
   ```
   This runs the security analyzer on the database.

## Usage Examples

### Example 1: Run Security Analysis

```bash
# Launch CLI
python3 SpeQL.py

# Navigate: Main Menu → 1 (Security Analysis) → 1 (Analyze from Database)
# The analyzer will run and display results
# Press Enter to return to the menu
```

### Example 2: Analyze a Specific Azure Service

```bash
# Launch CLI
python3 SpeQL.py

# Step 1: Build database for specific service
# Navigate: Main Menu → 2 (Database Management) → 3 (Build for Specific Service)
# Enter: specification/keyvault
# Wait for completion, press Enter

# Step 2: Run analysis
# Navigate: Main Menu → 1 (Security Analysis) → 1 (Analyze from Database)
# Press Enter when complete
```

### Example 3: Run CodeQL Queries

```bash
# Launch CLI
python3 SpeQL.py

# Navigate: Main Menu → 3 (CodeQL Security Queries) → 1 (Run All Security Queries)
# Wait for queries to complete
# Press Enter to return

# View results
# Navigate: Main Menu → 3 (CodeQL Security Queries) → 3 (View Previous Results)
```

### Example 4: Threat Hunting with SARIF Analysis

```bash
# Launch CLI
python3 SpeQL.py

# Step 1: Run queries to generate SARIF files
# Navigate: Main Menu → 3 (CodeQL Security Queries) → 1 (Run All Queries)

# Step 2: Deduplicate results
# Navigate: Main Menu → 4 (SARIF Analysis Tools) → 1 (Deduplicate SARIF Results)
# Enter: results/SasUriInResponse-results.sarif

# Step 3: Prioritize threats
# Navigate: Main Menu → 4 (SARIF Analysis Tools) → 3 (Prioritize Threats)
# Enter: results/SasUriInResponse-results.sarif
# Enter: high (or critical/medium)
```

## Menu Structure

The CLI menu is organized into 7 main categories:

1. **📊 Security Analysis** - Run security scans
   - Analyze from database
   - Analyze custom directories
   - Analyze specific Azure services
   - Verbose mode

2. **🗄️ Database Management** - Manage CodeQL database
   - Update and rebuild
   - Fresh clone
   - Service-specific builds
   - Repository updates

3. **🔍 CodeQL Security Queries** - Execute CodeQL queries
   - Run all queries
   - Run individual queries
   - View results
   - Query documentation

4. **📈 SARIF Analysis Tools** - Analyze SARIF output
   - Deduplicate results
   - Parse endpoints
   - Prioritize threats
   - View documentation

5. **⚙️ Setup and Installation** - Setup and dependencies
   - Automated setup
   - Install CodeQL
   - Install Python packages
   - Check prerequisites

6. **📚 Documentation and Help** - Access guides
   - README
   - Quick start
   - Contributing
   - Example workflows

7. **ℹ️ About SpeQL** - Learn about the tool

## Navigation Tips

- **Enter a number** to select a menu option
- **Press 0** to go back or exit
- **Press Ctrl+C** to exit immediately
- Invalid inputs show an error and re-prompt
- Commands display their output in real-time

## Color Coding

The CLI uses color coding for better readability:
- 🔵 **Blue**: Information and headers
- 🟢 **Green**: Success messages and menu numbers
- 🟡 **Yellow**: Warnings and prompts
- 🔴 **Red**: Errors
- 🟣 **Cyan**: Logo and user input prompts

## Troubleshooting

### "Must be run from the UndREST-SpecQL repository root directory"
**Solution:** Navigate to the repository root where `analyze.py` exists:
```bash
cd /path/to/UndREST-SpecQL
```

### "pyfiglet not installed"
**Solution:** Install pyfiglet:
```bash
pip3 install pyfiglet
```
Or use requirements.txt:
```bash
pip3 install -r requirements.txt
```

### "Command not found" errors
**Solutions:**
1. Make scripts executable:
   ```bash
   chmod +x *.sh *.py
   ```
2. Check prerequisites:
   ```
   Menu → Setup → Check Prerequisites
   ```
3. Install missing tools (git, codeql, python3)

### CodeQL not available
**Solutions:**
1. Install CodeQL CLI:
   ```
   Menu → Setup → Install CodeQL CLI
   ```
2. Or use the Python analyzer only (doesn't require CodeQL):
   ```
   Menu → Security Analysis → Analyze from Database
   ```

## Command-Line Alternative

For automation or scripting, you can still use the individual scripts directly:

```bash
# Run security analysis
python3 analyze.py

# Update database
python3 refresh_database.py

# Run CodeQL queries
./run-queries.sh

# Analyze SARIF
./scripts/sarif-analysis/deduplicate-by-product-operation.sh results/file.sarif
```

## Further Documentation

- **Comprehensive Usage Guide**: `docs/CLI_MENU_GUIDE.md`
- **Quick Start**: `docs/QUICKSTART.md`
- **Main README**: `README.md`
- **Repository Structure**: `docs/REPOSITORY_STRUCTURE.md`

## Support

For issues, questions, or contributions:
- **GitHub Issues**: https://github.com/UndREST-Labs/UndREST-SpecQL/issues
- **Repository**: https://github.com/UndREST-Labs/UndREST-SpecQL
- **APISpy** (browser extension): https://github.com/UndREST-Labs/UndREST-APISpy
- **Documentation**: See `docs/` directory

## Summary

The SpeQL CLI menu system provides:
- ✅ Intuitive navigation for all SpeQL actions
- ✅ Interactive prompts with input validation
- ✅ Beautiful ASCII art logo
- ✅ Comprehensive coverage of all scripts
- ✅ User-friendly error handling
- ✅ Built-in documentation access
- ✅ Modular design for easy extension

Simply run `python3 SpeQL.py` to get started!
