#!/usr/bin/env python3
"""
SpeQL - API Spec Query Analyser for Azure REST API
Analyzes Azure REST API specifications to identify potential security vulnerabilities
"""

import json
import sys
import os
import re
import argparse
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from zipfile import ZipFile

# ANSI color codes
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color

# Pre-compiled regex patterns for efficiency
CONNECTION_STRING_PATTERN = re.compile(
    r'(?:server|database|password|accountkey|sharedaccesskey|connectionstring)=',
    re.IGNORECASE
)
CREDENTIAL_PATTERN = re.compile(r'password=.+[;&]|accountkey=.+', re.IGNORECASE)

class SecurityIssue:
    """Represents a security issue found in the analysis"""
    def __init__(self, severity: str, title: str, message: str, file_path: str, location: str = ""):
        self.severity = severity
        self.title = title
        self.message = message
        self.file_path = file_path
        self.location = location

    def __str__(self):
        color = RED if self.severity == "error" else YELLOW
        return f"{color}[{self.severity.upper()}]{NC} {self.title}\n  File: {self.file_path}\n  {self.message}\n"


class AzureSecurityAnalyzer:
    """Analyzes Azure API specifications for security issues"""
    
    def __init__(self):
        self.issues: List[SecurityIssue] = []
        
    def analyze_file(self, file_path: str, content: Dict[str, Any]):
        """Analyze a single JSON file for security issues"""
        # Check for insecure Logic App triggers
        self._check_logic_app_triggers(file_path, content)
        
        # Check for Key Vault misconfigurations
        self._check_key_vault_config(file_path, content)
        
        # Check for missing access control
        self._check_access_control(file_path, content)
        
        # Check for insecure credentials
        self._check_insecure_credentials(file_path, content)
    
    def _check_logic_app_triggers(self, file_path: str, content: Dict[str, Any]):
        """Check for insecure Logic App trigger configurations"""
        # Check workflow definitions
        if "definition" in content:
            definition = content.get("definition", {})
            triggers = definition.get("triggers", {})
            
            for trigger_name, trigger_config in triggers.items():
                trigger_type = trigger_config.get("type", "")
                
                # Check for HTTP triggers without authentication
                if trigger_type in ["Request", "HttpTrigger", "HTTP"]:
                    inputs = trigger_config.get("inputs", {})
                    
                    # Check if authentication is missing or weak
                    if "authentication" not in inputs:
                        self.issues.append(SecurityIssue(
                            "error",
                            "Insecure Logic App Trigger",
                            f"HTTP trigger '{trigger_name}' is missing authentication configuration, allowing unauthorized access",
                            file_path,
                            f"triggers.{trigger_name}"
                        ))
                    else:
                        auth = inputs.get("authentication", {})
                        auth_type = auth.get("type", "") if isinstance(auth, dict) else str(auth)
                        
                        if auth_type in ["None", "Anonymous", ""]:
                            self.issues.append(SecurityIssue(
                                "error",
                                "Weak Logic App Trigger Authentication",
                                f"HTTP trigger '{trigger_name}' uses weak or no authentication ({auth_type})",
                                file_path,
                                f"triggers.{trigger_name}.inputs.authentication"
                            ))
        
        # Check for enabled workflows without access control
        if content.get("properties", {}).get("state") == "Enabled":
            if "accessEndpoint" in content.get("properties", {}):
                access_control = content.get("properties", {}).get("accessControl", {})
                
                if not access_control or len(access_control) == 0:
                    self.issues.append(SecurityIssue(
                        "error",
                        "Workflow Without Access Control",
                        "Enabled workflow has public access endpoint but no access control configuration",
                        file_path,
                        "properties.accessControl"
                    ))
    
    def _check_key_vault_config(self, file_path: str, content: Dict[str, Any]):
        """Check for Key Vault misconfigurations (Azure Vault Recon)"""
        
        # Helper to recursively check for Key Vault references
        def has_keyvault_reference(obj: Any) -> bool:
            """Check if object contains Key Vault references"""
            if isinstance(obj, str):
                return ("keyvault" in obj.lower() or 
                       "vault.azure.net" in obj.lower() or 
                       "@Microsoft.KeyVault" in obj)
            elif isinstance(obj, dict):
                return any(has_keyvault_reference(v) for v in obj.values())
            elif isinstance(obj, list):
                return any(has_keyvault_reference(item) for item in obj)
            return False
        
        # Only check files that reference Key Vault
        if not has_keyvault_reference(content):
            return
        
        properties = content.get("properties", {})
        
        # Check for missing network restrictions
        if "networkAcls" not in properties and "networkRuleSet" not in properties:
            if has_keyvault_reference(properties):
                self.issues.append(SecurityIssue(
                    "error",
                    "Key Vault Without Network Restrictions",
                    "Key Vault configuration missing network restrictions, allowing access from any network",
                    file_path,
                    "properties"
                ))
        
        # Check for public network access
        if properties.get("publicNetworkAccess") == "Enabled":
            self.issues.append(SecurityIssue(
                "error",
                "Key Vault Public Access Enabled",
                "Key Vault allows public network access, potentially exposing secrets to unauthorized enumeration",
                file_path,
                "properties.publicNetworkAccess"
            ))
        
        # Check network ACLs default action
        network_acls = properties.get("networkAcls", {})
        if network_acls.get("defaultAction") == "Allow":
            self.issues.append(SecurityIssue(
                "error",
                "Permissive Key Vault Network ACL",
                "Key Vault network ACL default action is 'Allow', should be 'Deny' with explicit allowlists",
                file_path,
                "properties.networkAcls.defaultAction"
            ))
    
    def _check_access_control(self, file_path: str, content: Dict[str, Any]):
        """Check for missing access control in API endpoints"""
        # Check Swagger/OpenAPI specs
        if content.get("swagger") == "2.0" or "openapi" in content:
            paths = content.get("paths", {})
            global_security = content.get("security", [])
            
            for path, operations in paths.items():
                if not isinstance(operations, dict):
                    continue
                    
                for method, operation in operations.items():
                    if method.upper() not in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                        continue
                    
                    if not isinstance(operation, dict):
                        continue
                    
                    operation_id = operation.get("operationId", f"{method.upper()} {path}")
                    operation_security = operation.get("security", None)
                    
                    # Check if sensitive operation lacks security
                    is_sensitive = any(keyword in operation_id.lower() 
                                     for keyword in ["delete", "create", "update", "write", "admin"])
                    
                    # Operation has no security and no global security
                    if operation_security is None and not global_security:
                        if is_sensitive:
                            self.issues.append(SecurityIssue(
                                "error",
                                "Sensitive Operation Without Authentication",
                                f"Sensitive operation '{operation_id}' missing security requirements",
                                file_path,
                                f"paths.{path}.{method}"
                            ))
                    
                    # Security explicitly set to empty array
                    elif operation_security is not None and len(operation_security) == 0:
                        self.issues.append(SecurityIssue(
                            "error",
                            "API Endpoint With No Security",
                            f"Operation '{operation_id}' explicitly configured with no security (empty array)",
                            file_path,
                            f"paths.{path}.{method}.security"
                        ))
    
    def _check_insecure_credentials(self, file_path: str, content: Dict[str, Any]):
        """Check for hardcoded credentials and connection strings"""
        
        def check_object(obj: Any, path: str = "", depth: int = 0):
            """Recursively check object for credentials with depth limit"""
            # Prevent stack overflow on deeply nested structures
            if depth > 50:
                return
                
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key
                    
                    # Check if key suggests sensitive data
                    if any(sensitive in key.lower() for sensitive in 
                          ["password", "secret", "apikey", "api_key", "connectionstring", 
                           "accountkey", "sharedkey", "accesskey"]):
                        
                        if isinstance(value, str) and value and len(value) > 10:
                            # Check if it's a Key Vault reference (secure)
                            if not ("@Microsoft.KeyVault" in value or "${keyvault:" in value):
                                self.issues.append(SecurityIssue(
                                    "error",
                                    "Hardcoded Credential",
                                    f"Hardcoded credential found in property '{key}'. Use Azure Key Vault instead.",
                                    file_path,
                                    current_path
                                ))
                    
                    # Check for connection strings
                    if isinstance(value, str):
                        if CONNECTION_STRING_PATTERN.search(value):
                            if CREDENTIAL_PATTERN.search(value):
                                if not ("@Microsoft.KeyVault" in value or "${keyvault:" in value):
                                    self.issues.append(SecurityIssue(
                                        "error",
                                        "Insecure Connection String",
                                        f"Connection string with embedded credentials in property '{key}'. Use Key Vault reference.",
                                        file_path,
                                        current_path
                                    ))
                    
                    # Check securestring with default values
                    if key == "type" and value == "securestring":
                        parent_obj = obj
                        if "defaultValue" in parent_obj:
                            default = parent_obj["defaultValue"]
                            if default and not ("@Microsoft.KeyVault" in str(default)):
                                self.issues.append(SecurityIssue(
                                    "error",
                                    "Visible Secure String",
                                    "Secure string parameter has visible default value. Should be retrieved from Key Vault.",
                                    file_path,
                                    current_path
                                ))
                    
                    # Recurse with incremented depth
                    check_object(value, current_path, depth + 1)
                    
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    check_object(item, f"{path}[{i}]", depth + 1)
        
        check_object(content)
    
    def analyze_directory(self, directory: Path):
        """Analyze all JSON files in a directory"""
        json_files = list(directory.rglob("*.json"))
        
        print(f"Analyzing {len(json_files)} JSON files...")
        
        # List of encodings to try in order
        encodings = ['utf-8-sig', 'utf-8', 'latin-1']
        
        for json_file in json_files:
            try:
                content = None
                for encoding in encodings:
                    try:
                        with open(json_file, 'r', encoding=encoding) as f:
                            content = json.load(f)
                        break  # Success, exit encoding loop
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        continue  # Try next encoding
                
                if content is None:
                    raise ValueError(f"Could not decode file with any supported encoding")
                
                relative_path = json_file.relative_to(directory)
                self.analyze_file(str(relative_path), content)
            except Exception as e:
                print(f"{YELLOW}Warning: Could not analyze {json_file}: {e}{NC}")
    
    def print_results(self):
        """Print analysis results"""
        if not self.issues:
            print(f"\n{GREEN}✓ No security issues found!{NC}\n")
            return
        
        print(f"\n{RED}✗ Found {len(self.issues)} security issue(s):{NC}\n")
        
        # Group by severity
        errors = [i for i in self.issues if i.severity == "error"]
        warnings = [i for i in self.issues if i.severity == "warning"]
        
        if errors:
            print(f"{RED}Errors: {len(errors)}{NC}")
            for issue in errors:
                print(issue)
        
        if warnings:
            print(f"{YELLOW}Warnings: {len(warnings)}{NC}")
            for issue in warnings:
                print(issue)
        
        print(f"\n{'═' * 60}")
        print(f"Total issues: {len(self.issues)}")
        print(f"{'═' * 60}\n")


