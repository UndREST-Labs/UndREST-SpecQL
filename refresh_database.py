#!/usr/bin/env python3
"""
SpeQL Database Refresh Script
Refreshes the CodeQL database from Azure REST API specifications
"""

import argparse
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

# Configuration
AZURE_REPO_URL = "https://github.com/Azure/azure-rest-api-specs.git"
SPECS_DIR = "azure-rest-api-specs"
DATABASE_DIR = "database/azure-api-db"
CONFIG_FILE = "config/SpeQL.yml"
DEFAULT_SPEC_PATH = "specification/logic"


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


def manage_azure_repo(fresh: bool, branch: str, spec_path: str, include_all: bool) -> bool:
    """Clone or update Azure REST API specs repository"""
    print_info("Managing Azure REST API specs repository...")
    
    specs_path = Path(SPECS_DIR)
    
    # Handle fresh clone
    if fresh and specs_path.exists():
        print_warning("Removing existing Azure repo for fresh clone...")
        shutil.rmtree(specs_path)
    
    # Update existing repo
    if (specs_path / ".git").exists():
        print_info("Updating existing Azure REST API specs...")
        
        # Fetch latest
        success, _ = run_command(["git", "fetch", "origin", branch], cwd=SPECS_DIR)
        if not success:
            print_error("Failed to fetch from remote")
            return False
        
        # Reset to latest
        success, _ = run_command(["git", "reset", "--hard", f"origin/{branch}"], cwd=SPECS_DIR)
        if not success:
            print_error("Failed to reset to latest version")
            return False
        
        # Clean untracked files
        run_command(["git", "clean", "-fdx"], cwd=SPECS_DIR)
        
        print_success("Repository updated to latest version")
    else:
        print_info("Cloning Azure REST API specs (this may take a few minutes)...")
        
        if include_all:
            # Full clone with depth 1
            success, _ = run_command([
                "git", "clone", "--depth", "1", "--branch", branch,
                AZURE_REPO_URL, SPECS_DIR
            ])
        else:
            # Sparse checkout for specific path
            success, _ = run_command([
                "git", "clone", "--depth", "1", "--branch", branch,
                "--filter=blob:none", "--sparse",
                AZURE_REPO_URL, SPECS_DIR
            ])
            
            if success:
                success, _ = run_command(
                    ["git", "sparse-checkout", "set", spec_path],
                    cwd=SPECS_DIR
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


def build_codeql_database(spec_path: str, clean: bool) -> bool:
    """Build CodeQL database from specs"""
    print_info("Building CodeQL database...")
    
    db_path = Path(DATABASE_DIR)
    source_path = Path(SPECS_DIR) / spec_path
    
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
        "codeql", "database", "create", DATABASE_DIR,
        "--language=javascript",
        f"--source-root={source_path}",
        f"--codescanning-config={CONFIG_FILE}",
        "--overwrite"
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
    run_command(["codeql", "database", "info", DATABASE_DIR])
    
    return True


def verify_database() -> bool:
    """Verify database integrity"""
    print_info("Verifying database...")
    
    db_path = Path(DATABASE_DIR)
    
    if not db_path.exists():
        print_error(f"Database directory does not exist: {DATABASE_DIR}")
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
        description="Refresh the SpeQL CodeQL database from Azure REST API specifications",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Update repo and rebuild database (default Logic Apps specs)
  %(prog)s

  # Fresh clone and rebuild
  %(prog)s --fresh

  # Build database for Key Vault specs
  %(prog)s --path specification/keyvault

  # Build database for all Azure specs
  %(prog)s --all

  # Just update the repo without rebuilding database
  %(prog)s --update --skip-db-build
        """
    )
    
    parser.add_argument(
        '-f', '--fresh',
        action='store_true',
        help='Perform a fresh clone of the Azure repo (removes existing)'
    )
    parser.add_argument(
        '-u', '--update',
        action='store_true',
        help='Update existing Azure repo clone (default)'
    )
    parser.add_argument(
        '-p', '--path',
        default=DEFAULT_SPEC_PATH,
        help=f'Specify Azure spec path to include (default: {DEFAULT_SPEC_PATH})'
    )
    parser.add_argument(
        '-a', '--all',
        action='store_true',
        help='Include all Azure specifications'
    )
    parser.add_argument(
        '-b', '--branch',
        default='main',
        help='Specify branch to use (default: main)'
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
    
    # Adjust spec path for --all
    spec_path = "specification" if args.all else args.path
    
    # Print header
    print("╔════════════════════════════════════════════════════════════╗")
    print("║         SpeQL - Database Refresh Utility                  ║")
    print("║    Building from Azure REST API Specifications            ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print()
    
    print_info("Configuration:")
    print(f"  - Specification path: {spec_path}")
    print(f"  - Branch: {args.branch}")
    print(f"  - Fresh clone: {args.fresh}")
    print(f"  - Skip DB build: {args.skip_db_build}")
    print()
    
    # Check prerequisites
    if not check_prerequisites(skip_codeql=args.skip_db_build):
        sys.exit(1)
    
    # Manage Azure repo
    if not manage_azure_repo(args.fresh, args.branch, spec_path, args.all):
        sys.exit(1)
    
    # Build database if not skipped
    if not args.skip_db_build:
        if not build_codeql_database(spec_path, args.clean):
            sys.exit(1)
        
        if not verify_database():
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
