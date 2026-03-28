# CodeQL Memory Management

## Overview

SpeQL now includes intelligent memory management for CodeQL query execution. The system automatically detects when large databases (>50,000 JSON files) are being analyzed and applies appropriate memory limits to improve performance and prevent out-of-memory errors.

## Features

### Automatic Memory Detection
- **System Memory Detection**: Automatically detects total system memory on Linux and macOS
- **Smart Calculation**: Allocates 90% of total system memory for CodeQL operations
- **Threshold-Based**: Only applies memory limits when database exceeds 50,000 JSON files
- **Manual Override**: Supports custom memory limits via environment variable or interactive menu

### How It Works

1. **Database Analysis**: The system counts JSON files in the CodeQL database
2. **Threshold Check**: If count exceeds 50,000 files, memory management is activated
3. **Memory Calculation**: Calculates 90% of total system memory
4. **Application**: Applies `--ram` flag to CodeQL analyze command

## Usage

### Automatic Mode (Recommended)

Simply run queries as normal. Memory limits are applied automatically when needed:

```bash
./run-queries.sh
```

The script will display memory configuration information:

```
Applying dynamic memory limit: 7149 MB
Memory Configuration:
  Total System Memory: 7944 MB
  Available for CodeQL (90%): 7149 MB
  JSON files in database: 60000
  Memory limit will be applied (>50K files)
```

### Custom Memory Limit (Environment Variable)

Set a specific memory limit using the `CODEQL_MEMORY_LIMIT` environment variable:

```bash
# Set custom limit (in MB)
export CODEQL_MEMORY_LIMIT=4096

# Run queries
./run-queries.sh

# Or in one line
CODEQL_MEMORY_LIMIT=4096 ./run-queries.sh
```

### Interactive Menu Option

Using the SpeQL CLI menu (`python3 SpeQL.py`):

1. Navigate to **CodeQL Security Queries**
2. Select **Run with Custom Memory Limit**
3. Enter your desired memory limit in MB (or press Enter for automatic detection)
4. Queries will run with your specified settings

## Memory Configuration Details

### Default Behavior

- **Small Databases (<50K files)**: No memory limit applied, uses CodeQL defaults
- **Large Databases (≥50K files)**: Applies 90% of system memory

### Why 90%?

- Leaves 10% for system operations and other processes
- Prevents system from running out of memory
- Optimal balance between performance and stability

### Supported Platforms

- **Linux**: Uses `free` command or `/proc/meminfo`
- **macOS**: Uses `sysctl hw.memsize`
- **Other**: Falls back to default behavior if memory detection unavailable

## Technical Details

### Memory Utilities Module

Located at `utils/memory_utils.sh`, provides:

- `get_total_memory_mb()`: Detects total system memory
- `calculate_memory_limit()`: Calculates 90% of total memory
- `count_json_files()`: Counts JSON files in directory
- `should_apply_memory_limit()`: Determines if threshold is met
- `get_memory_setting()`: Integrated function for complete memory setting logic
- `print_memory_info()`: Displays memory configuration information

### Integration Points

1. **run-queries.sh**: 
   - Sources memory utilities
   - Checks database size
   - Applies `--ram` flag to `codeql database analyze`

2. **SpeQL.py**:
   - Adds "Run with Custom Memory Limit" menu option
   - Prompts for custom memory limit
   - Sets `CODEQL_MEMORY_LIMIT` environment variable

## Examples

### Example 1: Small Database

```bash
$ ./run-queries.sh
═══════════════════════════════════════════════════════════
  SpeQL - Azure Security Query Analyzer
═══════════════════════════════════════════════════════════

Using default memory settings (database < 50K JSON files)
Running security queries...
```

### Example 2: Large Database