def validate_zip_file(zip_path: Path) -> bool:
    """Validate that the zip file is correct and contains expected content"""
    try:
        with ZipFile(zip_path, 'r') as zip_ref:
            # Check if zip is valid
            if zip_ref.testzip() is not None:
                print(f"{RED}Error: {zip_path} is corrupted{NC}")
                return False
            
            # Get list of files in zip
            file_list = zip_ref.namelist()
            
            # Must contain JSON files
            has_json = any(f.endswith('.json') for f in file_list)
            
            if not has_json:
                print(f"{YELLOW}Warning: {zip_path} contains no JSON files{NC}")
                return False
            
            # Print diagnostic information
            json_count = sum(1 for f in file_list if f.endswith('.json'))
            print(f"{BLUE}Zip file validation:{NC}")
            print(f"  - Total files: {len(file_list)}")
            print(f"  - JSON files: {json_count}")
            
            # Show top-level directories
            top_dirs = set()
            for f in file_list:
                if '/' in f:
                    first_dir = f.split('/')[0]
                    top_dirs.add(first_dir)
            if top_dirs:
                print(f"  - Top-level directories: {', '.join(sorted(top_dirs)[:5])}")
            
            return True
            
    except Exception as e:
        print(f"{RED}Error: Cannot read {zip_path}: {e}{NC}")
        return False


