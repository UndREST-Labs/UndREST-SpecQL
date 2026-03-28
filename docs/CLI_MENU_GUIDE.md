# SpeQL.py - CLI Menu System Usage Guide

## Overview

The SpeQL.py script provides an interactive command-line interface (CLI) menu system that makes it easy to navigate and execute all SpeQL API spec query analysis actions. SpeQL is an API Spec Query Analyser that currently supports the Azure REST API and is designed to identify APIs that might be vulnerable to SilentReaper. The menu is designed for both beginners and experienced users, offering intuitive navigation and helpful prompts.

## Installation

### Installing Dependencies

The CLI menu system requires only one Python dependency: `pyfiglet` for rendering the ASCII art logo.

```bash
# Install from requirements.txt
pip3 install -r requirements.txt

# Or install pyfiglet directly
pip3 install pyfiglet
```

**Note**: If pyfiglet is not installed, the CLI will still work but will use a simple ASCII logo fallback.

## Launching the CLI Menu

```bash
# Make sure you're in the SpeQL repository root directory
cd /path/to/SpeQL

# Launch the interactive menu
python3 SpeQL.py

# Or make it executable and run directly
chmod +x SpeQL.py
./SpeQL.py
```

![SpeQL Interactive CLI Menu Demo](../demos/05-cli-menu.gif)

## Main Menu Overview

When you launch SpeQL.py, you'll see the main menu with the following options:

```
   _____            ____    __ 
  / ___/____  ___  / __ \  / / 
  \__ \/ __ \/ _ \/ / / / / /  
 ___/ / /_/ /  __/ /_/ / / /___
/____/ .___/\___/\___\_\/_____/
    /_/                        

API Spec Query Analyser for Azure REST API
═══════════════════════════════════════════════════════════

Main Menu
────────────────────────────────────────────────────────────
1. 📊 Security Analysis
2. 🗄️  Database Management
3. 🔍 CodeQL Security Queries
4. 📈 SARIF Analysis Tools
5. ⚙️  Setup and Installation
6. 📚 Documentation and Help
7. ℹ️  About SpeQL
0. Exit
────────────────────────────────────────────────────────────
```

## Menu Categories

### 1. 📊 Security Analysis

Provides options to run the Python-based security analyzer (`analyze.py`) in different modes:

#### Options:
1. **Analyze from Database (default - fast)**
   - Analyzes specifications from the pre-built database
   - Fastest option, analyzes ~300-500 files
   - Command: `python3 analyze.py`

2. **Analyze from Custom Source Directory**
   - Analyze any custom directory containing JSON specification files
   - Prompts for directory path
   - Command: `python3 analyze.py --source <path>`

3. **Analyze Specific Azure Service**
   - Analyze a specific Azure service (Logic Apps, Key Vault, Compute, etc.)
   - Shows common service paths
   - Command: `python3 analyze.py --source azure-rest-api-specs/<service>`

4. **Analyze All Azure Services (comprehensive)**
   - Analyzes all Azure specifications (~253,000 files)
   - Warning: This takes significant time
   - Command: `python3 analyze.py --source azure-rest-api-specs/specification`

5. **Verbose Analysis Mode**
   - Runs analysis with additional diagnostic output
   - Command: `python3 analyze.py --verbose`

6. **Show Available Analysis Options**
   - Displays help text for analyze.py
   - Command: `python3 analyze.py --help`

#### Example Workflow:
```
Main Menu → 1 (Security Analysis) → 1 (Analyze from Database) → Press Enter
```

### 2. 🗄️ Database Management

Manages the CodeQL database and Azure REST API specifications repository:

#### Options:
1. **Update Repository and Rebuild Database (default)**
   - Updates existing Azure specs and rebuilds the database
   - Default service: Logic Apps
   - Command: `python3 refresh_database.py`

2. **Fresh Clone and Rebuild**
   - Removes existing repo and performs fresh clone
   - Command: `python3 refresh_database.py --fresh`

3. **Build Database for Specific Service**
   - Prompts for Azure service path
   - Rebuilds database with only that service
   - Command: `python3 refresh_database.py --path <service> --fresh`

4. **Build Database for All Services**
   - Builds comprehensive database with all Azure services
   - Warning: Requires significant disk space and time
   - Command: `python3 refresh_database.py --all --fresh`

