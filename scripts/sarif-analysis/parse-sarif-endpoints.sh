#!/usr/bin/env bash
# Parse SARIF output files and extract detailed API endpoint information
# Designed for threat hunting in Azure REST APIs

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to display usage
usage() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS] <sarif-file>

Parse SARIF output files and extract detailed API endpoint information.
Designed for threat hunting and security analysis of Azure REST APIs.

OPTIONS:
    -h, --help              Show this help message
    -o, --output FILE       Output file (default: stdout)
    -f, --format FMT        Output format: json|csv|table (default: table)
    -v, --verbose           Verbose output with statistics
    --include-lines         Include line numbers in output
    --include-messages      Include result messages in output

FORMATS:
    json    - Structured JSON output (best for automation)
    csv     - Comma-separated values (best for spreadsheets)
    table   - Human-readable table format (default)

EXAMPLES:
    # Show results in table format
    $(basename "$0") results/SasUriInResponse-results.sarif

    # Export to CSV for Excel analysis
    $(basename "$0") -f csv -o endpoints.csv results/SasUriInResponse-results.sarif

    # Export to JSON with all details
    $(basename "$0") -f json --include-lines --include-messages -o endpoints.json results/*.sarif

    # Process multiple SARIF files
    for file in results/*.sarif; do
        $(basename "$0") -f csv "\$file" >> all-endpoints.csv
    done

DESCRIPTION:
    This script extracts comprehensive endpoint information from SARIF files:
    - Product/Service name (e.g., Microsoft.Storage)
    - Operation/Resource name (e.g., blob, queue)
    - API version (e.g., 2021-09-01)
    - Stability level (stable/preview)
    - File path
    - Line numbers (optional)
    - Result messages (optional)

EOF
    exit 0
}

# Parse command line arguments
OUTPUT_FILE=""
FORMAT="table"
VERBOSE=false
INCLUDE_LINES=false
INCLUDE_MESSAGES=false

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
        --include-lines)
            INCLUDE_LINES=true
            shift
            ;;
        --include-messages)
            INCLUDE_MESSAGES=true
            shift
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
if [[ ! "$FORMAT" =~ ^(json|csv|table)$ ]]; then
    echo -e "${RED}Error: Invalid format '$FORMAT'. Must be: json, csv, or table${NC}" >&2
    exit 1
fi

# Show progress
if [ "$VERBOSE" = true ]; then
    echo -e "${BLUE}Parsing SARIF file: $SARIF_FILE${NC}" >&2
    echo -e "${BLUE}Format: $FORMAT${NC}" >&2
    echo "" >&2
fi

# Process based on output format
case "$FORMAT" in
    json)
        if [ "$INCLUDE_LINES" = true ] && [ "$INCLUDE_MESSAGES" = true ]; then
            RESULT=$(cat "$SARIF_FILE" | jq -c '
                .runs[].results[] |
                .locations[].physicalLocation.artifactLocation.uri as $uri |
                {
                    product: (if ($uri | test("Microsoft\\.[^/]+")) then $uri | capture("Microsoft\\.(?<p>[^/]+)") | "Microsoft." + .p else "Unknown" end),
                    operation: (if ($uri | test("/[^/]+\\.json$")) then $uri | capture("/(?<o>[^/]+)\\.json$") | .o else "Unknown" end),
                    version: (if ($uri | test("/(preview|stable)/[^/]+/")) then $uri | capture("/(preview|stable)/(?<v>[^/]+)/") | .v else "N/A" end),
                    stability: (if ($uri | test("/preview/")) then "preview" elif ($uri | test("/stable/")) then "stable" else "unknown" end),
                    file: $uri,
                    line: (.locations[].physicalLocation.region.startLine // 0),
                    message: .message.text
                }
            ')
        elif [ "$INCLUDE_LINES" = true ]; then
            RESULT=$(cat "$SARIF_FILE" | jq -c '
                .runs[].results[] |
                .locations[].physicalLocation.artifactLocation.uri as $uri |
                {
                    product: (if ($uri | test("Microsoft\\.[^/]+")) then $uri | capture("Microsoft\\.(?<p>[^/]+)") | "Microsoft." + .p else "Unknown" end),
                    operation: (if ($uri | test("/[^/]+\\.json$")) then $uri | capture("/(?<o>[^/]+)\\.json$") | .o else "Unknown" end),
                    version: (if ($uri | test("/(preview|stable)/[^/]+/")) then $uri | capture("/(preview|stable)/(?<v>[^/]+)/") | .v else "N/A" end),
                    stability: (if ($uri | test("/preview/")) then "preview" elif ($uri | test("/stable/")) then "stable" else "unknown" end),
                    file: $uri,
                    line: (.locations[].physicalLocation.region.startLine // 0)
                }
            ')
        elif [ "$INCLUDE_MESSAGES" = true ]; then
            RESULT=$(cat "$SARIF_FILE" | jq -c '
                .runs[].results[] |
                .locations[].physicalLocation.artifactLocation.uri as $uri |
                {
                    product: (if ($uri | test("Microsoft\\.[^/]+")) then $uri | capture("Microsoft\\.(?<p>[^/]+)") | "Microsoft." + .p else "Unknown" end),
                    operation: (if ($uri | test("/[^/]+\\.json$")) then $uri | capture("/(?<o>[^/]+)\\.json$") | .o else "Unknown" end),
                    version: (if ($uri | test("/(preview|stable)/[^/]+/")) then $uri | capture("/(preview|stable)/(?<v>[^/]+)/") | .v else "N/A" end),
                    stability: (if ($uri | test("/preview/")) then "preview" elif ($uri | test("/stable/")) then "stable" else "unknown" end),
                    file: $uri,
                    message: .message.text
                }
            ')
        else
            RESULT=$(cat "$SARIF_FILE" | jq -c '
                .runs[].results[] |
                .locations[].physicalLocation.artifactLocation.uri as $uri |
                {
                    product: (if ($uri | test("Microsoft\\.[^/]+")) then $uri | capture("Microsoft\\.(?<p>[^/]+)") | "Microsoft." + .p else "Unknown" end),
                    operation: (if ($uri | test("/[^/]+\\.json$")) then $uri | capture("/(?<o>[^/]+)\\.json$") | .o else "Unknown" end),
                    version: (if ($uri | test("/(preview|stable)/[^/]+/")) then $uri | capture("/(preview|stable)/(?<v>[^/]+)/") | .v else "N/A" end),
                    stability: (if ($uri | test("/preview/")) then "preview" elif ($uri | test("/stable/")) then "stable" else "unknown" end),
                    file: $uri
                }
            ')
        fi
        ;;
    
    csv)
        # Generate CSV header
        HEADER="Product,Operation,Version,Stability,File"
        [ "$INCLUDE_LINES" = true ] && HEADER+=",Line"
        [ "$INCLUDE_MESSAGES" = true ] && HEADER+=",Message"
        
        # Generate CSV content based on options
        RESULT=$(echo -e "$HEADER")
        RESULT+=$'\n'
        
        if [ "$INCLUDE_LINES" = true ] && [ "$INCLUDE_MESSAGES" = true ]; then
            RESULT+=$(cat "$SARIF_FILE" | jq -r '
                .runs[].results[] |
                .locations[].physicalLocation.artifactLocation.uri as $uri |
                {
                    product: (if ($uri | test("Microsoft\\.[^/]+")) then $uri | capture("Microsoft\\.(?<p>[^/]+)") | "Microsoft." + .p else "Unknown" end),
                    operation: (if ($uri | test("/[^/]+\\.json$")) then $uri | capture("/(?<o>[^/]+)\\.json$") | .o else "Unknown" end),
                    version: (if ($uri | test("/(preview|stable)/[^/]+/")) then $uri | capture("/(preview|stable)/(?<v>[^/]+)/") | .v else "N/A" end),
                    stability: (if ($uri | test("/preview/")) then "preview" elif ($uri | test("/stable/")) then "stable" else "unknown" end),
                    file: $uri,
                    line: (.locations[].physicalLocation.region.startLine // 0),
                    message: .message.text
                } |
                .product + "," + .operation + "," + .version + "," + .stability + "," + .file + "," + (.line | tostring) + "," + (.message | gsub(","; ";"))
            ')
        elif [ "$INCLUDE_LINES" = true ]; then
            RESULT+=$(cat "$SARIF_FILE" | jq -r '
                .runs[].results[] |
                .locations[].physicalLocation.artifactLocation.uri as $uri |
                {
                    product: (if ($uri | test("Microsoft\\.[^/]+")) then $uri | capture("Microsoft\\.(?<p>[^/]+)") | "Microsoft." + .p else "Unknown" end),
                    operation: (if ($uri | test("/[^/]+\\.json$")) then $uri | capture("/(?<o>[^/]+)\\.json$") | .o else "Unknown" end),
                    version: (if ($uri | test("/(preview|stable)/[^/]+/")) then $uri | capture("/(preview|stable)/(?<v>[^/]+)/") | .v else "N/A" end),
                    stability: (if ($uri | test("/preview/")) then "preview" elif ($uri | test("/stable/")) then "stable" else "unknown" end),
                    file: $uri,
                    line: (.locations[].physicalLocation.region.startLine // 0)
                } |
                .product + "," + .operation + "," + .version + "," + .stability + "," + .file + "," + (.line | tostring)
            ')
        elif [ "$INCLUDE_MESSAGES" = true ]; then
            RESULT+=$(cat "$SARIF_FILE" | jq -r '
                .runs[].results[] |
                .locations[].physicalLocation.artifactLocation.uri as $uri |
                {
                    product: (if ($uri | test("Microsoft\\.[^/]+")) then $uri | capture("Microsoft\\.(?<p>[^/]+)") | "Microsoft." + .p else "Unknown" end),
                    operation: (if ($uri | test("/[^/]+\\.json$")) then $uri | capture("/(?<o>[^/]+)\\.json$") | .o else "Unknown" end),
                    version: (if ($uri | test("/(preview|stable)/[^/]+/")) then $uri | capture("/(preview|stable)/(?<v>[^/]+)/") | .v else "N/A" end),
                    stability: (if ($uri | test("/preview/")) then "preview" elif ($uri | test("/stable/")) then "stable" else "unknown" end),
                    file: $uri,
                    message: .message.text
                } |
                .product + "," + .operation + "," + .version + "," + .stability + "," + .file + "," + (.message | gsub(","; ";"))
            ')
        else
            RESULT+=$(cat "$SARIF_FILE" | jq -r '
                .runs[].results[] |
                .locations[].physicalLocation.artifactLocation.uri as $uri |
                {
                    product: (if ($uri | test("Microsoft\\.[^/]+")) then $uri | capture("Microsoft\\.(?<p>[^/]+)") | "Microsoft." + .p else "Unknown" end),
                    operation: (if ($uri | test("/[^/]+\\.json$")) then $uri | capture("/(?<o>[^/]+)\\.json$") | .o else "Unknown" end),
                    version: (if ($uri | test("/(preview|stable)/[^/]+/")) then $uri | capture("/(preview|stable)/(?<v>[^/]+)/") | .v else "N/A" end),
                    stability: (if ($uri | test("/preview/")) then "preview" elif ($uri | test("/stable/")) then "stable" else "unknown" end),
                    file: $uri
                } |
                .product + "," + .operation + "," + .version + "," + .stability + "," + .file
            ')
        fi
        ;;
    
    table)
        # Generate table format
        RESULT=$(cat "$SARIF_FILE" | jq -r '
            .runs[].results[] |
            .locations[].physicalLocation.artifactLocation.uri as $uri |
            {
                product: (if ($uri | test("Microsoft\\.[^/]+")) then $uri | capture("Microsoft\\.(?<p>[^/]+)") | "Microsoft." + .p else "Unknown" end),
                operation: (if ($uri | test("/[^/]+\\.json$")) then $uri | capture("/(?<o>[^/]+)\\.json$") | .o else "Unknown" end),
                version: (if ($uri | test("/(preview|stable)/[^/]+/")) then $uri | capture("/(preview|stable)/(?<v>[^/]+)/") | .v else "N/A" end),
                stability: (if ($uri | test("/preview/")) then "preview" elif ($uri | test("/stable/")) then "stable" else "unknown" end),
                file: $uri
            }
        ' | jq -s '
        "═══════════════════════════════════════════════════════════════════════════════",
        "Product                    Operation          Version          Stability    File",
        "───────────────────────────────────────────────────────────────────────────────",
        (.[] | 
            (.product | .[0:25] + (" " * (25 - (. | length | if . > 25 then 25 else . end)))) + " " +
            (.operation | .[0:18] + (" " * (18 - (. | length | if . > 18 then 18 else . end)))) + " " +
            (.version | .[0:16] + (" " * (16 - (. | length | if . > 16 then 16 else . end)))) + " " +
            (.stability | .[0:12] + (" " * (12 - (. | length | if . > 12 then 12 else . end)))) + " " +
            .file
        ),
        "═══════════════════════════════════════════════════════════════════════════════"
        ' | sed 's/^"//;s/"$//')
        ;;
esac

# Output results
if [ -n "$OUTPUT_FILE" ]; then
    echo "$RESULT" > "$OUTPUT_FILE"
    if [ "$VERBOSE" = true ]; then
        echo -e "${GREEN}✓ Results written to: $OUTPUT_FILE${NC}" >&2
        LINES=$(echo "$RESULT" | wc -l)
        echo -e "${GREEN}  Lines: $LINES${NC}" >&2
    fi
else
    echo "$RESULT"
fi

# Show statistics in verbose mode
if [ "$VERBOSE" = true ]; then
    echo "" >&2
    echo -e "${BLUE}Statistics:${NC}" >&2
    TOTAL=$(cat "$SARIF_FILE" | jq '[.runs[].results[]] | length')
    echo -e "${BLUE}  Total results: $TOTAL${NC}" >&2
fi

exit 0