def find_specs_directory(db_path: Path) -> Path:
    """Find directory containing JSON specification files"""
    # Check known directories first
    for dir_name in ['mnt', 'src', 'specification']:
        dir_path = db_path / dir_name
        if dir_path.exists() and any(dir_path.rglob("*.json")):
            return dir_path
    
    # Search for any subdirectory with JSON files
    for item in db_path.iterdir():
        if item.is_dir() and item.name not in ['db-javascript', 'diagnostic', 'log', 'temp']:
            if any(item.rglob("*.json")):
                return item
    
    return None


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="SpeQL - Security analyzer for Azure REST API specifications",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze from database (default)
  %(prog)s
  
  # Analyze from azure-rest-api-specs repository
  %(prog)s --source azure-rest-api-specs/specification
  
  # Analyze a specific path in azure-rest-api-specs
  %(prog)s --source azure-rest-api-specs/specification/logic
  
  # Analyze with verbose output
  %(prog)s --verbose
        """
    )
    
    parser.add_argument(
        '-s', '--source',
        type=str,
        default=None,
        help='Path to Azure specifications directory (default: use database/azure-api-db)'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output with additional diagnostics'
    )
    
    return parser.parse_args()


def main():
    """Main entry point"""
    args = parse_arguments()
    
    print("═" * 60)
    print("  SpeQL - API Spec Query Analyser")
    print("  Identifying security vulnerabilities in Azure REST API")
    print("═" * 60)
    print()
    
    # Determine source directory
    if args.source:
        # User specified a custom source directory
        source_path = Path(args.source)
        if not source_path.exists():
            print(f"{RED}Error: Specified source path does not exist: {source_path}{NC}")
            sys.exit(1)
        
        json_count = sum(1 for _ in source_path.rglob("*.json"))
        print(f"{BLUE}Diagnostics:{NC}")
        print(f"  - Source mode: Custom directory")
        print(f"  - Source path: {source_path.absolute()}")
        print(f"  - JSON files found: {json_count:,}")
        print()
        
        if json_count == 0:
            print(f"{RED}Error: No JSON files found in source path{NC}")
            sys.exit(1)
        
        # Analyze the custom source directly
        analyzer = AzureSecurityAnalyzer()
        print(f"{BLUE}Analyzing specifications from: {source_path.name}/{NC}")
        analyzer.analyze_directory(source_path)
        analyzer.print_results()
        
        # Exit with error code if issues found
        if analyzer.issues:
            sys.exit(1)
        sys.exit(0)
    
    # Default behavior: use database
    db_path = Path("database/azure-api-db")
    src_zip = db_path / "src.zip"
    
    # Diagnostic information
    print(f"{BLUE}Diagnostics:{NC}")
    print(f"  - Source mode: Database")
    print(f"  - Database path: {db_path.absolute()}")
    print(f"  - Database exists: {db_path.exists()}")
    print(f"  - src.zip exists: {src_zip.exists()}")
    if src_zip.exists():
        print(f"  - src.zip size: {src_zip.stat().st_size:,} bytes")
    
    # Check for azure-rest-api-specs repository
    azure_specs_path = Path("azure-rest-api-specs/specification")
    if azure_specs_path.exists() and args.verbose:
        azure_json_count = sum(1 for _ in azure_specs_path.rglob("*.json"))
        print(f"  - azure-rest-api-specs found: {azure_json_count:,} JSON files")
        print(f"    (Use --source azure-rest-api-specs/specification to analyze all)")
    
    # Find any directory with specs
    extracted_dir = find_specs_directory(db_path)
    if extracted_dir:
        json_count = sum(1 for _ in extracted_dir.rglob("*.json"))
        print(f"  - Found specifications in: {extracted_dir.name}/")
        print(f"  - JSON files in database: {json_count}")
    else:
        print(f"  - No specification directories found")
    print()
    
    # Check if extraction is needed
    needs_extraction = extracted_dir is None
    
    if needs_extraction:
        print(f"{YELLOW}Specification directory not found, extraction needed{NC}")
        
        if not src_zip.exists():
            print(f"{RED}Error: Cannot extract - {src_zip} not found{NC}")
            print()
            
            # Check if azure-rest-api-specs exists
            azure_specs_path = Path("azure-rest-api-specs/specification")
            if azure_specs_path.exists():
                azure_json_count = sum(1 for _ in azure_specs_path.rglob("*.json"))
                print(f"{YELLOW}Note: azure-rest-api-specs repository found with {azure_json_count:,} JSON files.{NC}")
                print(f"{YELLOW}To analyze these files, run:{NC}")
                print(f"  python3 analyze.py --source azure-rest-api-specs/specification")
                print()
            
            print(f"{YELLOW}To create a database, run 'python3 refresh_database.py' first.{NC}")
            sys.exit(1)
        
        # Validate the zip file before extraction  
        print(f"{BLUE}Validating {src_zip}...{NC}")
        if not validate_zip_file(src_zip):
            print()
            print(f"{RED}Error: Invalid or corrupted zip file{NC}")
            print(f"{YELLOW}Please run 'python3 refresh_database.py' to recreate the database.{NC}")
            sys.exit(1)
        
        print()
        print(f"{BLUE}Extracting Azure API specifications...{NC}")
        try:
            with ZipFile(src_zip, 'r') as zip_ref:
                zip_ref.extractall(db_path)
            print(f"{GREEN}✓ Extraction complete{NC}\n")
            
            # Find the extracted directory
            extracted_dir = find_specs_directory(db_path)
                
        except Exception as e:
            print(f"{RED}Error: Extraction failed: {e}{NC}")
            print(f"{YELLOW}Please check file permissions and disk space.{NC}")
            sys.exit(1)
    
    # Analyze the specifications
    analyzer = AzureSecurityAnalyzer()
    
    if extracted_dir and extracted_dir.exists():
        print(f"{BLUE}Analyzing specifications from: {extracted_dir.name}/{NC}")
        analyzer.analyze_directory(extracted_dir)
    else:
        print(f"{RED}Error: Azure API specifications not found after extraction{NC}")
        print(f"Searched in: {db_path}")
        print()
        print(f"{YELLOW}The zip file may not contain JSON specification files.{NC}")
        print(f"{YELLOW}Please run 'python3 refresh_database.py' to recreate the database.{NC}")
        sys.exit(1)
    
    # Print results
    analyzer.print_results()
    
    # Exit with error code if issues found
    if analyzer.issues:
        sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()
