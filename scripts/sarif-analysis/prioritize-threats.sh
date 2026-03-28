#!/usr/bin/env bash
# Prioritize SARIF results for SilentReaper vulnerabilities
# Identifies high-priority vulnerabilities where APIs emit SAS URIs with improper RBAC or control/data plane isolation

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Function to display usage
usage() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS] <sarif-file>

Prioritize SARIF results for SilentReaper vulnerabilities.
Focuses on APIs emitting SAS URIs in responses with improper RBAC or control/data plane isolation.

OPTIONS:
    -h, --help              Show this help message
    -o, --output FILE       Output file (default: stdout)
    -f, --format FMT        Output format: table|json|markdown (default: table)
    -v, --verbose           Verbose output with analysis details
    --threshold LEVEL       Priority threshold: critical|high|medium|low (default: all)

PRIORITY LEVELS:
    CRITICAL - Direct SAS token exposure in control plane APIs
    HIGH     - Control plane APIs with data plane access patterns
    MEDIUM   - APIs with potential isolation issues
    LOW      - General security concerns

EXAMPLES:
    # Show all prioritized results
    $(basename "$0") results/SasUriInResponse-results.sarif

    # Show only critical and high priority threats
    $(basename "$0") --threshold high results/SasUriInResponse-results.sarif

    # Export to markdown report
    $(basename "$0") -f markdown -o threat-report.md results/SasUriInResponse-results.sarif

    # Analyze with verbose details
    $(basename "$0") -v results/SasUriInResponse-results.sarif

DESCRIPTION:
    This script prioritizes security findings based on threat severity,
    specifically focusing on control plane/data plane isolation issues.
    
    High-priority patterns include:
    - SAS tokens exposed in ARM/control plane responses
    - Storage account management APIs leaking data access tokens
    - Logic Apps exposing workflow execution tokens
    - Key Vault management APIs exposing secret access URIs
    - Compute APIs exposing storage or disk access credentials

EOF
    exit 0
}

# Parse command line arguments
OUTPUT_FILE=""
FORMAT="table"
VERBOSE=false
THRESHOLD="all"

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            ;;
        -o|--output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        -f|--format)
            FORMAT="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        --threshold)
            THRESHOLD="$2"
            shift 2
            ;;
        -*)
            echo -e "${RED}Error: Unknown option $1${NC}" >&2
            exit 1
            ;;
        *)
            SARIF_FILE="$1"
            shift
            ;;
    esac
done

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    echo -e "${RED}Error: jq is not installed${NC}" >&2
    exit 1
fi

# Check if SARIF file is provided
if [ -z "${SARIF_FILE:-}" ]; then
    echo -e "${RED}Error: No SARIF file specified${NC}" >&2
    exit 1
fi

# Check if SARIF file exists
if [ ! -f "$SARIF_FILE" ]; then
    echo -e "${RED}Error: File not found: $SARIF_FILE${NC}" >&2
    exit 1
fi

# Validate FORMAT option
if [[ ! "$FORMAT" =~ ^(table|json|markdown)$ ]]; then
    echo -e "${RED}Error: Invalid format '$FORMAT'. Must be: table, json, or markdown${NC}" >&2
    exit 1
fi

# Validate THRESHOLD option
if [[ ! "$THRESHOLD" =~ ^(all|critical|high|medium|low)$ ]]; then
    echo -e "${RED}Error: Invalid threshold '$THRESHOLD'. Must be: all, critical, high, medium, or low${NC}" >&2
    exit 1
fi

# Show progress
if [ "$VERBOSE" = true ]; then
    echo -e "${BLUE}Analyzing SARIF file: $SARIF_FILE${NC}" >&2
    echo -e "${BLUE}Priority threshold: $THRESHOLD${NC}" >&2
    echo "" >&2
fi

