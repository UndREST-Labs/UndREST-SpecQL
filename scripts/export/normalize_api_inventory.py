"""
normalize_api_inventory.py — Normalization utilities for the SpecRecon API Inventory Export.

All functions are conservative: they return "unknown" (or an appropriate empty/None value)
rather than guessing when reliable derivation is not possible.
"""

import re
from pathlib import Path


# ---------------------------------------------------------------------------
# HTTP method normalization
# ---------------------------------------------------------------------------

def normalize_method(method: str) -> str:
    """Return the HTTP method normalized to uppercase.

    Returns "UNKNOWN" for None or empty input.
    """
    if not method:
        return "UNKNOWN"
    return str(method).upper()


# ---------------------------------------------------------------------------
# Provider / resource-type extraction from URL path templates
# ---------------------------------------------------------------------------

# Matches the provider namespace segment such as Microsoft.Storage
_PROVIDER_RE = re.compile(
    r"/providers/([A-Za-z][A-Za-z0-9]*\.[A-Za-z][A-Za-z0-9]*)",
    re.IGNORECASE,
)

# After the provider namespace, capture the first resource type segment
_RESOURCE_FAMILY_RE = re.compile(
    r"/providers/[A-Za-z][A-Za-z0-9]*\.[A-Za-z][A-Za-z0-9]*/([A-Za-z][A-Za-z0-9]*)",
    re.IGNORECASE,
)


def extract_provider_namespace(path_template: str) -> str:
    """Extract the provider namespace (e.g. ``Microsoft.Storage``) from a path template.

    Returns ``"unknown"`` when the namespace cannot be determined.
    """
    if not path_template:
        return "unknown"
    m = _PROVIDER_RE.search(path_template)
    if m:
        return m.group(1)
    return "unknown"


def extract_resource_provider_family(path_template: str) -> str:
    """Extract the first resource type segment that follows the provider namespace.

    For ``/providers/Microsoft.Storage/storageAccounts/{accountName}`` this returns
    ``"storageAccounts"``.  Returns ``"unknown"`` when it cannot be determined.
    """
    if not path_template:
        return "unknown"
    m = _RESOURCE_FAMILY_RE.search(path_template)
    if m:
        return m.group(1)
    return "unknown"


# ---------------------------------------------------------------------------
# Plane classification
# ---------------------------------------------------------------------------

_MANAGEMENT_HOSTS = {
    "management.azure.com",
    "management.core.windows.net",
}


def classify_plane(host: str, path_template: str) -> str:
    """Return ``"management"``, ``"data"``, or ``"unknown"`` for an operation.

    Classification rules (in priority order):
    1. Host is ``management.azure.com`` or ``management.core.windows.net`` → management.
    2. Host ends in ``.azure.com`` or a known data-plane TLD suffix → data.
    3. Path contains ``/providers/`` → management (ARM pattern).
    4. Path contains ``/subscriptions/`` → management (ARM pattern).
    5. Otherwise → unknown.
    """
    host_lower = (host or "").lower().strip()
    path = path_template or ""

    if host_lower in _MANAGEMENT_HOSTS:
        return "management"

    if host_lower:
        # Known data-plane host suffixes
        data_suffixes = (
            ".blob.core.windows.net",
            ".queue.core.windows.net",
            ".table.core.windows.net",
            ".file.core.windows.net",
            ".dfs.core.windows.net",
            ".servicebus.windows.net",
            ".vault.azure.net",
            ".documents.azure.com",
            ".search.windows.net",
            ".openai.azure.com",
            ".cognitiveservices.azure.com",
            ".azuredatabricks.net",
            ".azurehdinsight.net",
            ".azurewebsites.net",
            ".azure-api.net",
            ".dev.azure.com",
        )
        for suffix in data_suffixes:
            if host_lower.endswith(suffix):
                return "data"

    # Fall back to path heuristics
    if "/providers/" in path or "/subscriptions/" in path or "/resourcegroups/" in path.lower():
        return "management"

    return "unknown"


# ---------------------------------------------------------------------------
# Stability classification
# ---------------------------------------------------------------------------

_PREVIEW_VERSION_RE = re.compile(r"preview", re.IGNORECASE)


def is_preview_version(api_version: str) -> bool:
    """Return ``True`` when the version string indicates a preview release.

    Matches common Azure conventions such as ``2023-01-01-preview``,
    ``2023-01-01-beta``, ``2023-01-01-alpha``, and ``2023-01-01-privatepreview``.
    Returns ``False`` for empty/None input.
    """
    if not api_version:
        return False
    return bool(_PREVIEW_VERSION_RE.search(api_version))