```bash
$ ./run-queries.sh
═══════════════════════════════════════════════════════════
  SpeQL - Azure Security Query Analyzer
═══════════════════════════════════════════════════════════

Applying dynamic memory limit: 14336 MB
Memory Configuration:
  Total System Memory: 15929 MB
  Available for CodeQL (90%): 14336 MB
  JSON files in database: 253000
  Memory limit will be applied (>50K files)

Running security queries...
```

### Example 3: Custom Memory Limit

```bash
$ export CODEQL_MEMORY_LIMIT=8192
$ ./run-queries.sh
═══════════════════════════════════════════════════════════
  SpeQL - Azure Security Query Analyzer
═══════════════════════════════════════════════════════════

Using custom memory limit: 8192 MB (from CODEQL_MEMORY_LIMIT)
Running security queries...
```

## Performance Impact

### Before Memory Management
- Large databases could cause CodeQL to run out of memory
- Queries might fail or hang on systems with limited RAM
- Manual intervention required to set memory limits

### After Memory Management
- Automatic optimization for large databases
- Prevents out-of-memory errors
- Improved query performance on large datasets
- No manual configuration needed for most cases

## Troubleshooting

### Memory limit not applied

**Cause**: Database has fewer than 50,000 JSON files  
**Solution**: This is expected behavior. Memory limits are only needed for large databases.

### Custom memory limit ignored

**Cause**: Typo in environment variable name  
**Solution**: Ensure you're using `CODEQL_MEMORY_LIMIT` (not `CODEQL_MEM_LIMIT`)

### Out of memory errors persist

**Cause**: System doesn't have enough RAM for the database size  
**Solution**: Try reducing memory limit or analyzing smaller subsets of the data

```bash
# Reduce memory to 50% of total
CODEQL_MEMORY_LIMIT=4096 ./run-queries.sh

# Or analyze specific Azure services instead of all
python3 refresh_database.py --path specification/logic
```

### Memory detection fails

**Cause**: Unsupported platform or missing utilities  
**Solution**: Use manual override with `CODEQL_MEMORY_LIMIT`

```bash
# Manually set to 8GB
export CODEQL_MEMORY_LIMIT=8192
./run-queries.sh
```

## Testing

Run the test suite to verify memory management functionality:

```bash
./tests/test_memory_management.sh
```

The test validates:
- Memory detection on your system
- Memory limit calculation (90% rule)
- JSON file counting
- Threshold logic (50K files)
- Integration with run-queries.sh
- Environment variable support
- Menu integration

## FAQ

**Q: Will this slow down queries on small databases?**  
A: No. Memory limits are only applied to databases with >50K JSON files. Small databases use CodeQL's default memory management.

**Q: Can I disable automatic memory management?**  
A: Yes, set `CODEQL_MEMORY_LIMIT=0` to disable it, or modify the threshold in `utils/memory_utils.sh`.

**Q: What if I have multiple databases?**  
A: Memory limits are calculated per-query execution based on the current database being analyzed.

**Q: Does this work with the analyze.py script?**  
A: No, analyze.py is a Python-based analyzer that doesn't use CodeQL. Memory management only applies to CodeQL query execution via run-queries.sh.

**Q: How do I change the 50K threshold?**  
A: Edit `run-queries.sh` and modify the threshold parameter in `get_memory_setting "$DATABASE_PATH" 50000` (change 50000 to your desired threshold).

**Q: Can I use a percentage other than 90%?**  
A: Yes, modify the `calculate_memory_limit()` function in `utils/memory_utils.sh` to use a different percentage.

## Related Documentation

- [Quick Start Guide](QUICKSTART.md)
- [Database Refresh Documentation](DATABASE_REFRESH.md)
- [CodeQL Workflow Guide](CODEQL_WORKFLOW.md)
- [CLI Menu Guide](CLI_MENU_GUIDE.md)

## Future Enhancements

Potential improvements for future versions:
- Per-query memory profiles based on query complexity
- Dynamic adjustment based on available (not total) memory
- Memory usage monitoring and reporting
- Integration with refresh_database.py for database creation
- Support for Windows memory detection