# Extract and prioritize results
TEMP_JSON=$(cat "$SARIF_FILE" | jq -r '
.runs[].results[] |
.locations[].physicalLocation.artifactLocation.uri as $uri |
{
    product: (if ($uri | test("Microsoft\\.[^/]+")) then $uri | capture("Microsoft\\.(?<p>[^/]+)") | "Microsoft." + .p else "Unknown" end),
    operation: (if ($uri | test("/[^/]+\\.json$")) then $uri | capture("/(?<o>[^/]+)\\.json$") | .o else "Unknown" end),
    version: (if ($uri | test("/(preview|stable)/[^/]+/")) then $uri | capture("/(preview|stable)/(?<v>[^/]+)/") | .v else "N/A" end),
    file: $uri,
    line: (try (.locations[].physicalLocation.region.startLine) catch 0)
} |
# Assign priority
.priority = (
    if (.file | test("Microsoft\\.Storage/.*(blob|queue|file|table)")) and (.file | test("resource-manager|management")) then
        "CRITICAL"
    elif (.file | test("Microsoft\\.Logic"; "i")) and (.operation | test("Workflow|workflow|callback|Callback|run|trigger"; "")) then
        "CRITICAL"
    elif (.file | test("resource-manager|management")) and (.file | test("Microsoft\\.(Compute|KeyVault|Web|Storage)")) then
        "HIGH"
    elif (.file | test("data-plane")) or (.operation | test("sas|token|credential|secret")) then
        "MEDIUM"
    else
        "LOW"
    end
) |
# Assign threat description
.threat = (
    if .priority == "CRITICAL" then
        if .product | test("Storage") then
            "Control plane API exposes SAS tokens for data plane access - enables data exfiltration"
        elif .product | test("Logic") then
            "Logic Apps management API exposes workflow execution tokens - enables unauthorized execution"
        else
            "Critical control plane/data plane isolation violation"
        end
    elif .priority == "HIGH" then
        "Control plane API may expose data plane access credentials"
    elif .priority == "MEDIUM" then
        "Potential credential or token exposure in API response"
    else
        "Security finding requires review"
    end
)
')

# Filter by threshold
FILTERED_JSON=$(echo "$TEMP_JSON" | jq -s --arg threshold "$THRESHOLD" '
.[] | select(
    if $threshold == "all" then true
    elif $threshold == "critical" then .priority == "CRITICAL"
    elif $threshold == "high" then (.priority == "CRITICAL" or .priority == "HIGH")
    elif $threshold == "medium" then (.priority == "CRITICAL" or .priority == "HIGH" or .priority == "MEDIUM")
    else true
    end
)
')

# Process based on output format
case "$FORMAT" in
    json)
        RESULT=$(echo "$FILTERED_JSON" | jq -c '.')
        ;;
    
    markdown)
        RESULT=$(cat << EOF
# SilentReaper Vulnerability Threat Hunting Report
## Control Plane/Data Plane Isolation Analysis

**Generated:** $(date)
**Source:** $(basename "$SARIF_FILE")

---

EOF
)
        
        # Add results grouped by priority
        for LEVEL in CRITICAL HIGH MEDIUM LOW; do
            COUNT=$(echo "$FILTERED_JSON" | jq -s --arg level "$LEVEL" '[.[] | select(.priority == $level)] | length')
            
            if [ "$COUNT" -gt 0 ]; then
                RESULT+=$'\n\n'
                RESULT+="## $LEVEL Priority ($COUNT findings)"$'\n\n'
                
                RESULT+=$(echo "$FILTERED_JSON" | jq -s --arg level "$LEVEL" -r '
                .[] | select(.priority == $level) |
                "### " + .product + " - " + .operation + "\n\n" +
                "- **Priority:** " + .priority + "\n" +
                "- **Version:** " + .version + "\n" +
                "- **Threat:** " + .threat + "\n" +
                "- **File:** `" + .file + ":" + (.line | tostring) + "`\n"
                ')
            fi
        done
        ;;
    
    table)
        # Generate table format without colors first
        RESULT=$(echo "$FILTERED_JSON" | jq -s -r '
        "═══════════════════════════════════════════════════════════════════════════════════════════",
        "Priority    Product                Operation        Version          Threat Pattern",
        "───────────────────────────────────────────────────────────────────────────────────────────",
        (sort_by(.priority) | reverse | .[] | 
            (.priority | .[0:11] + (" " * (11 - (. | length | if . > 11 then 11 else . end)))) + " " +
            (.product | .[0:22] + (" " * (22 - (. | length | if . > 22 then 22 else . end)))) + " " +
            (.operation | .[0:16] + (" " * (16 - (. | length | if . > 16 then 16 else . end)))) + " " +
            (.version | .[0:16] + (" " * (16 - (. | length | if . > 16 then 16 else . end)))) + " " +
            (.threat | .[0:40])
        ),
        "═══════════════════════════════════════════════════════════════════════════════════════════"
        ')
        ;;
esac

# Output results
if [ -n "$OUTPUT_FILE" ]; then
    # Remove ANSI color codes when writing to file
    echo "$RESULT" | sed 's/\x1b\[[0-9;]*m//g' > "$OUTPUT_FILE"
    if [ "$VERBOSE" = true ]; then
        echo -e "${GREEN}✓ Results written to: $OUTPUT_FILE${NC}" >&2
    fi
else
    echo "$RESULT"
fi

# Show statistics in verbose mode
if [ "$VERBOSE" = true ]; then
    echo "" >&2
    echo -e "${BLUE}Priority Distribution:${NC}" >&2
    for LEVEL in CRITICAL HIGH MEDIUM LOW; do
        COUNT=$(echo "$TEMP_JSON" | jq -s --arg level "$LEVEL" '[.[] | select(.priority == $level)] | length')
        if [ "$COUNT" -gt 0 ]; then
            COLOR=""
            case "$LEVEL" in
                CRITICAL) COLOR="$RED" ;;
                HIGH) COLOR="$YELLOW" ;;
                MEDIUM) COLOR="$BLUE" ;;
                LOW) COLOR="$NC" ;;
            esac
            echo -e "${COLOR}  $LEVEL: $COUNT${NC}" >&2
        fi
    done
fi

exit 0
