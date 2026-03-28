#!/usr/bin/env bash
# Deduplicate SARIF results by product + operation, ignoring API versions
# This script is designed for threat hunting in Azure REST APIs
# focusing on SilentReaper vulnerabilities (SAS URIs in responses with improper RBAC or control/data plane isolation)

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

Deduplicate SARIF results by product + operation, ignoring API versions.
Useful for threat hunting and identifying unique API endpoint vulnerabilities.

OPTIONS:
    -h, --help          Show this help message
    -o, --output FILE   Output file (default: stdout)
    -v, --verbose       Verbose output with statistics
    -f, --format FMT    Output format: unique|grouped|summary (default: unique)

EXAMPLES:
    # Extract unique product+operation combinations
    $(basename "$0") results/SasUriInResponse-results.sarif

    # Save to file with verbose statistics
    $(basename "$0") -v -o deduplicated.txt results/SasUriInResponse-results.sarif

    # Show grouped results by product
    $(basename "$0") -f grouped results/SasUriInResponse-results.sarif

    # Show summary statistics only
    $(basename "$0") -f summary results/SasUriInResponse-results.sarif

DESCRIPTION:
    This script processes SARIF output files to identify unique API endpoints
    by extracting the product name and operation from file paths, while
    ignoring API version differences. This is essential for threat hunting
    to identify patterns across different API versions.

    Example transformation:
        specification/storage/resource-manager/Microsoft.Storage/stable/2021-09-01/blob.json
        specification/storage/resource-manager/Microsoft.Storage/preview/2022-01-01-preview/blob.json
    
    Both become: Microsoft.Storage/blob

EOF
    exit 0
}

# Parse command line arguments
OUTPUT_FILE=""
VERBOSE=false
FORMAT="unique"

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            ;;
        -o|--output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -f|--format)
            FORMAT="$2"
            shift 2
            ;;
        -*)
            echo -e "${RED}Error: Unknown option $1${NC}" >&2
            echo "Use -h or --help for usage information" >&2
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
    echo "Please install jq: https://jqlang.github.io/jq/" >&2
    exit 1
fi

# Check if SARIF file is provided
if [ -z "${SARIF_FILE:-}" ]; then
    echo -e "${RED}Error: No SARIF file specified${NC}" >&2
    echo "Use -h or --help for usage information" >&2
    exit 1
fi

# Check if SARIF file exists
if [ ! -f "$SARIF_FILE" ]; then
    echo -e "${RED}Error: File not found: $SARIF_FILE${NC}" >&2
    exit 1
fi

# Validate FORMAT option
if [[ ! "$FORMAT" =~ ^(unique|grouped|summary)$ ]]; then
    echo -e "${RED}Error: Invalid format '$FORMAT'. Must be: unique, grouped, or summary${NC}" >&2
    exit 1
fi

# Show progress
if [ "$VERBOSE" = true ]; then
    echo -e "${BLUE}Analyzing SARIF file: $SARIF_FILE${NC}" >&2
    echo -e "${BLUE}Format: $FORMAT${NC}" >&2
    echo "" >&2
fi

# Main processing: Extract URIs and deduplicate
case "$FORMAT" in
    unique)
        # Extract unique product+operation combinations
        RESULT=$(cat "$SARIF_FILE" | jq -r '
            .runs[].results[]
            | .locations[].physicalLocation.artifactLocation.uri
            | sub("/(preview|stable)/[0-9-]+(-preview)?/"; "/*/")
            | capture(".*/Microsoft\\.(?<product>[^/]+)/.*/(?<operation>[^/]+)\\.json") 
            | "Microsoft." + .product + "/" + .operation
        ' | sort -u)
        ;;
    
    grouped)
        # Group by product and show operations
        RESULT=$(cat "$SARIF_FILE" | jq -r '
            .runs[].results[]
            | .locations[].physicalLocation.artifactLocation.uri
            | sub("/(preview|stable)/[0-9-]+(-preview)?/"; "/*/")
            | capture(".*/Microsoft\\.(?<product>[^/]+)/.*/(?<operation>[^/]+)\\.json") 
            | "Microsoft." + .product + "/" + .operation
        ' | sort -u | awk -F'/' '{
            product=$1
            operation=$2
            products[product] = products[product] (products[product] ? "\n  - " : "  - ") operation
        }
        END {
            for (p in products) {
                print p ":"
                print products[p]
                print ""
            }
        }')
        ;;
    
    summary)
        # Show summary statistics
        TOTAL_RESULTS=$(cat "$SARIF_FILE" | jq '[.runs[].results[]] | length')
        UNIQUE_PRODUCTS=$(cat "$SARIF_FILE" | jq -r '
            .runs[].results[]
            | .locations[].physicalLocation.artifactLocation.uri
            | capture(".*/Microsoft\\.(?<product>[^/]+)/.*") 
            | "Microsoft." + .product
        ' | sort -u | wc -l)
        UNIQUE_OPERATIONS=$(cat "$SARIF_FILE" | jq -r '
            .runs[].results[]
            | .locations[].physicalLocation.artifactLocation.uri
            | sub("/(preview|stable)/[0-9-]+(-preview)?/"; "/*/")
            | capture(".*/Microsoft\\.(?<product>[^/]+)/.*/(?<operation>[^/]+)\\.json") 
            | "Microsoft." + .product + "/" + .operation
        ' | sort -u | wc -l)
        
        RESULT=$(cat << EOF
═══════════════════════════════════════════════════════════
SARIF Analysis Summary
═══════════════════════════════════════════════════════════
File: $(basename "$SARIF_FILE")
Total Results: $TOTAL_RESULTS
Unique Products: $UNIQUE_PRODUCTS
Unique Product+Operation Combinations: $UNIQUE_OPERATIONS
═══════════════════════════════════════════════════════════
EOF
)
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
if [ "$VERBOSE" = true ] && [ "$FORMAT" != "summary" ]; then
    echo "" >&2
    echo -e "${BLUE}Statistics:${NC}" >&2
    UNIQUE_COUNT=$(echo "$RESULT" | grep -v '^$' | wc -l)
    echo -e "${BLUE}  Unique product+operation combinations: $UNIQUE_COUNT${NC}" >&2
fi

exit 0
