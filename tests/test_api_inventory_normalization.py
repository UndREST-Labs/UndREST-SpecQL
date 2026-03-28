"""
tests/test_api_inventory_normalization.py

Unit tests for scripts/export/normalize_api_inventory.py.
"""

import sys
from pathlib import Path

# Make the export package importable when running from the repo root
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "export"))

import normalize_api_inventory as norm


# ---------------------------------------------------------------------------
# normalize_method
# ---------------------------------------------------------------------------

class TestNormalizeMethod:
    def test_lowercase_to_uppercase(self):
        assert norm.normalize_method("get") == "GET"
        assert norm.normalize_method("post") == "POST"
        assert norm.normalize_method("delete") == "DELETE"

    def test_already_uppercase(self):
        assert norm.normalize_method("PUT") == "PUT"

    def test_mixed_case(self):
        assert norm.normalize_method("pAtCh") == "PATCH"

    def test_empty_string(self):
        assert norm.normalize_method("") == "UNKNOWN"

    def test_none(self):
        assert norm.normalize_method(None) == "UNKNOWN"


# ---------------------------------------------------------------------------
# extract_provider_namespace
# ---------------------------------------------------------------------------

class TestExtractProviderNamespace:
    def test_standard_arm_path(self):
        path = "/subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Storage/storageAccounts/{name}"
        assert norm.extract_provider_namespace(path) == "Microsoft.Storage"

    def test_compute_provider(self):
        path = "/providers/Microsoft.Compute/virtualMachines/{vmName}"
        assert norm.extract_provider_namespace(path) == "Microsoft.Compute"

    def test_no_provider(self):
        path = "/subscriptions/{sub}/resourceGroups/{rg}"
        assert norm.extract_provider_namespace(path) == "unknown"

    def test_empty_string(self):
        assert norm.extract_provider_namespace("") == "unknown"

    def test_none(self):
        assert norm.extract_provider_namespace(None) == "unknown"

    def test_case_insensitive(self):
        path = "/providers/microsoft.storage/storageAccounts"
        result = norm.extract_provider_namespace(path)
        assert result.lower() == "microsoft.storage"


# ---------------------------------------------------------------------------
# extract_resource_provider_family
# ---------------------------------------------------------------------------

class TestExtractResourceProviderFamily:
    def test_storage_accounts(self):
        path = "/providers/Microsoft.Storage/storageAccounts/{accountName}"
        assert norm.extract_resource_provider_family(path) == "storageAccounts"

    def test_virtual_machines(self):
        path = "/providers/Microsoft.Compute/virtualMachines/{vmName}/extensions"
        assert norm.extract_resource_provider_family(path) == "virtualMachines"

    def test_no_provider(self):
        path = "/subscriptions/{sub}/resourceGroups"
        assert norm.extract_resource_provider_family(path) == "unknown"

    def test_empty(self):
        assert norm.extract_resource_provider_family("") == "unknown"

    def test_none(self):
        assert norm.extract_resource_provider_family(None) == "unknown"


# ---------------------------------------------------------------------------
# classify_plane
# ---------------------------------------------------------------------------

class TestClassifyPlane:
    def test_management_azure_com(self):
        assert norm.classify_plane("management.azure.com", "/subscriptions/{sub}") == "management"

    def test_management_core_windows_net(self):
        assert norm.classify_plane("management.core.windows.net", "/") == "management"

    def test_blob_storage_data(self):
        result = norm.classify_plane("mystorage.blob.core.windows.net", "/container/blob")
        assert result == "data"

    def test_vault_data(self):
        result = norm.classify_plane("myvault.vault.azure.net", "/secrets/{name}")
        assert result == "data"

    def test_providers_path_heuristic(self):
        # No host but path contains /providers/
        result = norm.classify_plane("", "/subscriptions/{sub}/providers/Microsoft.Storage/storageAccounts")
        assert result == "management"

    def test_unknown_host_no_clues(self):
        result = norm.classify_plane("some.random.host", "/api/v1/thing")
        assert result == "unknown"

    def test_empty_host_empty_path(self):
        result = norm.classify_plane("", "")
        assert result == "unknown"


# ---------------------------------------------------------------------------
# classify_stability
# ---------------------------------------------------------------------------

