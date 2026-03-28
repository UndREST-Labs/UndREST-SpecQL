# SpeQL Demo GIFs & Extension Screenshots

This directory contains animated GIF demonstrations of all major SpeQL use cases, as well as static PNG screenshots of the APISpy DevTools browser extension. These visuals showcase the tool's capabilities and provide visual guides for users.

## Available Demos

### 1. Setup and Installation (`01-setup.gif`)
Demonstrates the initial setup process:
- Cloning the repository
- Installing Python dependencies
- Running automated setup
- Installing CodeQL and dependencies

### 2. Database Refresh (`02-database-refresh.gif`)
Shows how to refresh the database with Azure Logic Apps specifications:
- Running `refresh_database.py` with `specification/logic`
- Cloning Azure REST API specs
- Building the CodeQL database
- Verifying 309 JSON files indexed

### 3. Python Security Analyzer (`03-python-analyzer.gif`)
Demonstrates running the Python-based security analyzer:
- Analyzing Logic Apps specifications
- Detecting multiple vulnerability types
- Showing detected issues (SilentReaper, Azure Vault Recon, etc.)

### 4. CodeQL Security Queries (`04-codeql-queries.gif`)
Shows CodeQL query execution:
- Running `run-queries.sh`
- Detecting SAS URIs in API responses
- Generating SARIF results
- Identifying SilentReaper vulnerabilities

### 5. Interactive CLI Menu (`05-cli-menu.gif`)
Demonstrates the SpeQL interactive CLI:
- Launching `python3 SpeQL.py`
- Displaying the main menu with all options
- Navigating through Security Analysis, Database Management, CodeQL Queries, SARIF Tools, Setup, and Documentation

### 6. SARIF Analysis Tools (`06-sarif-analysis.gif`)
Shows SARIF analysis and threat hunting:
- Deduplicating findings across API versions
- Parsing endpoint data to CSV
- Prioritizing threats by severity
- Identifying control plane/data plane isolation issues

### 7. Complete Workflow (`07-complete-workflow.gif`)
End-to-end demonstration from setup to results:
- Refreshing database with Logic Apps specs
- Running Python analyzer
- Executing CodeQL queries
- Analyzing SARIF results
- Complete security analysis workflow

### 8. APISpy Portal Sweep (`apispy-portal-sweep-terminal.gif`)
Demonstrates the automated portal sweep script:
- Running `python3 scripts/portal_sweep.py --help` to view all options
- Simulating a complete sweep of all 305 Azure Portal services
- Showing the ARM request capture, URL collection, and CSV export phases

## Generating Demos

To regenerate all VHS terminal demos, use the provided script:

```bash
cd /path/to/SpeQL
./tests/generate-vhs-demos.sh
```

This requires:
- [VHS](https://github.com/charmbracelet/vhs) tool installed
- ffmpeg for video processing
- ttyd for terminal recording

To regenerate the APISpy extension screenshots:

```bash
# Install dependencies (one-time)
pip install playwright
python3 -m playwright install chromium

# Regenerate screenshots
python3 scripts/generate_screenshots.py
```

## APISpy Extension Screenshots

Static PNG screenshots of the [APISpy DevTools extension](../apispy/extension/README.md) captured
in an automated agent environment using Playwright.

### Empty state (`apispy-empty.png`)

Initial panel state — no Azure/Microsoft API requests have been observed yet.  The toolbar
shows the status-filter toggles and the count badge reads 0.

![APISpy empty state](apispy-empty.png)

### Requests table (`apispy-requests.png`)

Panel populated with observed requests, showing all five classification statuses:
✅ Exact match, ⚠️ Version mismatch, 🔶 Unknown route, ℹ️ ARM root route, and an ARM
batch sub-request (↳).

![APISpy requests table](apispy-requests.png)

### Column filter (`apispy-filter.png`)

The Status column-filter dropdown is open, letting users show only selected status values.
Each column header (Method, api-version, Status, Reason, Shard) has its own independent
multi-value filter accessible via the ▾ button.

![APISpy column filter](apispy-filter.png)

### Detail panel (`apispy-detail.png`)

A row is selected, opening the resizable detail panel with the full request breakdown:
URL, method, host, path, normalised path, api-version, status, provider namespace,
matched route key, available spec versions, shard source, and reason code.

![APISpy detail panel](apispy-detail.png)

## Technical Details

**Terminal GIF demos**
- **Format**: Animated GIF
- **Size**: 1000×720 pixels
- **Theme**: TokyoNight
- **Font Size**: 16pt
- **Tool**: VHS (Video Hype Script) by Charm

**Extension screenshots**
- **Format**: PNG
- **Size**: 1280×720 pixels
- **Tool**: Playwright (headless Chromium)
- **Script**: `scripts/generate_screenshots.py`
- **Output**: `demos/apispy-{empty,requests,filter,detail}.png`

## Usage in Documentation

These GIFs are referenced throughout the SpeQL documentation:
- `README.md` - Quick start and overview sections
- `docs/QUICKSTART.md` - Setup and first run guides
- `docs/CLI_MENU_GUIDE.md` - CLI navigation examples
- `docs/DATABASE_REFRESH.md` - Database management workflows
- `docs/SARIF_ANALYSIS_QUICKSTART.md` - SARIF tool demonstrations
- `scripts/PORTAL_SWEEP.md` - Portal sweep terminal demo

## License

These demos are part of the SpeQL project and are subject to the same license terms.

