#!/usr/bin/env bash
set -euo pipefail

# Set CodeQL environment variable to suppress installation path warnings
if [ -z "${CODEQL_ALLOW_INSTALLATION_ANYWHERE:-}" ]; then
    export CODEQL_ALLOW_INSTALLATION_ANYWHERE=true
fi

# SpeQL Database Refresh Script
# Clones/updates an API spec source repository and rebuilds the CodeQL database.
# The source repository and related paths are driven by a JSON source config file
# (default: config/sources/azure.json).  Pass --source-config to use a different
# source — see docs/ADDING_API_SOURCES.md for how to create one.

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ---------------------------------------------------------------------------
# Helper: read a field from a JSON source config using Python (no jq needed)
# ---------------------------------------------------------------------------
_json_field() {
    local file="$1"
    local field="$2"
    local default="$3"
    python3 -c "
import json
import sys
try:
    cfg = json.load(open('$file'))
    print(cfg.get('$field', '$default'))
except Exception:
    print('$default')
"
}

# ---------------------------------------------------------------------------
# Default source config
# ---------------------------------------------------------------------------
DEFAULT_SOURCE_CONFIG="config/sources/azure.json"
SOURCE_CONFIG=""

# These will be populated after parsing --source-config
REPO_URL=""
SPECS_DIR=""
DATABASE_DIR=""
DEFAULT_SPEC_PATH=""
SOURCE_NAME=""

CONFIG_FILE="config/SpeQL.yml"

# Function to print colored messages
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to display usage
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Refresh the SpeQL CodeQL database from an API spec source.

OPTIONS:
    -h, --help                  Show this help message
        --source-config PATH    Path to a source config JSON file
                                (default: $DEFAULT_SOURCE_CONFIG)
                                See docs/ADDING_API_SOURCES.md for the format.
    -f, --fresh                 Perform a fresh clone (removes existing directory)
    -u, --update                Update existing repo clone (default)
    -p, --path PATH             Spec subdirectory to include
                                (overrides source config default_spec_path)
    -a, --all                   Include all specifications in the source
    -b, --branch BRANCH         Branch to use (overrides source config source_branch)
        --skip-db-build         Skip CodeQL database build (only clone/update repo)
        --clean                 Clean existing database before rebuild

EXAMPLES:
    # Update repo and rebuild database (default: Azure, Logic Apps specs)
    $0

    # Use a custom source definition
    $0 --source-config config/sources/azure.json

    # Fresh clone and rebuild
    $0 --fresh

    # Build database for a specific spec path within the source
    $0 --path specification/keyvault

    # Build database for all specs in the source
    $0 --all

    # Just update the repo without rebuilding the database
    $0 --update --skip-db-build

EOF
    exit 0
}

# Function to check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."
    
    # Check for git
    if ! command -v git &> /dev/null; then
        print_error "git is not installed. Please install git first."
        exit 1
    fi
    
    # Check for python3 (required for source config parsing)
    if ! command -v python3 &> /dev/null; then
        print_error "python3 is not installed. Please install Python 3 first."
        exit 1
    fi
    
    # Check for CodeQL (only if we're building the database)
    if [ "$SKIP_DB_BUILD" = false ]; then
        if ! command -v codeql &> /dev/null; then
            print_error "CodeQL CLI is not installed."
            echo ""
            echo "To install CodeQL 2.20.2 (required version):"
            echo "1. Download from: https://github.com/github/codeql-cli-binaries/releases/tag/v2.20.2"
            echo "2. Extract and add to PATH"
            echo ""
            echo "Example:"
            echo "  wget https://github.com/github/codeql-cli-binaries/releases/download/v2.20.2/codeql-linux64.zip"
            echo "  unzip codeql-linux64.zip"
            echo "  export PATH=\"\$PATH:\$(pwd)/codeql\""
            echo ""
            echo "Note: CodeQL 2.23.x and newer have compatibility issues with JSON-only databases."
            echo "      Version 2.20.1 or 2.20.2 is required."
            echo ""
            echo "Alternatively, run with --skip-db-build to only update the repository."
            exit 1
        fi
        
        # Get and check CodeQL version
        codeql_version=$(codeql version | head -n1)
        print_success "CodeQL CLI found: $codeql_version"
        
        # Extract version number and check if 2.23 or newer
        if echo "$codeql_version" | grep -qE "2\.(2[3-9]|[3-9][0-9])\."; then
            print_warning "WARNING: CodeQL 2.23.x or newer detected."
            print_warning "CodeQL 2.23.x and newer have known compatibility issues with JSON-only databases."
            print_warning "If database creation fails, please downgrade to CodeQL 2.20.1 or 2.20.2."
            print_warning "Download: https://github.com/github/codeql-cli-binaries/releases/tag/v2.20.2"
            echo ""
        fi
    fi
    
    print_success "Prerequisites check complete"
}

