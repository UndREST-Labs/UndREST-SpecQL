# VHS Testing Guide for SpeQL

This guide explains how to use, maintain, and regenerate the VHS (Video Hype Script) demo tests for the SpeQL repository.

## Overview

VHS tests are automated terminal recordings that demonstrate all major use cases of SpeQL. These tests:
- Provide visual documentation of features
- Ensure consistent user experience
- Serve as regression tests for CLI behavior
- Generate GIF animations for documentation

## Test Structure

### VHS Tape Files (tests/vhs/)

Seven VHS tape files cover all major use cases:

1. **01-setup.tape** - Setup and installation workflow
2. **02-database-refresh.tape** - Database refresh with specification/logic
3. **03-python-analyzer.tape** - Python security analyzer execution
4. **04-codeql-queries.tape** - CodeQL security queries
5. **05-cli-menu.tape** - Interactive CLI menu navigation
6. **06-sarif-analysis.tape** - SARIF analysis tools
7. **07-complete-workflow.tape** - End-to-end workflow

### Generated Demos (demos/)

Each tape file generates a corresponding GIF in the `demos/` directory:
- High-quality 1000x600 pixel GIFs
- Catppuccin Mocha theme for consistent appearance
- Optimized file sizes (240KB to 2.7MB)
- Referenced in documentation for visual guidance

## Running Tests

### Prerequisites

Install required dependencies:

```bash
# Install VHS tool
go install github.com/charmbracelet/vhs@latest

# Install supporting tools (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y ffmpeg ttyd
```

### Generate All Demos

Use the provided script to generate all demos at once:

```bash
cd /path/to/SpeQL
./tests/generate-vhs-demos.sh
```

This script:
- Validates VHS installation
- Processes all tape files sequentially
- Generates GIFs in the demos/ directory
- Reports success/failure for each demo
- Provides summary statistics

### Generate Individual Demos

To regenerate a specific demo:

```bash
cd /path/to/SpeQL
vhs tests/vhs/01-setup.tape
```

Replace `01-setup.tape` with any tape file name.

## Test Database Setup

The VHS tests demonstrate using the **specification/logic** API specs path as required. To set up the database for testing:

```bash
# Clone Azure REST API specs with Logic Apps only
python3 refresh_database.py --path specification/logic
```

This creates a database with 309 JSON files from Logic Apps specifications, which is used in the demos.

## Maintaining Tests

### When to Update Tests

Update VHS tapes when:
- CLI output format changes
- New features are added to SpeQL.py menu
- Command-line arguments change
- Database refresh workflow is modified
- SARIF analysis tools are enhanced

### Updating Tape Files

1. Edit the tape file in `tests/vhs/`
2. Adjust timing (Sleep commands) as needed
3. Update Type commands for new text
4. Test the changes:
   ```bash
   vhs tests/vhs/YOUR_FILE.tape
   ```
4. Verify the generated GIF looks correct
5. Commit both tape and GIF files

### VHS Tape Syntax

Key VHS commands used in our tapes:

```tape
Output demos/01-setup.gif          # Output file path
Set Shell bash                      # Shell to use
Set FontSize 16                     # Terminal font size (20% larger)
Set Width 1000                      # Terminal width
Set Height 720                      # Terminal height (20% taller)
Set Theme "TokyoNight"             # Color theme
Set TypingSpeed 80ms               # Typing animation speed (20% faster)
Set WindowBar ColorfulRight        # Window decoration bar

Hide                                # Hide commands from display
Type "cd /path/to/dir"             # Navigate to correct directory
Enter
Show                                # Show subsequent commands

Type "command text"                 # Type text (simulated)
Enter                               # Press Enter key
Sleep 1s                            # Wait 1 second
```

## Documentation Integration

### Where GIFs are Referenced

The generated GIFs are embedded in:

1. **README.md**
   - CLI menu demo
   - Setup demo
   - Database refresh demo
   - Python analyzer demo
   - CodeQL queries demo
   - SARIF analysis demo
   - Complete workflow demo

2. **docs/QUICKSTART.md**
   - Setup demo
   - CodeQL queries demo
   - Python analyzer demo

3. **docs/CLI_MENU_GUIDE.md**
   - CLI menu demo

4. **docs/DATABASE_REFRESH.md**
   - Database refresh demo

5. **docs/SARIF_ANALYSIS_QUICKSTART.md**
   - SARIF analysis demo

### Updating Documentation References

When regenerating demos, ensure documentation paths are correct:

```markdown
![Description](../demos/01-setup.gif)
```

Use relative paths from the documentation file location.

## Troubleshooting

### VHS Not Found

```bash
# Verify installation
which vhs

# Add Go bin to PATH if needed
export PATH=$PATH:$(go env GOPATH)/bin
```

### GIF Generation Fails

Common issues:
1. **Missing ffmpeg**: Install with `sudo apt-get install ffmpeg`
2. **Missing ttyd**: Install with `sudo apt-get install ttyd`
3. **Syntax errors**: Check tape file syntax
4. **Timeout**: Increase Sleep durations in tape

### GIF Quality Issues

Adjust settings in tape files:
- Increase `FontSize` for readability
- Adjust `Width` and `Height` for better aspect ratio
- Change `Theme` for different color schemes
- Modify `TypingSpeed` for faster/slower animations

## Best Practices

### Tape File Design

1. **Keep demos focused**: Each tape covers one specific use case
2. **Use consistent timing**: Standard Sleep durations for predictability
3. **Add comments**: Document sections with comments in tape
4. **Show output clearly**: Allow time for output to be visible
5. **Realistic demonstration**: Mimic actual user workflows

### GIF Optimization

Current settings balance quality and file size:
- **Font size**: 16pt (larger, more readable)
- **Dimensions**: 1000x720px (20% taller for more content visibility)
- **Theme**: TokyoNight (modern, developer-friendly theme)
- **Typing speed**: 80ms (20% faster than before)
- **Window bar**: ColorfulRight (adds visual polish)
- **Demo approach**: Shows only actual command execution - no typed comments or expected outputs
- **Environment**: Uses Hide/Show to set proper working directory without displaying it
- **Sleep times**: Longer sleeps for long-running commands (8-15s) to ensure completion

### Version Control

**Include in repository**:
- VHS tape files (tests/vhs/*.tape)
- Generated GIFs (demos/*.gif)
- Generation script (tests/generate-vhs-demos.sh)
- Documentation with references

**Exclude from repository**:
- Temporary VHS cache files
- Work-in-progress demos not ready for commit

## CI/CD Integration

### Automated Generation

Consider automating demo generation in CI:

```yaml
# GitHub Actions example
- name: Generate VHS Demos
  run: |
    go install github.com/charmbracelet/vhs@latest
    ./tests/generate-vhs-demos.sh
    
- name: Check for Changes
  run: |
    git diff --exit-code demos/
```

### Validation

Validate demos haven't broken:
1. Check GIF files are generated
2. Verify file sizes are reasonable
3. Ensure no syntax errors in tapes

## Additional Resources

- [VHS Documentation](https://github.com/charmbracelet/vhs)
- [VHS Examples](https://github.com/charmbracelet/vhs/tree/main/examples)
- [Catppuccin Theme](https://github.com/catppuccin/catppuccin)

## Support

For issues with VHS tests:
1. Check this guide for troubleshooting
2. Review VHS documentation
3. Open an issue on the SpeQL repository
4. Include error messages and tape file contents

## License

VHS tests and demos are part of the SpeQL project and subject to the same license terms.