class TestClassifyStability:
    def test_preview_directory(self):
        path = "specification/storage/resource-manager/Microsoft.Storage/preview/2023-01-01-preview/storage.json"
        assert norm.classify_stability(path, "2023-01-01-preview") == "preview"

    def test_stable_directory(self):
        path = "specification/storage/resource-manager/Microsoft.Storage/stable/2023-01-01/storage.json"
        assert norm.classify_stability(path, "2023-01-01") == "stable"

    def test_preview_version_string(self):
        assert norm.classify_stability("", "2023-01-01-preview") == "preview"

    def test_stable_version_no_path(self):
        assert norm.classify_stability("", "2023-01-01") == "stable"

    def test_unknown_both_empty(self):
        assert norm.classify_stability("", "") == "unknown"

    def test_unknown_no_recognizable_info(self):
        assert norm.classify_stability("some/path/without/clues/file.json", "") == "unknown"


# ---------------------------------------------------------------------------
# is_preview_version
# ---------------------------------------------------------------------------

class TestIsPreviewVersion:
    def test_preview_suffix(self):
        assert norm.is_preview_version("2023-01-01-preview") is True

    def test_privatepreview(self):
        assert norm.is_preview_version("2023-01-01-privatepreview") is True

    def test_stable_date(self):
        assert norm.is_preview_version("2023-01-01") is False

    def test_empty(self):
        assert norm.is_preview_version("") is False

    def test_none(self):
        assert norm.is_preview_version(None) is False

    def test_case_insensitive(self):
        assert norm.is_preview_version("2023-01-01-Preview") is True


# ---------------------------------------------------------------------------
# generate_lookup_key
# ---------------------------------------------------------------------------

class TestGenerateLookupKey:
    def test_basic(self):
        key = norm.generate_lookup_key(
            "management.azure.com",
            "GET",
            "/subscriptions/{sub}/providers/Microsoft.Storage/storageAccounts",
        )
        assert key == "management.azure.com|GET|/subscriptions/{sub}/providers/Microsoft.Storage/storageAccounts"

    def test_host_lowercased(self):
        key = norm.generate_lookup_key("Management.Azure.COM", "get", "/path")
        assert key.startswith("management.azure.com|GET|")

    def test_empty_host(self):
        key = norm.generate_lookup_key("", "post", "/path")
        assert key == "|POST|/path"

    def test_consistent_for_same_inputs(self):
        k1 = norm.generate_lookup_key("host.example.com", "DELETE", "/resource/{id}")
        k2 = norm.generate_lookup_key("host.example.com", "DELETE", "/resource/{id}")
        assert k1 == k2


# ---------------------------------------------------------------------------
# extract_api_version_from_path
# ---------------------------------------------------------------------------

class TestExtractApiVersionFromPath:
    def test_stable_version(self):
        path = "specification/storage/resource-manager/Microsoft.Storage/stable/2023-01-01/storage.json"
        assert norm.extract_api_version_from_path(path) == "2023-01-01"

    def test_preview_version(self):
        path = "specification/network/resource-manager/Microsoft.Network/preview/2022-05-01-preview/network.json"
        assert norm.extract_api_version_from_path(path) == "2022-05-01-preview"

    def test_no_version_in_path(self):
        path = "specification/storage/resource-manager/storage.json"
        assert norm.extract_api_version_from_path(path) == "unknown"

    def test_empty(self):
        assert norm.extract_api_version_from_path("") == "unknown"

    def test_none(self):
        assert norm.extract_api_version_from_path(None) == "unknown"


# ---------------------------------------------------------------------------
# detect_source_kind
# ---------------------------------------------------------------------------

class TestDetectSourceKind:
    def test_paths(self):
        assert norm.detect_source_kind("paths") == "paths"

    def test_x_ms_paths(self):
        assert norm.detect_source_kind("x-ms-paths") == "x-ms-paths"

    def test_other(self):
        assert norm.detect_source_kind("something-else") == "other"

    def test_empty(self):
        assert norm.detect_source_kind("") == "other"


# ---------------------------------------------------------------------------
# normalize_path_template_for_key
# ---------------------------------------------------------------------------