# Function to load source config
load_source_config() {
    local cfg_file="${SOURCE_CONFIG:-$DEFAULT_SOURCE_CONFIG}"
    if [ ! -f "$cfg_file" ]; then
        print_warning "Source config not found: $cfg_file — using built-in Azure defaults"
        REPO_URL="https://github.com/Azure/azure-rest-api-specs.git"
        SPECS_DIR="azure-rest-api-specs"
        DATABASE_DIR="database/azure-api-db"
        DEFAULT_SPEC_PATH="specification/logic"
        SOURCE_NAME="Azure REST API Specifications"
        return
    fi

    REPO_URL=$(_json_field "$cfg_file" "repo_url" "https://github.com/Azure/azure-rest-api-specs.git")
    SPECS_DIR=$(_json_field "$cfg_file" "specs_dir" "azure-rest-api-specs")
    DATABASE_DIR=$(_json_field "$cfg_file" "database_dir" "database/azure-api-db")
    DEFAULT_SPEC_PATH=$(_json_field "$cfg_file" "default_spec_path" "specification/logic")
    SOURCE_NAME=$(_json_field "$cfg_file" "name" "API Specifications")
    print_info "Loaded source config: $cfg_file ($SOURCE_NAME)"
}

# Function to clone or update the source repo
manage_source_repo() {
    print_info "Managing spec repository: $REPO_URL"
    
    if [ "$FRESH_CLONE" = true ] && [ -d "$SPECS_DIR" ]; then
        print_warning "Removing existing directory '$SPECS_DIR' for fresh clone..."
        rm -rf "$SPECS_DIR"
    fi
    
    if [ -d "$SPECS_DIR/.git" ]; then
        print_info "Updating existing spec repository in '$SPECS_DIR'..."
        cd "$SPECS_DIR"
        
        # Fetch latest changes
        git fetch origin "$BRANCH"
        
        # Reset to latest
        git reset --hard "origin/$BRANCH"
        
        # Clean untracked files
        git clean -fdx
        
        cd ..
        print_success "Repository updated to latest version"
    else
        print_info "Cloning spec repository (this may take a few minutes)..."
        
        # Clone with depth to speed up
        if [ "$INCLUDE_ALL" = true ]; then
            git clone --depth 1 --branch "$BRANCH" "$REPO_URL" "$SPECS_DIR"
        else
            # Sparse checkout for specific paths
            git clone --depth 1 --branch "$BRANCH" --filter=blob:none --sparse "$REPO_URL" "$SPECS_DIR"
            cd "$SPECS_DIR"
            git sparse-checkout set "$SPEC_PATH"
            cd ..
        fi
        
        print_success "Repository cloned successfully"
    fi
    
    # Display stats
    if [ -d "$SPECS_DIR" ]; then
        local json_count=$(find "$SPECS_DIR/$SPEC_PATH" -name "*.json" 2>/dev/null | wc -l)
        print_info "Found $json_count JSON files in $SPEC_PATH"
    fi
}

# Function to build CodeQL database
build_codeql_database() {
    print_info "Building CodeQL database..."
    
    # Clean existing database if requested
    if [ "$CLEAN_DB" = true ] && [ -d "$DATABASE_DIR" ]; then
        print_warning "Cleaning existing database..."
        rm -rf "$DATABASE_DIR"
    fi
    
    # Create source directory for CodeQL
    local source_path="$SPECS_DIR/$SPEC_PATH"
    
    if [ ! -d "$source_path" ]; then
        print_error "Source path does not exist: $source_path"
        exit 1
    fi
    
    # Build the database
    print_info "Creating CodeQL database from $source_path..."
    
    # Remove old database if it exists
    if [ -d "$DATABASE_DIR" ]; then
        print_info "Removing old database..."
        rm -rf "$DATABASE_DIR"
    fi
    
    # Ensure parent directory exists (Git doesn't track empty directories)
    mkdir -p "$(dirname "$DATABASE_DIR")"
    
    # Create database with JavaScript extractor (JSON is analyzed as JavaScript)
    # Use --codescanning-config to specify which files to index (JSON files)
    # The warning "Only found JavaScript or TypeScript files that were empty..." is expected
    # but harmless - the JSON files are still indexed correctly
    codeql database create "$DATABASE_DIR" \
        --language=javascript \
        --source-root="$source_path" \
        --codescanning-config="$CONFIG_FILE" \
        --overwrite \
        2>&1 | tee /tmp/codeql-build.log || {
            print_error "Failed to create CodeQL database"
            print_info "Check /tmp/codeql-build.log for details"
            exit 1
        }
    
    print_success "CodeQL database created successfully"
    
    # Create src.zip for analyze.py compatibility
    print_info "Creating src.zip for analyzer compatibility..."
    if [ -d "$DATABASE_DIR/src" ]; then
        cd "$DATABASE_DIR"
        zip -r src.zip src/ > /dev/null 2>&1
        cd - > /dev/null
        print_success "Created src.zip"
    fi
    
    # Display database info
    print_info "Database information:"
    codeql database info "$DATABASE_DIR" || true
}

