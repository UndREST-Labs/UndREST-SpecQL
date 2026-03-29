#!/usr/bin/env python3
"""
SpeQL Database Refresh Script
Refreshes the CodeQL database from a configured API spec source.

By default it uses the Azure REST API specifications, but any source can be
specified via --source-config.  Source definitions live in config/sources/ as
JSON files (e.g. config/sources/azure.json).
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

# Set CodeQL environment variable to suppress installation path warnings
if 'CODEQL_ALLOW_INSTALLATION_ANYWHERE' not in os.environ:
    os.environ['CODEQL_ALLOW_INSTALLATION_ANYWHERE'] = 'true'

# ANSI color codes
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color

# ---------------------------------------------------------------------------
# Default source configuration (Azure) — overridden by --source-config
# ---------------------------------------------------------------------------
_DEFAULT_SOURCE_CONFIG = Path(__file__).parent / "config" / "sources" / "azure.json"

_FALLBACK_SOURCE = {
    "id": "azure",
    "name": "Azure REST API Specifications",
    "repo_url": "https://github.com/Azure/azure-rest-api-specs.git",
    "specs_dir": "azure-rest-api-specs",
    "database_dir": "database/azure-api-db",
    "default_spec_path": "specification/logic",
    "source_repo": "Azure/azure-rest-api-specs",
    "source_branch": "main",
}

CONFIG_FILE = "config/SpeQL.yml"


def _load_source_config(config_path: Optional[str]) -> dict:
    """Load a source config JSON file.  Falls back to the built-in Azure config."""
    path = Path(config_path) if config_path else _DEFAULT_SOURCE_CONFIG
    try:
        with open(path, "r", encoding="utf-8") as fh:
            cfg = json.load(fh)
        if not isinstance(cfg, dict):
            raise ValueError("Source config must be a JSON object")
        return cfg
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"{YELLOW}[WARNING]{NC} Could not load source config '{path}': {exc}")
        print(f"{YELLOW}[WARNING]{NC} Falling back to built-in Azure defaults")
        return dict(_FALLBACK_SOURCE)


# These module-level names are kept for backward compatibility with code that
# imports them directly.  They are set after argument parsing in main().
SPECS_DIR: str = _FALLBACK_SOURCE["specs_dir"]
DATABASE_DIR: str = _FALLBACK_SOURCE["database_dir"]
DEFAULT_SPEC_PATH: str = _FALLBACK_SOURCE["default_spec_path"]


def print_info(message: str):
    """Print info message"""
    print(f"{BLUE}[INFO]{NC} {message}")


def print_success(message: str):
    """Print success message"""
    print(f"{GREEN}[SUCCESS]{NC} {message}")


def print_warning(message: str):
    """Print warning message"""
    print(f"{YELLOW}[WARNING]{NC} {message}")


def print_error(message: str):
    """Print error message"""
    print(f"{RED}[ERROR]{NC} {message}")


def check_command(command: str) -> bool:
    """Check if a command is available"""
    return shutil.which(command) is not None


def run_command(cmd: list, cwd: Optional[str] = None, capture: bool = False) -> tuple:
    """Run a shell command"""
    try:
        if capture:
            result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=True)
            return True, result.stdout
        else:
            result = subprocess.run(cmd, cwd=cwd, check=True)
            return True, ""
    except subprocess.CalledProcessError as e:
        return False, str(e)


def check_prerequisites(skip_codeql: bool = False) -> bool:
    """Check if required tools are installed"""
    print_info("Checking prerequisites...")
    
    # Check git
    if not check_command("git"):
        print_error("git is not installed. Please install git first.")
        return False
    
    # Check CodeQL if needed
    if not skip_codeql:
        if not check_command("codeql"):
            print_error("CodeQL CLI is not installed.")
            print("")
            print("To install CodeQL 2.20.2 (required version):")
            print("1. Download from: https://github.com/github/codeql-cli-binaries/releases/tag/v2.20.2")
            print("2. Extract and add to PATH")
            print("")
            print("Example:")
            print("  wget https://github.com/github/codeql-cli-binaries/releases/download/v2.20.2/codeql-linux64.zip")
            print("  unzip codeql-linux64.zip")
            print("  export PATH=\"$PATH:$(pwd)/codeql\"")
            print("")
            print("Note: CodeQL 2.23.x and newer have compatibility issues with JSON-only databases.")
            print("      Version 2.20.1 or 2.20.2 is required.")
            print("")
            print("Alternatively, run with --skip-db-build to only update the repository.")
            return False
        
        # Get CodeQL version
        success, output = run_command(["codeql", "version"], capture=True)
        if success:
            version = output.strip().split('\n')[0]
            print_success(f"CodeQL CLI found: {version}")
            
            # Extract version number and check
            version_match = re.search(r'(\d+)\.(\d+)\.(\d+)', version)
            if version_match:
                major, minor, patch = map(int, version_match.groups())
                if major == 2 and minor >= 23:
                    print_warning(f"WARNING: CodeQL {major}.{minor}.{patch} detected.")
                    print_warning("CodeQL 2.23.x and newer have known compatibility issues with JSON-only databases.")
                    print_warning("If database creation fails, please downgrade to CodeQL 2.20.1 or 2.20.2.")
                    print_warning("Download: https://github.com/github/codeql-cli-binaries/releases/tag/v2.20.2")
                    print("")
    
    print_success("Prerequisites check complete")
    return True


def manage_source_repo(
    repo_url: str,
    specs_dir: str,
    fresh: bool,
    branch: str,
    spec_path: str,
    include_all: bool,
) -> bool:
    """Clone or update an API spec source repository."""
    print_info(f"Managing spec repository: {repo_url}")

    specs_path = Path(specs_dir)

    # Handle fresh clone
    if fresh and specs_path.exists():
        print_warning(f"Removing existing repo directory '{specs_dir}' for fresh clone...")
        shutil.rmtree(specs_path)

    # Update existing repo
    if (specs_path / ".git").exists():
        print_info(f"Updating existing spec repository in '{specs_dir}'...")

        # Fetch latest
        success, _ = run_command(["git", "fetch", "origin", branch], cwd=specs_dir)
        if not success:
            print_error("Failed to fetch from remote")
            return False

        # Reset to latest
        success, _ = run_command(["git", "reset", "--hard", f"origin/{branch}"], cwd=specs_dir)
        if not success:
            print_error("Failed to reset to latest version")
            return False

        # Clean untracked files
        run_command(["git", "clean", "-fdx"], cwd=specs_dir)

        print_success("Repository updated to latest version")
    else:
        print_info("Cloning spec repository (this may take a few minutes)...")

        if include_all:
            # Full clone with depth 1
            success, _ = run_command([
                "git", "clone", "--depth", "1", "--branch", branch,
                repo_url, specs_dir,
            ])
        else:
            # Sparse checkout for specific path
            success, _ = run_command([
                "git", "clone", "--depth", "1", "--branch", branch,
                "--filter=blob:none", "--sparse",
                repo_url, specs_dir,
            ])

            if success:
                success, _ = run_command(
                    ["git", "sparse-checkout", "set", spec_path],
                    cwd=specs_dir,
                )

        if not success:
            print_error("Failed to clone repository")
            return False

        print_success("Repository cloned successfully")

    # Display stats
    spec_full_path = specs_path / spec_path
    if spec_full_path.exists():
        json_files = list(spec_full_path.rglob("*.json"))
        print_info(f"Found {len(json_files)} JSON files in {spec_path}")

    return True


# Backward-compatible alias
def manage_azure_repo(fresh: bool, branch: str, spec_path: str, include_all: bool) -> bool:
    """Clone or update Azure REST API specs repository (backward-compatible wrapper)."""
    return manage_source_repo(
        repo_url=_FALLBACK_SOURCE["repo_url"],
        specs_dir=SPECS_DIR,
        fresh=fresh,
        branch=branch,
        spec_path=spec_path,
        include_all=include_all,
    )


def _finalize_json_database(db_path: Path) -> None:
    """Finalize a JSON-only CodeQL database when codeql database create exits non-zero.

    CodeQL 2.23+ cannot cleanly finalize JavaScript databases that contain only JSON
    files (the JS extractor treats them as empty JS). The TRAP files are still written
    correctly, so we import them into a raw dataset and patch the YAML to mark the
    database as finalized so that codeql query run / database analyze can use it.
    """
    import shutil as _shutil

    # Find the JavaScript dbscheme bundled with the installed CodeQL CLI
    codeql_bin = shutil.which("codeql") or ""
    codeql_root = Path(codeql_bin).parent if codeql_bin else Path("")
    dbscheme = codeql_root / "javascript" / "semmlecode.javascript.dbscheme"

    dataset_dir = db_path / "db-javascript"
    trap_dir = db_path / "trap" / "javascript"

    if dataset_dir.exists():
        _shutil.rmtree(dataset_dir)
    dataset_dir.mkdir(parents=True)

    if dbscheme.exists():
        success, _ = run_command([
            "codeql", "dataset", "import",
            f"--dbscheme={dbscheme}",
            str(dataset_dir),
            str(trap_dir),
        ])
        if success:
            print_success("Imported TRAP files into dataset")
        else:
            print_warning("TRAP import had warnings (database may still be usable)")
    else:
        print_warning(f"dbscheme not found at {dbscheme}; skipping TRAP import")

    # Patch codeql-database.yml: remove inProgress block and mark as finalized
    yml_path = db_path / "codeql-database.yml"
    if yml_path.exists():
        lines = yml_path.read_text().splitlines()
        clean_lines: list[str] = []
        skip = False
        for line in lines:
            if line.startswith("inProgress:"):
                skip = True
                continue
            if skip and (line.startswith(" ") or line.startswith("\t")):
                continue
            skip = False
            if line.startswith("finalised:"):
                clean_lines.append("finalised: true")
            else:
                clean_lines.append(line)
        yml_path.write_text("\n".join(clean_lines) + "\n")

    print_success("Database finalized (CodeQL 2.23+ JSON-only compatibility mode)")


def build_codeql_database(spec_path: str, clean: bool, specs_dir: str = "", database_dir: str = "") -> bool:
    """Build CodeQL database from specs.

    Args:
        spec_path:    Subdirectory within *specs_dir* to index.
        clean:        Whether to remove any pre-existing database first.
        specs_dir:    Root directory of the cloned spec repository.
                      Defaults to the module-level ``SPECS_DIR`` value.
        database_dir: Where to write the CodeQL database.
                      Defaults to the module-level ``DATABASE_DIR`` value.
    """
    print_info("Building CodeQL database...")

    _specs_dir = specs_dir or SPECS_DIR
    _database_dir = database_dir or DATABASE_DIR

    db_path = Path(_database_dir)
    source_path = Path(_specs_dir) / spec_path

    # Check source path
    if not source_path.exists():
        print_error(f"Source path does not exist: {source_path}")
        return False

    # Remove old database (either for clean rebuild or normal overwrite)
    if db_path.exists():
        if clean:
            print_warning("Cleaning existing database...")
        else:
            print_info("Removing old database...")
        shutil.rmtree(db_path)

    # Ensure parent directory exists (Git doesn't track empty directories)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Create database
    print_info(f"Creating CodeQL database from {source_path}...")
    # Use --codescanning-config to specify which files to index (JSON files)
    # The warning "Only found JavaScript or TypeScript files that were empty..." is expected
    # but harmless - the JSON files are still indexed correctly
    success, output = run_command([
        "codeql", "database", "create", _database_dir,
        "--language=javascript",
        f"--source-root={source_path}",
        f"--codescanning-config={CONFIG_FILE}",
        "--overwrite",
    ])

    if not success:
        # CodeQL 2.23+ exits non-zero for JSON-only databases ("Only found JavaScript or
        # TypeScript files that were empty or contained syntax errors"), but TRAP files
        # are still extracted and the database can be finalised manually.
        trap_dir = db_path / "trap" / "javascript"
        if trap_dir.exists() and any(trap_dir.iterdir()):
            print_warning("CodeQL exited with warnings (expected for JSON-only databases on CodeQL 2.23+)")
            print_info("TRAP files were extracted — completing database build manually...")
            _finalize_json_database(db_path)
        else:
            print_error("Failed to create CodeQL database")
            print_info("Check output for details")
            return False

    print_success("CodeQL database created successfully")

    # Create src.zip for analyze.py compatibility
    print_info("Creating src.zip for analyzer compatibility...")
    src_dir = db_path / "src"
    if src_dir.exists():
        import zipfile
        zip_path = db_path / "src.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in src_dir.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(src_dir.parent)
                    zipf.write(file_path, arcname)
        print_success("Created src.zip")

    # Display database info
    print_info("Database information:")
    run_command(["codeql", "database", "info", _database_dir])

    return True


def verify_database(database_dir: str = "") -> bool:
    """Verify database integrity.

    Args:
        database_dir: Path to the CodeQL database directory.
                      Defaults to the module-level ``DATABASE_DIR`` value.
    """
    print_info("Verifying database...")

    _database_dir = database_dir or DATABASE_DIR
    db_path = Path(_database_dir)

    if not db_path.exists():
        print_error(f"Database directory does not exist: {_database_dir}")
        return False

    if not (db_path / "codeql-database.yml").exists():
        print_error("Database appears to be invalid (missing codeql-database.yml)")
        return False

    # Check src.zip for analyze.py compatibility
    src_zip = db_path / "src.zip"
    src_dir = db_path / "src"
    if not src_zip.exists() and src_dir.exists():
        print_warning("src.zip not found, creating it...")
        import zipfile
        with zipfile.ZipFile(src_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in src_dir.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(src_dir.parent)
                    zipf.write(file_path, arcname)

    print_success("Database verification complete")
    return True


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Refresh the SpeQL CodeQL database from an API spec source",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Update repo and rebuild database (default: Azure Logic Apps specs)
  %(prog)s

  # Use a custom source definition
  %(prog)s --source-config config/sources/azure.json

  # Fresh clone and rebuild
  %(prog)s --fresh

  # Build database for a specific spec path within the source
  %(prog)s --path specification/keyvault

  # Build database for all specs in the source
  %(prog)s --all

  # Just update the repo without rebuilding database
  %(prog)s --update --skip-db-build
        """
    )

    parser.add_argument(
        '--source-config',
        default=None,
        metavar='PATH',
        help=(
            'Path to a source config JSON file (default: config/sources/azure.json). '
            'Source config files live in config/sources/ and define the repository URL, '
            'specs directory, database directory, and other source-specific settings. '
            'See docs/ADDING_API_SOURCES.md for how to create a new source config.'
        ),
    )
    parser.add_argument(
        '-f', '--fresh',
        action='store_true',
        help='Perform a fresh clone of the source repo (removes existing directory)'
    )
    parser.add_argument(
        '-u', '--update',
        action='store_true',
        help='Update existing repo clone (default)'
    )
    parser.add_argument(
        '-p', '--path',
        default=None,
        help='Spec subdirectory to include (overrides source config default_spec_path)'
    )
    parser.add_argument(
        '-a', '--all',
        action='store_true',
        help='Include all specifications in the source (uses the top-level spec root)'
    )
    parser.add_argument(
        '-b', '--branch',
        default=None,
        help='Branch to use (overrides source config source_branch; default: main)'
    )
    parser.add_argument(
        '--skip-db-build',
        action='store_true',
        help='Skip CodeQL database build (only clone/update repo)'
    )
    parser.add_argument(
        '--clean',
        action='store_true',
        help='Clean existing database before rebuild'
    )

    args = parser.parse_args()

    # Load source config
    cfg = _load_source_config(args.source_config)

    # Apply source config values as defaults (CLI args take precedence)
    source_name = cfg.get("name", "API Specifications")
    repo_url = cfg.get("repo_url", _FALLBACK_SOURCE["repo_url"])
    specs_dir = cfg.get("specs_dir", _FALLBACK_SOURCE["specs_dir"])
    database_dir = cfg.get("database_dir", _FALLBACK_SOURCE["database_dir"])
    default_spec_path = cfg.get("default_spec_path", _FALLBACK_SOURCE["default_spec_path"])
    branch = args.branch or cfg.get("source_branch", "main")

    # Derive final spec path
    if args.all:
        # --all walks the entire spec root; for Azure that is "specification/"
        # For other sources the root may differ — use the parent of default_spec_path
        spec_root = str(Path(default_spec_path).parts[0]) if default_spec_path else "specification"
        spec_path = spec_root
    else:
        spec_path = args.path or default_spec_path

    # Update module-level globals so that helper functions that still reference
    # them (e.g. build_codeql_database called without explicit args) work correctly.
    global SPECS_DIR, DATABASE_DIR, DEFAULT_SPEC_PATH
    SPECS_DIR = specs_dir
    DATABASE_DIR = database_dir
    DEFAULT_SPEC_PATH = default_spec_path

    # Print header
    print("╔════════════════════════════════════════════════════════════╗")
    print("║         SpeQL - Database Refresh Utility                  ║")
    print(f"║  Source: {source_name[:50]:<50}║")
    print("╚════════════════════════════════════════════════════════════╝")
    print()

    print_info("Configuration:")
    print(f"  - Source: {source_name}")
    print(f"  - Repository: {repo_url}")
    print(f"  - Specs directory: {specs_dir}")
    print(f"  - Database directory: {database_dir}")
    print(f"  - Specification path: {spec_path}")
    print(f"  - Branch: {branch}")
    print(f"  - Fresh clone: {args.fresh}")
    print(f"  - Skip DB build: {args.skip_db_build}")
    print()

    # Check prerequisites
    if not check_prerequisites(skip_codeql=args.skip_db_build):
        sys.exit(1)

    # Manage source repo
    if not manage_source_repo(repo_url, specs_dir, args.fresh, branch, spec_path, args.all):
        sys.exit(1)

    # Build database if not skipped
    if not args.skip_db_build:
        if not build_codeql_database(spec_path, args.clean, specs_dir, database_dir):
            sys.exit(1)

        if not verify_database(database_dir):
            sys.exit(1)

        print()
        print_success("Database refresh complete!")
        print()
        print_info("Next steps:")
        print("  1. Run security analysis: python3 analyze.py")
        print("  2. Run CodeQL queries: ./run-queries.sh")
        print()
    else:
        print_success("Repository updated successfully (database build skipped)")
        print()
        print_info(f"To build the database, run: {sys.argv[0]} (without --skip-db-build)")
        print()


if __name__ == "__main__":
    main()