class TestNormalizePathTemplateForKey:
    """normalize_path_template_for_key replaces non-scope placeholders with {name}."""

    def test_vault_name_replaced(self):
        path = (
            "/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}"
            "/providers/Microsoft.KeyVault/vaults/{vaultName}"
        )
        expected = (
            "/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}"
            "/providers/Microsoft.KeyVault/vaults/{name}"
        )
        assert norm.normalize_path_template_for_key(path) == expected

    def test_multi_level_resource_names(self):
        path = (
            "/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}"
            "/providers/Microsoft.KeyVault/vaults/{vaultName}/keys/{keyName}"
        )
        expected = (
            "/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}"
            "/providers/Microsoft.KeyVault/vaults/{name}/keys/{name}"
        )
        assert norm.normalize_path_template_for_key(path) == expected

    def test_scope_params_preserved(self):
        """ARM scope placeholders must stay as-is so they match normaliser output."""
        path = (
            "/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}"
            "/providers/Microsoft.Compute/virtualMachines/{vmName}"
        )
        result = norm.normalize_path_template_for_key(path)
        assert "{subscriptionId}" in result
        assert "{resourceGroupName}" in result
        assert "{name}" in result
        assert "{vmName}" not in result

    def test_tenant_scope_preserved(self):
        path = "/tenants/{tenantId}/providers/Microsoft.AAD/domainServices/{domainName}"
        expected = "/tenants/{tenantId}/providers/Microsoft.AAD/domainServices/{name}"
        assert norm.normalize_path_template_for_key(path) == expected

    def test_location_scope_preserved(self):
        path = (
            "/subscriptions/{subscriptionId}"
            "/providers/Microsoft.KeyVault.Admin/locations/{location}/quotas"
        )
        result = norm.normalize_path_template_for_key(path)
        assert "{location}" in result
        assert "{subscriptionId}" in result

    def test_management_group_scope_preserved(self):
        path = "/managementGroups/{managementGroupId}/providers/Microsoft.Authorization/policyAssignments/{policyAssignmentName}"
        expected = "/managementGroups/{managementGroupId}/providers/Microsoft.Authorization/policyAssignments/{name}"
        assert norm.normalize_path_template_for_key(path) == expected

    def test_default_singleton_preserved(self):
        """Literal 'default' segments (not a placeholder) must remain unchanged."""
        path = (
            "/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}"
            "/providers/Microsoft.Storage/storageAccounts/{accountName}/blobServices/default"
        )
        result = norm.normalize_path_template_for_key(path)
        assert "blobServices/default" in result
        assert "{name}" in result

    def test_storage_account_name_replaced(self):
        path = (
            "/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}"
            "/providers/Microsoft.Storage/storageAccounts/{accountName}"
        )
        expected = (
            "/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}"
            "/providers/Microsoft.Storage/storageAccounts/{name}"
        )
        assert norm.normalize_path_template_for_key(path) == expected

    def test_no_placeholders_unchanged(self):
        path = "/providers/Microsoft.Authorization/operations"
        assert norm.normalize_path_template_for_key(path) == path

    def test_already_normalised_unchanged(self):
        """A path that already uses {name} is returned unchanged."""
        path = (
            "/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}"
            "/providers/Microsoft.KeyVault/vaults/{name}"
        )
        assert norm.normalize_path_template_for_key(path) == path

    def test_empty_string(self):
        assert norm.normalize_path_template_for_key("") == ""

    def test_none(self):
        assert norm.normalize_path_template_for_key(None) is None

    def test_query_string_stripped(self):
        """x-ms-paths query strings must be stripped from the route key."""
        path = "/providers/Microsoft.Test/things/{name}?api-version=2023-01-01"
        expected = "/providers/Microsoft.Test/things/{name}"
        assert norm.normalize_path_template_for_key(path) == expected

    def test_query_string_with_multiple_params(self):
        """x-ms-paths with multiple query parameters stripped."""
        path = "/v2/{name}/blobs/{digest}?mode=chunk&comp=metadata"
        expected = "/v2/{name}/blobs/{name}"
        assert norm.normalize_path_template_for_key(path) == expected

    def test_query_string_disambiguation_stripped(self):
        """x-ms-paths disambiguation markers stripped."""
        path = "/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/Microsoft.Solutions/applicationDefinitions/{applicationDefinitionName}?disambiguation_dummy"
        expected = "/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/Microsoft.Solutions/applicationDefinitions/{name}"
        assert norm.normalize_path_template_for_key(path) == expected

    def test_no_query_string_unchanged(self):
        """Paths without query strings are unaffected by stripping."""
        path = "/subscriptions/{subscriptionId}/providers/Microsoft.Test/things/{name}"
        expected = "/subscriptions/{subscriptionId}/providers/Microsoft.Test/things/{name}"
        assert norm.normalize_path_template_for_key(path) == expected