# Function to verify database
verify_database() {
    print_info "Verifying database..."
    
    if [ ! -d "$DATABASE_DIR" ]; then
        print_error "Database directory does not exist: $DATABASE_DIR"
        return 1
    fi
    
    if [ ! -f "$DATABASE_DIR/codeql-database.yml" ]; then
        print_error "Database appears to be invalid (missing codeql-database.yml)"
        return 1
    fi
    
    # Check if src.zip exists for analyze.py
    if [ ! -f "$DATABASE_DIR/src.zip" ] && [ -d "$DATABASE_DIR/src" ]; then
        print_warning "src.zip not found, creating it..."
        cd "$DATABASE_DIR"
        zip -r src.zip src/ > /dev/null 2>&1
        cd - > /dev/null
    fi
    
    print_success "Database verification complete"
    return 0
}

# Parse command line arguments
FRESH_CLONE=false
UPDATE_REPO=true
SPEC_PATH_OVERRIDE=""
INCLUDE_ALL=false
BRANCH_OVERRIDE=""
SKIP_DB_BUILD=false
CLEAN_DB=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            ;;
        --source-config)
            SOURCE_CONFIG="$2"
            shift 2
            ;;
        -f|--fresh)
            FRESH_CLONE=true
            shift
            ;;
        -u|--update)
            UPDATE_REPO=true
            shift
            ;;
        -p|--path)
            SPEC_PATH_OVERRIDE="$2"
            shift 2
            ;;
        -a|--all)
            INCLUDE_ALL=true
            shift
            ;;
        -b|--branch)
            BRANCH_OVERRIDE="$2"
            shift 2
            ;;
        --skip-db-build)
            SKIP_DB_BUILD=true
            shift
            ;;
        --clean)
            CLEAN_DB=true
            shift
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Load source config (sets REPO_URL, SPECS_DIR, DATABASE_DIR, DEFAULT_SPEC_PATH, SOURCE_NAME)
load_source_config

# Apply overrides from CLI flags
BRANCH="${BRANCH_OVERRIDE:-$(_json_field "${SOURCE_CONFIG:-$DEFAULT_SOURCE_CONFIG}" source_branch main)}"

if [ "$INCLUDE_ALL" = true ]; then
    # Use the top-level spec root directory from default_spec_path
    SPEC_PATH=$(python3 -c "
from pathlib import Path
d = '$DEFAULT_SPEC_PATH'
print(Path(d).parts[0] if d else 'specification')
" 2>/dev/null || echo "specification")
elif [ -n "$SPEC_PATH_OVERRIDE" ]; then
    SPEC_PATH="$SPEC_PATH_OVERRIDE"
else
    SPEC_PATH="$DEFAULT_SPEC_PATH"
fi

# Main execution
main() {
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║         SpeQL - Database Refresh Utility                  ║"
    printf "║  Source: %-50s║\n" "$SOURCE_NAME"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    
    print_info "Configuration:"
    echo "  - Source: $SOURCE_NAME"
    echo "  - Repository: $REPO_URL"
    echo "  - Specs directory: $SPECS_DIR"
    echo "  - Database directory: $DATABASE_DIR"
    echo "  - Specification path: $SPEC_PATH"
    echo "  - Branch: $BRANCH"
    echo "  - Fresh clone: $FRESH_CLONE"
    echo "  - Skip DB build: $SKIP_DB_BUILD"
    echo ""
    
    # Check prerequisites
    check_prerequisites
    
    # Manage source repo
    manage_source_repo
    
    # Build database if not skipped
    if [ "$SKIP_DB_BUILD" = false ]; then
        build_codeql_database
        verify_database
        
        echo ""
        print_success "Database refresh complete!"
        echo ""
        print_info "Next steps:"
        echo "  1. Run security analysis: python3 analyze.py"
        echo "  2. Run CodeQL queries: ./run-queries.sh"
        echo ""
    else
        print_success "Repository updated successfully (database build skipped)"
        echo ""
        print_info "To build the database, run: $0"
        echo ""
    fi
}

# Run main function
main

