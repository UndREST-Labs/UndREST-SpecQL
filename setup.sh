#!/bin/bash

# Set CodeQL environment variable to suppress installation path warnings
if [ -z "${CODEQL_ALLOW_INSTALLATION_ANYWHERE:-}" ]; then
    export CODEQL_ALLOW_INSTALLATION_ANYWHERE=true
fi

# SpeQL Setup Script
# This script automates the installation and configuration of SpeQL

set -e  # Exit on error

# Configuration
CODEQL_VERSION="2.20.2"
JAVASCRIPT_ALL_VERSION="0.9.4"
# Note: Manual library download from GitHub is discouraged due to version compatibility issues.
# The libraries in the main branch may contain syntax that CodeQL 2.20.2 cannot parse.
# It's strongly recommended to fix SSL certificate issues instead.
SHARED_PACKS="concepts dataflow controlflow mad regex ssa threat-models tutorial typetracking util xml yaml"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Helper function for download failure
handle_download_failure() {
    echo -e "${RED}✗ Failed to download CodeQL libraries${NC}"
    echo -e "${YELLOW}  Please check your internet connection and try again${NC}"
    echo -e "${YELLOW}  Or manually download from: https://github.com/github/codeql${NC}"
}

echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║    SpeQL - API Spec Query Analyser Setup                 ║${NC}"
echo -e "${GREEN}║         Azure REST API Security Analysis Tool            ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Step 1: Check and install JDK
echo -e "${YELLOW}Step 1: Checking Java Development Kit (JDK)...${NC}"
if command_exists java; then
    JAVA_VERSION=$(java -version 2>&1 | head -n 1)
    echo -e "${GREEN}✓ Java is already installed: ${JAVA_VERSION}${NC}"
else
    echo -e "${YELLOW}Java not found. Installing OpenJDK 11...${NC}"
    if command_exists apt-get; then
        sudo apt-get update
        sudo apt-get install -y openjdk-11-jdk
        echo -e "${GREEN}✓ OpenJDK 11 installed successfully${NC}"
    else
        echo -e "${RED}✗ apt-get not found. Please install JDK 11 or newer manually.${NC}"
        exit 1
    fi
fi
echo

# Step 2: Download and install CodeQL CLI
echo -e "${YELLOW}Step 2: Installing CodeQL CLI ${CODEQL_VERSION}...${NC}"
if command_exists codeql; then
    INSTALLED_VERSION=$(codeql version 2>&1 | head -n 1)
    echo -e "${GREEN}✓ CodeQL is already installed: ${INSTALLED_VERSION}${NC}"
else
    echo -e "${YELLOW}Downloading CodeQL CLI ${CODEQL_VERSION}...${NC}"
    
    # Create a temporary directory for download
    TEMP_DIR=$(mktemp -d)
    cd "$TEMP_DIR"
    
    # Download CodeQL
    wget -q "https://github.com/github/codeql-cli-binaries/releases/download/v${CODEQL_VERSION}/codeql-linux64.zip"
    
    # Extract to user's home directory
    unzip -q codeql-linux64.zip
    
    # Move to a permanent location
    if [ -d "$HOME/codeql" ]; then
        echo -e "${YELLOW}Removing existing ~/codeql directory...${NC}"
        rm -rf "$HOME/codeql"
    fi
    
    mv codeql "$HOME/"
    
    # Add to PATH in current session
    export PATH="$PATH:$HOME/codeql"
    
    # Add to user's shell profile
    SHELL_PROFILE=""
    if [ -f "$HOME/.bashrc" ]; then
        SHELL_PROFILE="$HOME/.bashrc"
    elif [ -f "$HOME/.bash_profile" ]; then
        SHELL_PROFILE="$HOME/.bash_profile"
    elif [ -f "$HOME/.zshrc" ]; then
        SHELL_PROFILE="$HOME/.zshrc"
    fi
    
    if [ -n "$SHELL_PROFILE" ]; then
        # Check if PATH already contains codeql
        if ! grep -q "export PATH.*codeql" "$SHELL_PROFILE"; then
            echo 'export PATH="$PATH:$HOME/codeql"' >> "$SHELL_PROFILE"
            echo -e "${GREEN}✓ Added CodeQL to PATH in ${SHELL_PROFILE}${NC}"
        fi
    fi
    
    # Clean up
    cd - > /dev/null
    rm -rf "$TEMP_DIR"
    
    echo -e "${GREEN}✓ CodeQL CLI ${CODEQL_VERSION} installed successfully${NC}"
    echo -e "${YELLOW}  Note: You may need to restart your shell or run: source ${SHELL_PROFILE}${NC}"
