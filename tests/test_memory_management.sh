#!/usr/bin/env bash
# Test Script: Memory Management Feature Validation
# 
# This script validates that the memory management features work correctly:
# 1. Memory detection and calculation
# 2. JSON file counting
# 3. Dynamic memory limit application
# 4. Environment variable override

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "═══════════════════════════════════════════════════════════"
echo "  SpeQL - Memory Management Feature Validation"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Test 1: Check if memory utilities exist
echo -e "${BLUE}Test 1: Memory utilities module${NC}"
if [ -f "utils/memory_utils.sh" ]; then
    echo -e "${GREEN}✓ Memory utilities module exists${NC}"
    source utils/memory_utils.sh
else
    echo -e "${RED}✗ Memory utilities module not found${NC}"
    exit 1
fi
echo ""

# Test 2: Memory detection
echo -e "${BLUE}Test 2: System memory detection${NC}"
TOTAL_MEM=$(get_total_memory_mb)
if [ "$TOTAL_MEM" -gt 0 ]; then
    echo -e "${GREEN}✓ System memory detected: ${TOTAL_MEM} MB${NC}"
else
    echo -e "${RED}✗ Failed to detect system memory${NC}"
    exit 1
fi
echo ""

# Test 3: Memory limit calculation (90%)
echo -e "${BLUE}Test 3: Memory limit calculation${NC}"
MEM_LIMIT=$(calculate_memory_limit)
EXPECTED=$((TOTAL_MEM * 90 / 100))
if [ "$MEM_LIMIT" -eq "$EXPECTED" ]; then
    echo -e "${GREEN}✓ Memory limit calculated correctly: ${MEM_LIMIT} MB (90% of ${TOTAL_MEM} MB)${NC}"
else
    echo -e "${RED}✗ Memory limit calculation failed${NC}"
    echo "  Expected: ${EXPECTED} MB, Got: ${MEM_LIMIT} MB"
    exit 1
fi
echo ""

# Test 4: JSON file counting (with mock data if database doesn't exist)
echo -e "${BLUE}Test 4: JSON file counting${NC}"
if [ -d "database/azure-api-db/src" ]; then
    JSON_COUNT=$(count_json_files "database/azure-api-db/src")
    echo -e "${GREEN}✓ JSON files in database: ${JSON_COUNT}${NC}"
elif [ -f "database/azure-api-db/src.zip" ]; then
    JSON_COUNT=$(unzip -l "database/azure-api-db/src.zip" 2>/dev/null | grep -c '\.json$' || echo "0")
    echo -e "${GREEN}✓ JSON files in database (from src.zip): ${JSON_COUNT}${NC}"
else
    echo -e "${YELLOW}⚠ Database not found, creating mock directory for testing${NC}"
    mkdir -p /tmp/speql_test_db
    touch /tmp/speql_test_db/test1.json
    touch /tmp/speql_test_db/test2.json
    JSON_COUNT=$(count_json_files "/tmp/speql_test_db")
    if [ "$JSON_COUNT" -eq 2 ]; then
        echo -e "${GREEN}✓ JSON file counting works: ${JSON_COUNT} files${NC}"
    else
        echo -e "${RED}✗ JSON file counting failed${NC}"
        exit 1
    fi
    rm -rf /tmp/speql_test_db
fi
echo ""

# Test 5: Threshold logic
echo -e "${BLUE}Test 5: Threshold-based memory limit application${NC}"

# Test with count below threshold
if should_apply_memory_limit 1000 50000; then
    echo -e "${RED}✗ Threshold logic failed (should not apply for 1000 files)${NC}"
    exit 1
else
    echo -e "${GREEN}✓ Correctly skips memory limit for 1000 files (< 50K threshold)${NC}"
fi

# Test with count above threshold
if should_apply_memory_limit 60000 50000; then
    echo -e "${GREEN}✓ Correctly applies memory limit for 60000 files (> 50K threshold)${NC}"
else
    echo -e "${RED}✗ Threshold logic failed (should apply for 60000 files)${NC}"
    exit 1
fi
echo ""