5. **Update Repository Only (skip DB build)**
   - Updates Azure specs without rebuilding CodeQL database
   - Useful when CodeQL is not installed
   - Command: `python3 refresh_database.py --skip-db-build`

6. **Show Database Management Options**
   - Displays help text for refresh_database.py
   - Command: `python3 refresh_database.py --help`

#### Example Workflow:
```
Main Menu → 2 (Database Management) → 3 (Specific Service)
→ Enter: specification/keyvault → Wait for completion → Press Enter
```

### 3. 🔍 CodeQL Security Queries

Execute CodeQL security queries and view results (requires CodeQL CLI):

#### Options:
1. **Run All Security Queries**
1. **Run All Queries**
   - Runs CodeQL security query against the database
   - Generates SARIF output files
   - Command: `./run-queries.sh`

2. **Run Individual Query**
   - Lists available query:
     1. SasUriInResponse.ql (detects SAS URIs in API example responses)
   - Prompts for query selection
   - Command: `codeql database analyze database/azure-api-db queries/azure-security/<query>.ql ...`

3. **View Previous Results**
   - Lists SARIF result files in the results/ directory
   - Shows file names and counts

4. **Show Query Documentation**
   - Displays detailed description of the security query
   - Explains what the query detects and security impacts

#### Example Workflow:
```
Main Menu → 3 (CodeQL Queries) → 1 (Run All Queries) → Wait → Press Enter
Main Menu → 3 (CodeQL Queries) → 3 (View Results) → Press Enter
```

### 4. 📈 SARIF Analysis Tools

Analyze SARIF output files for threat hunting and prioritization:

#### Options:
1. **Deduplicate SARIF Results**
   - Removes duplicate findings across API versions
   - Prompts for SARIF file path
   - Command: `./scripts/sarif-analysis/deduplicate-by-product-operation.sh <file>`

2. **Parse SARIF Endpoints**
   - Extracts endpoint data in various formats (CSV, JSON, grouped)
   - Prompts for file path and format
   - Command: `./scripts/sarif-analysis/parse-sarif-endpoints.sh -f <format> <file>`

3. **Prioritize Threats**
   - Prioritizes findings by severity (critical, high, medium)
   - Prompts for threshold and file path
   - Command: `./scripts/sarif-analysis/prioritize-threats.sh --threshold <level> <file>`

4. **Show SARIF Tools Documentation**
   - Displays full SARIF analysis README
   - Command: `cat scripts/sarif-analysis/README.md`

#### Example Workflow:
```
Main Menu → 4 (SARIF Tools) → 1 (Deduplicate)
→ Enter: results/SasUriInResponse-results.sarif → Wait → Press Enter
```

### 5. ⚙️ Setup and Installation

Automated setup and dependency management:

#### Options:
1. **Run Automated Setup**
   - Installs Java, CodeQL CLI, and dependencies
   - Command: `./setup.sh`

2. **Install CodeQL CLI**
   - Shows manual installation instructions
   - Provides download links and commands

3. **Install Python Dependencies**
   - Installs packages from requirements.txt
   - Command: `pip3 install -r requirements.txt`

4. **Check Prerequisites**
   - Checks for Python 3, Git, CodeQL, and Java
   - Shows installation status for each

5. **Show Setup Documentation**
   - Displays setup instructions and quick start

#### Example Workflow:
```
Main Menu → 5 (Setup) → 4 (Check Prerequisites) → Press Enter
```

### 6. 📚 Documentation and Help

Access documentation and guides:

#### Options:
1. **View README**
   - Displays the main README.md file
   - Command: `cat README.md`

2. **View Quick Start Guide**
   - Shows docs/QUICKSTART.md if available
   - Command: `cat docs/QUICKSTART.md`

3. **View Contributing Guidelines**
   - Displays CONTRIBUTING.md
   - Command: `cat CONTRIBUTING.md`

4. **View Repository Structure**
   - Shows docs/REPOSITORY_STRUCTURE.md if available
   - Command: `cat docs/REPOSITORY_STRUCTURE.md`

5. **List All Available Scripts**
   - Lists all main scripts and tools
   - Organized by category

6. **Show Example Workflows**
   - Displays common usage patterns and workflows
   - Provides copy-paste command examples

#### Example Workflow:
```
Main Menu → 6 (Documentation) → 6 (Example Workflows) → Press Enter
```

