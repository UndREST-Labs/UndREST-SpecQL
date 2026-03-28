#!/bin/bash
# Script to generate all VHS demo GIFs
# This script runs all VHS tape files and generates GIFs for documentation

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║    SpeQL VHS Demo Generator                               ║${NC}"
echo -e "${GREEN}║    Creating GIF demonstrations for all use cases         ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if VHS is installed
if ! command -v vhs &> /dev/null; then
    echo -e "${RED}Error: VHS is not installed${NC}"
    echo "Please install VHS: https://github.com/charmbracelet/vhs"
    echo "  go install github.com/charmbracelet/vhs@latest"
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "SpeQL.py" ]; then
    echo -e "${RED}Error: Must be run from the SpeQL repository root directory${NC}"
    exit 1
fi

# Create demos directory if it doesn't exist
mkdir -p demos

# Array of VHS tape files
tapes=(
    "tests/vhs/01-setup.tape"
    "tests/vhs/02-database-refresh.tape"
    "tests/vhs/03-python-analyzer.tape"
    "tests/vhs/04-codeql-queries.tape"
    "tests/vhs/05-cli-menu.tape"
    "tests/vhs/06-sarif-analysis.tape"
    "tests/vhs/07-complete-workflow.tape"
)

# Descriptions for each tape
descriptions=(
    "Setup and Installation"
    "Database Refresh (specification/logic)"
    "Python Security Analyzer"
    "CodeQL Security Queries"
    "Interactive CLI Menu"
    "SARIF Analysis Tools"
    "Complete Workflow"
)

echo -e "${YELLOW}Found ${#tapes[@]} VHS tape files to process${NC}"
echo ""

# Process each tape file
success_count=0
failed_count=0

for i in "${!tapes[@]}"; do
    tape="${tapes[$i]}"
    description="${descriptions[$i]}"
    
    if [ ! -f "$tape" ]; then
        echo -e "${RED}✗ Tape file not found: $tape${NC}"
        ((failed_count++))
        continue
    fi
    
    echo -e "${YELLOW}Processing: $description${NC}"
    echo -e "  Tape: $tape"
    
    # Run VHS to generate the GIF
    if vhs "$tape" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Successfully generated GIF${NC}"
        ((success_count++))
    else
        echo -e "${RED}✗ Failed to generate GIF${NC}"
        ((failed_count++))
    fi
    echo ""
done

echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║    Generation Complete!                                   ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "Summary:"
echo -e "  ${GREEN}✓ Successfully generated: $success_count${NC}"
echo -e "  ${RED}✗ Failed: $failed_count${NC}"
echo ""
echo -e "Generated GIFs are located in the ${YELLOW}demos/${NC} directory"
echo ""

# List generated files
if [ $success_count -gt 0 ]; then
    echo "Generated files:"
    ls -lh demos/*.gif 2>/dev/null || echo "  (No GIF files found)"
fi