fi
echo

# Step 3: Install query pack dependencies
echo -e "${YELLOW}Step 3: Installing CodeQL query pack dependencies...${NC}"
if [ -d "queries/azure-security" ]; then
    cd queries/azure-security
    
    echo -e "${YELLOW}Running: codeql pack install .${NC}"
    if codeql pack install . 2>&1 | tee /tmp/pack_install.log; then
        cd ../..
        echo -e "${GREEN}✓ Query pack dependencies installed successfully${NC}"
        echo -e "${GREEN}  Dependencies installed to: ~/.codeql/packages/${NC}"
    else
        # Check if the error is due to SSL certificate issues
        if grep -q "SunCertPathBuilderException\|SSL\|certificate" /tmp/pack_install.log; then
            echo -e "${RED}✗ SSL certificate error detected during pack installation${NC}"
            echo -e "${YELLOW}  This is a known issue with certain network configurations.${NC}"
            echo
            echo -e "${RED}IMPORTANT: Manual library download is NOT recommended!${NC}"
            echo -e "${YELLOW}  Libraries from GitHub main branch may be incompatible with CodeQL ${CODEQL_VERSION}${NC}"
            echo -e "${YELLOW}  and can cause 'token recognition error' when parsing newer syntax.${NC}"
            echo
            echo -e "${GREEN}Recommended solutions (in order of preference):${NC}"
            echo -e "${GREEN}  1. Update system certificates: sudo update-ca-certificates${NC}"
            echo -e "${GREEN}  2. Use newer Java version (JDK 17 or 21) with updated CA certificates${NC}"
            echo -e "${GREEN}  3. Configure corporate proxy if behind one${NC}"
            echo -e "${GREEN}  4. Contact your system administrator to resolve SSL issues${NC}"
            echo
            read -p "Do you want to attempt manual download anyway? (y/N) " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                echo -e "${YELLOW}Setup cancelled. Please resolve SSL certificate issues and try again.${NC}"
                cd "$REPO_ROOT"
                exit 1
            fi
            
            echo -e "${YELLOW}⚠ WARNING: Proceeding with manual download at your own risk...${NC}"
            echo -e "${YELLOW}  If you encounter 'token recognition error' later, you'll need to${NC}"
            echo -e "${YELLOW}  resolve the SSL issue and use 'codeql pack install' instead.${NC}"
            echo
            
            # Create a temporary directory for manual download
            TEMP_DIR=$(mktemp -d)
            REPO_ROOT=$(pwd)
            cd "$TEMP_DIR"
            
            echo -e "${YELLOW}Attempting to download CodeQL libraries from GitHub...${NC}"
            # Try to download from main branch (may have compatibility issues)
            if wget -q https://github.com/github/codeql/archive/refs/heads/main.zip 2>/dev/null; then
                unzip -q main.zip
                CODEQL_DIR="codeql-main"
            else
                handle_download_failure
                cd "$REPO_ROOT"
                rm -rf "$TEMP_DIR"
                exit 1
            fi
            
            # Verify download was successful
            if [ ! -d "$CODEQL_DIR" ]; then
                echo -e "${RED}✗ CodeQL directory not found after extraction${NC}"
                cd "$REPO_ROOT"
                rm -rf "$TEMP_DIR"
                exit 1
            fi
            
            # Create package directories
            mkdir -p ~/.codeql/packages/codeql/javascript-all/${JAVASCRIPT_ALL_VERSION}
            
            # Copy JavaScript libraries
            echo -e "${YELLOW}  Installing javascript-all ${JAVASCRIPT_ALL_VERSION}...${NC}"
            if [ -d "$CODEQL_DIR/javascript/ql/lib" ]; then
                cp -r "$CODEQL_DIR/javascript/ql/lib"/* ~/.codeql/packages/codeql/javascript-all/${JAVASCRIPT_ALL_VERSION}/
            else
                echo -e "${RED}✗ JavaScript libraries not found in downloaded archive${NC}"
                cd "$REPO_ROOT"
                rm -rf "$TEMP_DIR"
                exit 1
            fi
            
            # Copy shared libraries
            echo -e "${YELLOW}  Installing shared libraries...${NC}"
            for pack in $SHARED_PACKS; do
                if [ -d "$CODEQL_DIR/shared/$pack" ]; then
                    VERSION=$(grep "^version:" "$CODEQL_DIR/shared/$pack/qlpack.yml" 2>/dev/null | awk '{print $2}' | sed 's/-dev$//')
                    if [ -n "$VERSION" ]; then
                        mkdir -p ~/.codeql/packages/codeql/$pack/$VERSION
                        cp -r "$CODEQL_DIR/shared/$pack"/* ~/.codeql/packages/codeql/$pack/$VERSION/
                        echo -e "${GREEN}    ✓ $pack $VERSION${NC}"
                    else
                        echo -e "${YELLOW}    ⚠ Could not determine version for $pack, skipping${NC}"
                    fi
                else
                    echo -e "${YELLOW}    ⚠ $pack not found, skipping${NC}"
                fi
            done
            
            cd "$REPO_ROOT"
            rm -rf "$TEMP_DIR"
            
            echo -e "${GREEN}✓ CodeQL libraries installed manually${NC}"
            echo
            echo -e "${RED}⚠ IMPORTANT WARNING:${NC}"
            echo -e "${YELLOW}  The manually installed libraries may be incompatible with CodeQL ${CODEQL_VERSION}${NC}"
            echo -e "${YELLOW}  If you see 'token recognition error' when running queries, you MUST:${NC}"
            echo -e "${YELLOW}    1. Remove manual libraries: rm -rf ~/.codeql/packages${NC}"
            echo -e "${YELLOW}    2. Fix SSL certificate issues (see README.md)${NC}"
            echo -e "${YELLOW}    3. Re-run this setup with: ./setup.sh${NC}"
            echo -e "${YELLOW}  The only reliable solution is to use 'codeql pack install'.${NC}"
            echo
            cd ../../
        else
            echo -e "${RED}✗ Pack installation failed with unexpected error${NC}"
            cat /tmp/pack_install.log
            cd ../../
            exit 1
        fi
    fi
else
    echo -e "${RED}✗ queries/azure-security directory not found${NC}"
    echo -e "${RED}  Please run this script from the SpeQL repository root${NC}"
    exit 1
fi
echo

# Step 4: Verify installation
echo -e "${YELLOW}Step 4: Verifying installation...${NC}"

# Check CodeQL version
echo -e "${YELLOW}CodeQL version:${NC}"
codeql version

# Check if JavaScript libraries are installed
echo
echo -e "${YELLOW}Checking installed CodeQL packages:${NC}"
if [ -d "$HOME/.codeql/packages/codeql/javascript-all" ]; then
    INSTALLED_VERSION=$(ls "$HOME/.codeql/packages/codeql/javascript-all" | head -n 1)
    echo -e "${GREEN}✓ codeql/javascript-all installed: version ${INSTALLED_VERSION}${NC}"
else
    echo -e "${RED}✗ codeql/javascript-all not found${NC}"
fi

# Check for qlpack.lock.yml
if [ -f "queries/azure-security/qlpack.lock.yml" ]; then
    echo -e "${GREEN}✓ Pack dependencies resolved (qlpack.lock.yml created)${NC}"
else
    echo -e "${YELLOW}⚠ qlpack.lock.yml not found${NC}"
fi

echo
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              Setup Complete!                              ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo
echo -e "${GREEN}You can now run SpeQL with:${NC}"
echo -e "  ${YELLOW}./run-queries.sh${NC}          # Run CodeQL security queries"
echo -e "  ${YELLOW}python3 analyze.py${NC}        # Run Python analyzer (no dependencies!)"
echo
echo -e "${GREEN}To analyze different Azure services:${NC}"
echo -e "  ${YELLOW}./refresh-database.sh --path specification/keyvault${NC}"
echo -e "  ${YELLOW}./refresh-database.sh --path specification/compute${NC}"
echo