def classify_stability(file_path: str, api_version: str) -> str:
    """Return ``"stable"``, ``"preview"``, or ``"unknown"`` for an operation.

    Checks the spec file path for a ``/preview/`` directory component first,
    then falls back to inspecting the API version string.
    """
    if not file_path and not api_version:
        return "unknown"

    # Check the file path for a preview directory
    path_str = str(file_path) if file_path else ""
    parts = Path(path_str).parts if path_str else []
    for part in parts:
        if part.lower() == "preview":
            return "preview"
        if part.lower() == "stable":
            return "stable"

    # Fall back to the version string
    if api_version:
        if is_preview_version(api_version):
            return "preview"
        # If the version looks like a date (YYYY-MM-DD) with no qualifier → stable
        if re.match(r"^\d{4}-\d{2}-\d{2}$", api_version):
            return "stable"

    return "unknown"


# ---------------------------------------------------------------------------
# API version extraction from file paths
# ---------------------------------------------------------------------------

# Matches directory names that look like Azure API versions:
# 2023-01-01  or  2023-01-01-preview  or  2023-01-01-privatepreview etc.
_API_VERSION_DIR_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2}(?:-[a-zA-Z0-9]+)*)$"
)


def extract_api_version_from_path(file_path: str) -> str:
    """Extract the API version from a spec file path.

    Azure spec paths typically contain a directory named like ``2023-01-01`` or
    ``2023-01-01-preview``.  Returns ``"unknown"`` when none is found.
    """
    if not file_path:
        return "unknown"
    parts = Path(str(file_path)).parts
    for part in parts:
        if _API_VERSION_DIR_RE.match(part):
            return part
    return "unknown"


# ---------------------------------------------------------------------------
# Lookup key generation
# ---------------------------------------------------------------------------

def generate_lookup_key(host: str, method: str, path_template: str) -> str:
    """Generate a normalized lookup key for runtime matching.

    Format: ``<host>|<METHOD>|<path_template>``

    The host is lowercased; the method is uppercased; the path template is
    preserved as-is (path parameter names are kept so that consumers can
    perform pattern matching against observed URLs).
    """
    host_norm = (host or "").lower().strip()
    method_norm = normalize_method(method)
    path_norm = path_template or ""
    return f"{host_norm}|{method_norm}|{path_norm}"


# ---------------------------------------------------------------------------
# Route key normalization
# ---------------------------------------------------------------------------

# ARM scope parameter placeholders that are kept verbatim in route keys.
# These match the placeholders emitted by the APISpy ARM normaliser for the
# structurally-defined scope segments (subscriptions, resourceGroups, etc.).
_ARM_SCOPE_PARAMS: frozenset = frozenset({
    "{subscriptionId}",
    "{resourceGroupName}",
    "{tenantId}",
    "{location}",
    "{managementGroupId}",
})

_PLACEHOLDER_RE = re.compile(r"\{[^}]+\}")


def normalize_path_template_for_key(path_template: str) -> str:
    """Normalise path parameter names in a path template for use as a route key.

    Azure REST API spec path templates use resource-specific parameter names
    such as ``{vaultName}``, ``{secretName}``, and ``{accountName}``.  The
    APISpy ARM normaliser replaces all resource-name positions with the
    structural placeholder ``{name}``.  To ensure the two sides compare equal
    during route lookup, this function replaces every non-scope placeholder
    with ``{name}``.

    **Query-string stripping** — ``x-ms-paths`` entries may embed query
    parameters in the path key (e.g. ``/path?comp=list``).  The runtime
    normaliser only sees the URL pathname (no query string), so the query
    portion is stripped before the route key is generated.

    ARM scope parameters that are preserved as-is (they already match the
    ARM normaliser output)::

        {subscriptionId}, {resourceGroupName}, {tenantId},
        {location}, {managementGroupId}

    Examples::

        /subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/
        providers/Microsoft.KeyVault/vaults/{vaultName}
        → /subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/
          providers/Microsoft.KeyVault/vaults/{name}

        /subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/
        providers/Microsoft.Storage/storageAccounts/{accountName}/blobServices/default
        → /subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/
          providers/Microsoft.Storage/storageAccounts/{name}/blobServices/default

        /path?comp=list&restype=container
        → /path

    Returns ``path_template`` unchanged when it contains no non-scope
    placeholders.
    """
    if not path_template:
        return path_template

    # Strip query string (x-ms-paths may include one).
    base_path = path_template.split("?", 1)[0] if "?" in path_template else path_template

    def _replace(match: re.Match) -> str:
        placeholder = match.group(0)
        return placeholder if placeholder in _ARM_SCOPE_PARAMS else "{name}"

    return _PLACEHOLDER_RE.sub(_replace, base_path)


# ---------------------------------------------------------------------------
# Source kind detection
# ---------------------------------------------------------------------------

def detect_source_kind(key_name: str) -> str:
    """Return the source kind for a paths dictionary key.

    * ``"x-ms-paths"`` — for the Azure extension paths block
    * ``"paths"`` — for standard OpenAPI paths
    * ``"other"`` — for anything else
    """
    if key_name == "x-ms-paths":
        return "x-ms-paths"
    if key_name == "paths":
        return "paths"
    return "other"