### 7. ℹ️ About SpeQL

Displays information about the SpeQL tool:
- Purpose and capabilities
- Vulnerabilities detected
- Repository link and license
- SilentReaper vulnerability focus and definition

## Navigation Tips

### General Navigation
- **Enter a number (0-7)** to select a menu option
- **Press 0** to go back to the previous menu or exit
- **Press Ctrl+C** at any time to exit gracefully

### Input Handling
- All inputs are validated to ensure they're valid numbers
- Invalid inputs show an error message and re-prompt
- Empty paths or invalid files show appropriate warnings

### Command Execution
- Commands show their full command line before execution
- Output is displayed in real-time
- After completion, press Enter to return to the menu

### Screen Management
- The screen clears between menu transitions for a clean interface
- Color coding helps distinguish different types of information:
  - 🔵 Blue: Information and headers
  - 🟢 Green: Success messages and menu numbers
  - 🟡 Yellow: Warnings and prompts
  - 🔴 Red: Errors
  - 🟣 Cyan: User input prompts

## Common Workflows

### Initial Setup and First Analysis
```
1. Launch CLI: python3 SpeQL.py
2. Main Menu → 5 (Setup) → 1 (Run Automated Setup)
3. Main Menu → 2 (Database) → 1 (Update and Rebuild)
4. Main Menu → 1 (Analysis) → 1 (Analyze from Database)
```

### Analyze a Specific Azure Service
```
1. Launch CLI: python3 SpeQL.py
2. Main Menu → 2 (Database) → 3 (Specific Service)
3. Enter: specification/keyvault
4. Main Menu → 1 (Analysis) → 1 (Analyze from Database)
```

### Run CodeQL Queries and Analyze Results
```
1. Launch CLI: python3 SpeQL.py
2. Main Menu → 3 (CodeQL Queries) → 1 (Run All Queries)
3. Main Menu → 4 (SARIF Tools) → 1 (Deduplicate)
4. Enter: results/SasUriInResponse-results.sarif
5. Main Menu → 4 (SARIF Tools) → 3 (Prioritize Threats)
```

### Check System Prerequisites
```
1. Launch CLI: python3 SpeQL.py
2. Main Menu → 5 (Setup) → 4 (Check Prerequisites)
```

## Troubleshooting

### "Must be run from the SpeQL repository root directory"
- Navigate to the repository root where analyze.py exists
- Command: `cd /path/to/SpeQL`

### "pyfiglet not installed. Using simple ASCII logo."
- Install pyfiglet: `pip3 install pyfiglet`
- Or: `pip3 install -r requirements.txt`
- The CLI will still work with the fallback logo

### "Command not found" errors
- Ensure scripts are executable: `chmod +x *.sh *.py`
- Check that required tools are installed (git, codeql, python3)
- Use Menu → Setup → Check Prerequisites

### Database or source path not found
- Run database refresh: Menu → Database → Update and Rebuild
- Or clone specs manually: `python3 refresh_database.py --skip-db-build`

### CodeQL not available
- Install CodeQL CLI (see Setup menu)
- Or run Python analyzer only (doesn't require CodeQL)

## Features

### Modular Design
- Each submenu is a separate function
- Easy to add new actions or modify existing ones
- Clean separation of concerns

### Error Handling
- Input validation for all user inputs
- Graceful handling of missing files/commands
- Clear error messages with suggestions

### User-Friendly
- Descriptive option names
- Context-aware prompts
- Help text and documentation access
- Color-coded output for readability

### Extensible
- Easy to add new menu options
- Simple function structure
- Well-commented code
- Follows existing patterns

## Contributing

To add new menu options:

1. Add the option to the appropriate menu's `options` list
2. Add a corresponding `elif choice == N:` block
3. Call `run_command()` with the appropriate command
4. Test the new option thoroughly

Example:
```python
elif choice == 8:  # New option
    clear_screen()
    print_logo()
    run_command(["python3", "new_script.py"], "Running new script")
    pause()
```

## Support

For issues, questions, or contributions:
- GitHub Issues: https://github.com/SpeQLSec/SpeQL/issues
- Repository: https://github.com/SpeQLSec/SpeQL
- Documentation: README.md and docs/ directory

## License

See the LICENSE file in the repository root.