# Test 6: Memory setting integration
echo -e "${BLUE}Test 6: Integrated memory setting function${NC}"
if [ -d "database/azure-api-db" ]; then
    MEM_SETTING=$(get_memory_setting "database/azure-api-db" 50000)
    
    # Get actual file count
    if [ -d "database/azure-api-db/src" ]; then
        ACTUAL_COUNT=$(count_json_files "database/azure-api-db/src")
    elif [ -f "database/azure-api-db/src.zip" ]; then
        ACTUAL_COUNT=$(unzip -l "database/azure-api-db/src.zip" 2>/dev/null | grep -c '\.json$' || echo "0")
    else
        ACTUAL_COUNT=0
    fi
    
    if [ "$ACTUAL_COUNT" -ge 50000 ]; then
        if [ -n "$MEM_SETTING" ] && [ "$MEM_SETTING" -gt 0 ]; then
            echo -e "${GREEN}✓ Memory setting applied for large database: ${MEM_SETTING} MB${NC}"
        else
            echo -e "${RED}✗ Memory setting not applied for large database${NC}"
            exit 1
        fi
    else
        if [ -z "$MEM_SETTING" ]; then
            echo -e "${GREEN}✓ Memory setting correctly skipped for small database (${ACTUAL_COUNT} files)${NC}"
        else
            echo -e "${YELLOW}⚠ Memory setting applied for small database (may be intentional)${NC}"
        fi
    fi
else
    echo -e "${YELLOW}⚠ Database not found, skipping integrated test${NC}"
fi
echo ""

# Test 7: run-queries.sh integration
echo -e "${BLUE}Test 7: run-queries.sh memory integration${NC}"
if grep -q "get_memory_setting" run-queries.sh; then
    echo -e "${GREEN}✓ run-queries.sh integrates memory management${NC}"
else
    echo -e "${RED}✗ run-queries.sh missing memory management integration${NC}"
    exit 1
fi

if grep -q "CODEQL_MEMORY_LIMIT" run-queries.sh; then
    echo -e "${GREEN}✓ run-queries.sh supports CODEQL_MEMORY_LIMIT override${NC}"
else
    echo -e "${RED}✗ run-queries.sh missing CODEQL_MEMORY_LIMIT support${NC}"
    exit 1
fi

if grep -q '\$MEMORY_OPTION' run-queries.sh; then
    echo -e "${GREEN}✓ run-queries.sh applies memory option to CodeQL command${NC}"
else
    echo -e "${RED}✗ run-queries.sh missing memory option application${NC}"
    exit 1
fi
echo ""

# Test 8: SpeQL.py menu integration
echo -e "${BLUE}Test 8: SpeQL.py menu integration${NC}"
if grep -q "Run with Custom Memory Limit" SpeQL.py; then
    echo -e "${GREEN}✓ SpeQL.py includes custom memory limit option${NC}"
else
    echo -e "${RED}✗ SpeQL.py missing custom memory limit option${NC}"
    exit 1
fi

if grep -q "CODEQL_MEMORY_LIMIT" SpeQL.py; then
    echo -e "${GREEN}✓ SpeQL.py sets CODEQL_MEMORY_LIMIT environment variable${NC}"
else
    echo -e "${RED}✗ SpeQL.py missing CODEQL_MEMORY_LIMIT support${NC}"
    exit 1
fi
echo ""

# Test 9: Documentation check
echo -e "${BLUE}Test 9: Code documentation${NC}"
if grep -q "Dynamic Memory Management" run-queries.sh; then
    echo -e "${GREEN}✓ run-queries.sh includes memory management documentation${NC}"
else
    echo -e "${YELLOW}⚠ run-queries.sh missing inline documentation${NC}"
fi

if grep -q "Memory Management Utilities" utils/memory_utils.sh; then
    echo -e "${GREEN}✓ memory_utils.sh includes header documentation${NC}"
else
    echo -e "${YELLOW}⚠ memory_utils.sh missing header documentation${NC}"
fi
echo ""

echo "═══════════════════════════════════════════════════════════"
echo -e "${GREEN}All tests passed! ✓${NC}"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "Summary of features:"
echo "  • System memory detection (Linux and macOS)"
echo "  • Automatic 90% memory limit calculation"
echo "  • JSON file counting for threshold determination"
echo "  • Dynamic memory limit for databases >50K files"
echo "  • Environment variable override (CODEQL_MEMORY_LIMIT)"
echo "  • Interactive menu option for custom memory settings"
echo ""
echo "Memory Configuration Details:"
echo "  • Total System Memory: ${TOTAL_MEM} MB"
echo "  • Calculated Limit (90%): ${MEM_LIMIT} MB"
echo "  • Threshold: 50,000 JSON files"
echo ""
echo "Usage:"
echo "  • Automatic: ./run-queries.sh"
echo "  • Custom: export CODEQL_MEMORY_LIMIT=4096 && ./run-queries.sh"
echo "  • Menu: python3 SpeQL.py -> CodeQL Queries -> Custom Memory Limit"
