#!/usr/bin/env bash
# Memory Management Utilities for SpeQL
# Provides functions to detect system memory and calculate appropriate CodeQL memory limits

# Get total system memory in MB
get_total_memory_mb() {
    local mem_mb=0
    
    # Try Linux free command
    if command -v free &> /dev/null; then
        mem_mb=$(free -m | awk '/^Mem:/{print $2}')
    # Try macOS sysctl
    elif command -v sysctl &> /dev/null && sysctl hw.memsize &> /dev/null; then
        local mem_bytes=$(sysctl -n hw.memsize)
        mem_mb=$((mem_bytes / 1024 / 1024))
    # Fallback: check /proc/meminfo on Linux
    elif [ -f /proc/meminfo ]; then
        mem_mb=$(awk '/MemTotal:/{print int($2/1024)}' /proc/meminfo)
    else
        # Unable to detect, return 0
        mem_mb=0
    fi
    
    echo "$mem_mb"
}

# Calculate 90% of total system memory in MB
calculate_memory_limit() {
    local total_mem=$(get_total_memory_mb)
    
    if [ "$total_mem" -eq 0 ]; then
        echo "0"
        return 1
    fi
    
    # Calculate 90% of total memory
    local mem_limit=$((total_mem * 90 / 100))
    echo "$mem_limit"
}

# Count JSON files in a directory
# Note: For very large directories (>100K files), this may be slow
# Consider using early termination if only threshold checking is needed
count_json_files() {
    local dir="$1"
    
    if [ ! -d "$dir" ]; then
        echo "0"
        return 1
    fi
    
    # Count JSON files recursively
    local count=$(find "$dir" -type f -name "*.json" 2>/dev/null | wc -l)
    echo "$count" | tr -d ' '
}

# Determine if memory limit should be applied based on JSON file count
should_apply_memory_limit() {
    local json_count="$1"
    local threshold="${2:-50000}"  # Default threshold is 50K
    
    if [ "$json_count" -ge "$threshold" ]; then
        return 0  # True, should apply
    else
        return 1  # False, should not apply
    fi
}

# Get recommended memory settings for CodeQL
# Returns memory limit in MB if applicable, or empty string
get_memory_setting() {
    local database_path="$1"
    local threshold="${2:-50000}"
    
    # Check if database exists
    if [ ! -d "$database_path" ]; then
        echo ""
        return 1
    fi
    
    # Look for src or src.zip in database
    local source_dir=""
    if [ -d "$database_path/src" ]; then
        source_dir="$database_path/src"
    elif [ -f "$database_path/src.zip" ]; then
        # For src.zip, we need to count entries without extracting
        local json_count=$(unzip -l "$database_path/src.zip" 2>/dev/null | grep -c '\.json$' || echo "0")
        
        if should_apply_memory_limit "$json_count" "$threshold"; then
            calculate_memory_limit
        else
            echo ""
        fi
        return 0
    fi
    
    # Count JSON files in source directory
    if [ -n "$source_dir" ] && [ -d "$source_dir" ]; then
        local json_count=$(count_json_files "$source_dir")
        
        if should_apply_memory_limit "$json_count" "$threshold"; then
            calculate_memory_limit
        else
            echo ""
        fi
    else
        echo ""
    fi
}

# Format memory value for CodeQL --ram option
# Note: This function is kept for potential future use but is not currently utilized
# Memory limits are directly formatted in get_memory_setting()
format_memory_for_codeql() {
    local mem_mb="$1"
    
    if [ -z "$mem_mb" ] || [ "$mem_mb" -eq 0 ]; then
        echo ""
        return
    fi
    
    # CodeQL accepts memory in MB (just the number)
    echo "$mem_mb"
}

# Print memory configuration information
print_memory_info() {
    local database_path="$1"
    local NC="${2:-\033[0m}"
    local BLUE="${3:-\033[0;34m}"
    local YELLOW="${4:-\033[1;33m}"
    local GREEN="${5:-\033[0;32m}"
    
    local total_mem=$(get_total_memory_mb)
    local mem_limit=$(calculate_memory_limit)
    local json_count=0
    
    if [ -d "$database_path/src" ]; then
        json_count=$(count_json_files "$database_path/src")
    elif [ -f "$database_path/src.zip" ]; then
        json_count=$(unzip -l "$database_path/src.zip" 2>/dev/null | grep -c '\.json$' || echo "0")
    fi
    
    echo -e "${BLUE}Memory Configuration:${NC}"
    echo -e "  Total System Memory: ${total_mem} MB"
    echo -e "  Available for CodeQL (90%): ${mem_limit} MB"
    echo -e "  JSON files in database: ${json_count}"
    
    if [ "$json_count" -ge 50000 ]; then
        echo -e "  ${GREEN}Memory limit will be applied (>50K files)${NC}"
    else
        echo -e "  ${YELLOW}Memory limit not needed (<50K files)${NC}"
    fi
}
