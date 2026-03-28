# Contributing to UndREST-SpecQL

Thank you for your interest in contributing to SpeQL! This guide will help you add new security queries and improve the tool.

**SpeQL** is an API Spec Query Analyser that supports the Azure REST API and identifies APIs that might be vulnerable to SilentReaper and related vulnerability classes. A SilentReaper vulnerability is characterised by emitting a SAS URI in API responses, which becomes dangerous when there is improper RBAC (Role-Based Access Control) or inadequate control/data plane isolation.

For **APISpy** (browser extension, portal sweep, shard preparation), see [UndREST-APISpy](https://github.com/UndREST-Labs/UndREST-APISpy).

## 🎯 Ways to Contribute

1. **Add new security queries** for Azure vulnerabilities
2. **Improve existing queries** to reduce false positives
3. **Add support for new Azure services**
4. **Improve documentation**
5. **Report bugs or suggest features**

## 🔧 Development Setup

### Prerequisites
- Python 3.6 or higher
- (Optional) CodeQL CLI for query development
- Git

### Getting Started
```bash
# Clone the repository
git clone https://github.com/UndREST-Labs/UndREST-SpecQL.git
cd UndREST-SpecQL

# (Optional) Refresh database with latest Azure specs
./refresh-database.sh --update

# Run the analyzer to ensure everything works
python3 analyze.py
```

### Database Management

To work with the latest Azure API specifications:

```bash
# Update database with latest specs
./refresh-database.sh --update

# Build database for a specific service
./refresh-database.sh --path specification/keyvault --fresh

# See docs/DATABASE_REFRESH.md for comprehensive documentation
```

## 📝 Adding a New Security Query

### 1. Identify the Vulnerability Pattern

Before writing a query, clearly define:
- What security issue are you detecting?
- What is the security impact?
- What CWE(s) does it relate to?
- What should the fix look like?

### 2. Add Detection Logic to analyze.py

Edit `analyze.py` and add a new method to the `AzureSecurityAnalyzer` class:

```python
def _check_your_vulnerability(self, file_path: str, content: Dict[str, Any]):
    """Check for your specific vulnerability"""
    # Your detection logic here
    
    # Example: Detect missing HTTPS enforcement
    if content.get("schemes"):
        schemes = content.get("schemes", [])
        if "http" in schemes and "https" not in schemes:
            self.issues.append(SecurityIssue(
                "error",
                "Insecure Transport Protocol",
                "API allows HTTP (unencrypted) connections",
                file_path,
                "schemes"
            ))
```

Then call your method in `analyze_file()`:
```python
def analyze_file(self, file_path: str, content: Dict[str, Any]):
    # ... existing checks ...
    self._check_your_vulnerability(file_path, content)
```

### 3. Create a CodeQL Query (Optional)

If you want to create a CodeQL query, add it to `queries/azure-security/`:

```ql
/**
 * @name Your Vulnerability Name
 * @description Detailed description of what this detects
 * @kind problem
 * @problem.severity error
 * @security-severity 8.0
 * @precision high
 * @id azure/your-vulnerability-id
 * @tags security
 *       external/cwe/cwe-XXX
 */

import javascript

// Your query logic here

from JsonObject obj, string message
where
  // Your detection conditions
  message = "Your vulnerability message"
select obj, message
```

### 4. Test Your Query

```bash
# Run the analyzer
python3 analyze.py

# Verify your new check detects the issue
# Check that it doesn't produce false positives
```

### 5. Document Your Query

Add documentation to:
- **README.md**: Add your query to the "Vulnerabilities Detected" section
- **docs/QUICK_REFERENCE.md**: Add usage examples
- **docs/EXAMPLE_OUTPUT.md**: Add sample output if applicable

## 🧪 Testing Guidelines

### Manual Testing
1. Create or find Azure API specs that contain the vulnerability
2. Run your analyzer against them
3. Verify the issue is detected correctly
4. Test against specs that don't have the issue (no false positives)

### Test Data
Use the existing Azure API specs in `database/azure-api-db/` for testing.

## 📋 Code Style Guidelines

### Python Code
- Follow PEP 8 style guide
- Use type hints where applicable
- Add docstrings to all methods
- Keep methods focused and single-purpose

```python
def _check_vulnerability(self, file_path: str, content: Dict[str, Any]):
    """
    Check for specific vulnerability pattern.
    
    Args:
        file_path: Path to the file being analyzed
        content: Parsed JSON content
    """
    # Implementation
```

### CodeQL Queries
- Include comprehensive documentation in query header
- Use descriptive predicate names
- Add comments for complex logic
- Follow CodeQL best practices

## 🐛 Reporting Issues

When reporting bugs, include:
1. SpeQL version or commit hash
2. Python version (`python3 --version`)
3. Steps to reproduce
4. Expected vs actual behavior
5. Sample files (if applicable)

## 💡 Query Ideas

Here are some vulnerability patterns you could add:

### Azure-Specific
- **Managed Identity not used**: Detects services not using managed identities
- **Storage Account public access**: Finds storage accounts with public access
- **SQL injection vectors**: Detects dynamic SQL construction
- **Weak TLS versions**: Finds services allowing TLS 1.0/1.1
- **Diagnostic logging disabled**: Detects resources without logging

### General API Security
- **Rate limiting missing**: APIs without rate limit configurations
- **CORS misconfiguration**: Overly permissive CORS policies
- **Weak password policies**: Password requirements below standards
- **Session timeout issues**: Long or indefinite session timeouts
- **Insufficient input validation**: Missing validation on inputs

## 🔄 Pull Request Process

1. **Fork** [UndREST-SpecQL](https://github.com/UndREST-Labs/UndREST-SpecQL)
2. **Create a branch** for your feature (`git checkout -b feature/your-feature`)
3. **Make your changes** following the guidelines above
4. **Test thoroughly** to ensure no regressions
5. **Commit** with clear messages (`git commit -m "Add detection for X vulnerability"`)
6. **Push** to your fork (`git push origin feature/your-feature`)
7. **Create a Pull Request** with:
   - Clear description of changes
   - Why the change is needed
   - Testing performed
   - Example output (if applicable)

### PR Checklist
- [ ] Code follows style guidelines
- [ ] All existing tests still pass
- [ ] New functionality is tested
- [ ] Documentation is updated
- [ ] Commit messages are clear
- [ ] No sensitive data included

## 📖 Documentation Standards

### Code Comments
- Explain *why*, not *what*
- Document complex algorithms
- Note any security assumptions
- Reference CWE/CVE when applicable

### Query Documentation
Include in query header:
- Clear vulnerability name
- Detailed description
- Severity level
- CWE references
- Remediation guidance

## 🔐 Security Considerations

- **Never commit secrets** or credentials
- **Don't include real Azure subscription IDs** in examples
- **Sanitize test data** before including in PRs
- **Report security vulnerabilities** privately (see SECURITY.md if it exists)

## 📚 Learning Resources

### Azure Security
- [Azure Security Documentation](https://docs.microsoft.com/en-us/azure/security/)
- [Azure Security Benchmark](https://docs.microsoft.com/en-us/security/benchmark/azure/)

### CodeQL
- [CodeQL Documentation](https://codeql.github.com/docs/)
- [CodeQL for JavaScript](https://codeql.github.com/docs/codeql-language-guides/codeql-for-javascript/)

### Security Standards
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE Top 25](https://cwe.mitre.org/top25/archive/2023/2023_top25_list.html)

## 🤝 Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on the code, not the person
- Help others learn and grow

## 📧 Contact

For questions or discussions:
- Open a GitHub issue in [UndREST-SpecQL](https://github.com/UndREST-Labs/UndREST-SpecQL/issues)
- Review existing issues and PRs

Thank you for contributing to SpeQL and UndREST Labs!
