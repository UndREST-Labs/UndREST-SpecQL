#!/usr/bin/env python3
"""
export_api_inventory.py — SpecRecon API Inventory Export

Walks a directory of OpenAPI/Swagger spec files, parses every operation, and
produces a normalized api-index.json that can be used for "spec vs reality"
comparison of REST API calls.

Works with any OpenAPI/Swagger spec corpus — not just azure-rest-api-specs.  The
upstream repository and branch are supplied via --source-repo / --source-branch
(or auto-detected from git) and recorded in the export metadata.

Usage:
    python3 scripts/export/export_api_inventory.py [options]

Options:
    --source-config Optional source config for path, provenance, and profile
    --source        Path to the specifications directory (default: config or azure-rest-api-specs/specification)
    --output-dir    Directory where the output files are written (default: inventory/)
    --source-repo   Upstream repository identifier recorded in metadata (e.g. Azure/azure-rest-api-specs)
    --source-branch Branch name recorded in metadata (default: main)
    --source-profile Source-specific parsing profile (default: auto)
    --minified      Also produce a minified api-index.min.json (no indentation)
    --grouped       Also produce a grouped/deduplicated api-index-grouped.json (schema 3.2.0)
    --sharded       Also produce per-provider shards under {output-dir}/shards/ (schema 3.2.0)
    --verbose       Print per-file progress messages

Output files:
    api-index.json                     Flat pretty-printed index (schema 2.1.0)
    api-index.min.json                 Flat minified index (with --minified)
    api-index-grouped.json             Grouped/deduplicated index (with --grouped, schema 3.2.0)
    api-index-grouped.min.json         Grouped minified index (with --grouped --minified)
    shards/{Provider.Namespace}.json   Per-provider shard (with --sharded, schema 3.2.0)
    shards/{Provider.Namespace}.min.json  Minified per-provider shard (with --sharded --minified)
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

try:
    import yaml
except ImportError:  # pragma: no cover - exercised through dependency-failure tests
    yaml = None

# Allow running as a standalone script or as a package member
_HERE = Path(__file__).parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from normalize_api_inventory import (
    classify_plane,
    classify_stability,
    detect_source_kind,
    extract_api_version_from_path,
    extract_provider_namespace,
    generate_lookup_key,
    is_preview_version,
    normalize_method,
    normalize_path_template_for_key,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TOOL_NAME = "SpecRecon"
TOOL_COMPONENT = "SpeQL"
SCHEMA_VERSION = "2.1.0"          # flat format — minor bump for additive source_kind field
GROUPED_SCHEMA_VERSION = "3.2.0"  # additive sibling-correlation metadata for grouped/sharded format

_MAX_SCHEMA_DEPTH = 8
_MAX_SCHEMA_NODES = 1000
_MAX_TOP_LEVEL_FIELDS = 100
_MAX_METADATA_ITEMS = 100
_MAX_RESOURCE_TYPE_SEGMENTS = 20

# Source metadata defaults — overridden at runtime via CLI args or source config.
# These remain as module-level sentinels so that callers that import and use
# run_export() without passing explicit source metadata still work.
_DEFAULT_SOURCE_REPO = "unknown"
_DEFAULT_SOURCE_BRANCH = "main"

_SOURCE_PROFILE_AUTO = "auto"
_SOURCE_PROFILE_GENERIC = "generic"
_SOURCE_PROFILE_MICROSOFT_GRAPH = "microsoft-graph"
_MICROSOFT_GRAPH_SOURCE_REPO = "microsoftgraph/msgraph-metadata"
_MICROSOFT_GRAPH_PROVIDER_NAMESPACE = "Microsoft.Graph"
_MICROSOFT_GRAPH_OPENAPI_PATHS = frozenset({
    "v1.0/openapi.yaml",
    "beta/openapi.yaml",
})

# Directories whose contents should be skipped entirely
_SKIP_DIRS = {
    "examples",
    "example",
    "quickstart-templates",
    "tests",
    "test",
    "mock",
    "mocks",
    "samples",
    "sample",
    "scenarios",
    "scenario",
    "restler",
    "node_modules",
}


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------

def _get_git_commit(repo_path: Path) -> str:
    """Try to retrieve the HEAD commit SHA from *repo_path*."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo_path),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "unknown"


def _detect_source_repo(source_dir: Path) -> str:
    """Try to infer the source repository identifier from the git remote URL.

    For a directory at ``azure-rest-api-specs/specification`` the function
    walks up to find the git root and reads the ``origin`` remote URL,
    returning a short ``org/repo`` identifier (e.g. ``Azure/azure-rest-api-specs``).
    Returns ``"unknown"`` when the information cannot be determined.
    """
    search_dir = source_dir
    for _ in range(4):  # Walk up at most 4 levels
        try:
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=str(search_dir),
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                url = result.stdout.strip()
                # Extract org/repo from HTTPS or SSH URLs
                # e.g. https://github.com/Azure/azure-rest-api-specs.git
                #      git@github.com:Azure/azure-rest-api-specs.git
                m = re.search(r"[:/]([^/:]+/[^/:]+?)(?:\.git)?$", url)
                if m:
                    return m.group(1)
        except Exception:
            pass
        parent = search_dir.parent
        if parent == search_dir:
            break
        search_dir = parent
    return _DEFAULT_SOURCE_REPO


# ---------------------------------------------------------------------------
# Spec-file discovery
# ---------------------------------------------------------------------------

def _should_skip_dir(dir_name: str) -> bool:
    """Return True when a directory should be excluded from traversal."""
    return dir_name.lower() in _SKIP_DIRS


def discover_spec_files(
    source_dir: Path,
    include_yaml: bool = False,
    allowed_relative_paths: set = None,
) -> list:
    """Yield supported spec files under *source_dir*, skipping excluded dirs."""
    suffixes = {".json"}
    if include_yaml:
        suffixes.update({".yaml", ".yml"})

    spec_files = []
    for root, dirs, files in os.walk(source_dir):
        # Prune directories in-place so os.walk doesn't descend into them
        dirs[:] = [d for d in dirs if not _should_skip_dir(d)]
        for fname in files:
            candidate = Path(root) / fname
            if candidate.suffix.lower() not in suffixes:
                continue
            relative = candidate.relative_to(source_dir).as_posix()
            if allowed_relative_paths is not None and relative not in allowed_relative_paths:
                continue
            spec_files.append(candidate)
    return spec_files


# ---------------------------------------------------------------------------
# Parameter extraction helpers
# ---------------------------------------------------------------------------

def _extract_parameter_info(parameters: list) -> dict:
    """Return a dict with parameter analysis for a list of parameter objects."""
    names = []
    required_query = []
    has_api_version = False

    for param in parameters:
        if not isinstance(param, dict):
            continue
        # Parameters may be $ref objects; skip them conservatively
        if "$ref" in param:
            continue
        raw_name = param.get("name")
        location = param.get("in", "")
        required = param.get("required", False)

        # Only work with non-empty string parameter names
        if isinstance(raw_name, str):
            name = raw_name.strip()
        else:
            name = ""

        if name:
            names.append(name)

        if name and name.lower() == "api-version":
            has_api_version = True

        if location == "query" and required and name:
            required_query.append(name)

    return {
        "parameter_names": names,
        "required_query_parameters": required_query,
        "has_api_version_parameter": has_api_version,
    }


# ---------------------------------------------------------------------------
# Spec-file parsing
# ---------------------------------------------------------------------------

def _detect_host(spec: dict, file_path: Path) -> str:
    """Extract the host from a Swagger 2.0 or OpenAPI 3.x spec."""
    # Swagger 2.0
    host = spec.get("host", "")
    if host:
        return host.lower()

    # OpenAPI 3.x — take the first server URL's host
    servers = spec.get("servers", [])
    if servers and isinstance(servers, list):
        first_url = servers[0].get("url", "") if isinstance(servers[0], dict) else ""
        if first_url:
            parsed = urlsplit(first_url)
            if parsed.hostname:
                return parsed.hostname.lower()

    return "unknown"


def _detect_server_base_path(spec: dict) -> str:
    """Return a normalized base path from Swagger/OpenAPI server metadata."""
    base_path = spec.get("basePath", "")
    if isinstance(base_path, str) and base_path.strip("/"):
        return "/" + base_path.strip("/")

    servers = spec.get("servers", [])
    if isinstance(servers, list) and servers and isinstance(servers[0], dict):
        server_url = servers[0].get("url", "")
        if isinstance(server_url, str):
            path = urlsplit(server_url).path
            if path and path != "/":
                return "/" + path.strip("/")
    return ""


def _join_server_path(base_path: str, path_template: str) -> str:
    """Join a server base path and OpenAPI path without changing placeholders."""
    if not base_path:
        return path_template
    normalized_path = "/" + str(path_template or "").lstrip("/")
    if normalized_path == base_path or normalized_path.startswith(base_path + "/"):
        return normalized_path
    return base_path.rstrip("/") + normalized_path


def _resolve_source_profile(source_profile: str, source_repo: str) -> str:
    """Resolve an explicit or source-derived export profile."""
    profile = source_profile or _SOURCE_PROFILE_AUTO
    if profile != _SOURCE_PROFILE_AUTO:
        return profile
    if str(source_repo or "").lower() == _MICROSOFT_GRAPH_SOURCE_REPO:
        return _SOURCE_PROFILE_MICROSOFT_GRAPH
    return _SOURCE_PROFILE_GENERIC


def _load_export_source_config(config_path: Path) -> dict:
    """Load and validate an exporter source configuration file."""
    try:
        with open(config_path, "r", encoding="utf-8") as fh:
            config = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot load source config {config_path}: {exc}") from exc
    if not isinstance(config, dict):
        raise ValueError(f"Source config must be a JSON object: {config_path}")
    return config


def _load_spec_document(file_path: Path):
    """Load a JSON or YAML spec document without resolving external content."""
    suffix = file_path.suffix.lower()
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as fh:
            if suffix in {".yaml", ".yml"}:
                if yaml is None:
                    raise RuntimeError("PyYAML is required to parse OpenAPI YAML files")
                return yaml.safe_load(fh)
            return json.load(fh)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON decode error in {file_path}: {exc}") from exc
    except Exception as exc:
        if yaml is not None and isinstance(exc, yaml.YAMLError):
            raise ValueError(f"YAML decode error in {file_path}: {exc}") from exc
        raise


def _resolve_local_ref(spec: dict, value, seen: set = None):
    """Resolve a local JSON pointer without fetching external content."""
    if not isinstance(value, dict) or not isinstance(value.get("$ref"), str):
        return value
    ref = value["$ref"]
    if not ref.startswith("#/"):
        return value
    seen = set() if seen is None else set(seen)
    if ref in seen or len(seen) >= _MAX_SCHEMA_DEPTH:
        return {"type": "cyclic_ref"}
    seen.add(ref)
    current = spec
    try:
        for token in ref[2:].split("/"):
            token = token.replace("~1", "/").replace("~0", "~")
            current = current[token]
    except (KeyError, TypeError):
        return {"type": "unresolved_ref"}
    return _resolve_local_ref(spec, current, seen)


def _schema_shape(schema, spec: dict, depth: int = 0, seen_refs: set = None, budget: list = None):
    """Return a bounded structural representation suitable for fingerprinting."""
    if budget is None:
        budget = [_MAX_SCHEMA_NODES]
    if budget[0] <= 0 or depth > _MAX_SCHEMA_DEPTH:
        return {"type": "truncated"}
    budget[0] -= 1

    seen_refs = set() if seen_refs is None else set(seen_refs)
    if isinstance(schema, dict) and isinstance(schema.get("$ref"), str):
        ref = schema["$ref"]
        if not ref.startswith("#/"):
            return {"type": "external_ref"}
        if ref in seen_refs:
            return {"type": "cyclic_ref"}
        seen_refs.add(ref)
        resolved = _resolve_local_ref(spec, schema, seen_refs - {ref})
        if resolved is schema or (
            isinstance(resolved, dict) and resolved.get("type") in {"cyclic_ref", "unresolved_ref"}
        ):
            return resolved
        return _schema_shape(resolved, spec, depth + 1, seen_refs, budget)

    if not isinstance(schema, dict):
        return {"type": "unknown"}

    schema_type = schema.get("type")
    if not schema_type:
        if isinstance(schema.get("properties"), dict):
            schema_type = "object"
        elif "items" in schema:
            schema_type = "array"
        else:
            schema_type = "unknown"

    shape = {"type": str(schema_type)}
    if isinstance(schema.get("format"), str):
        shape["format"] = schema["format"][:64]
    if schema.get("nullable") is True or schema.get("x-nullable") is True:
        shape["nullable"] = True

    required = set(schema.get("required", [])) if isinstance(schema.get("required"), list) else set()
    properties = schema.get("properties")
    if isinstance(properties, dict):
        shape["properties"] = {
            str(name)[:200]: {
                "required": name in required,
                "schema": _schema_shape(properties[name], spec, depth + 1, seen_refs, budget),
            }
            for name in sorted(properties, key=str)[:_MAX_TOP_LEVEL_FIELDS]
        }
        if len(properties) > _MAX_TOP_LEVEL_FIELDS:
            shape["properties_truncated"] = True

    if "items" in schema:
        shape["items"] = _schema_shape(schema.get("items"), spec, depth + 1, seen_refs, budget)

    additional = schema.get("additionalProperties")
    if isinstance(additional, bool):
        shape["additional_properties"] = additional
    elif isinstance(additional, dict):
        shape["additional_properties"] = _schema_shape(additional, spec, depth + 1, seen_refs, budget)

    for keyword in ("allOf", "oneOf", "anyOf"):
        variants = schema.get(keyword)
        if isinstance(variants, list):
            shape[keyword] = [
                _schema_shape(item, spec, depth + 1, seen_refs, budget)
                for item in variants[:20]
            ]
            if len(variants) > 20:
                shape[f"{keyword}_truncated"] = True

    return shape


def _effective_top_level_fields(shape: dict) -> tuple:
    fields = {}
    truncated = bool(shape.get("properties_truncated"))

    for name, field in shape.get("properties", {}).items():
        fields[name] = {
            "name": name,
            "type": field.get("schema", {}).get("type", "unknown"),
            "required": bool(field.get("required")),
        }

    for branch in shape.get("allOf", []):
        branch_fields, branch_truncated = _effective_top_level_fields(branch)
        truncated = truncated or branch_truncated
        for field in branch_fields:
            current = fields.get(field["name"])
            if not current:
                fields[field["name"]] = dict(field)
            else:
                if current["type"] != field["type"]:
                    current["type"] = "mixed"
                current["required"] = current["required"] or field["required"]

    for keyword in ("oneOf", "anyOf"):
        branches = shape.get(keyword, [])
        if not branches:
            continue
        branch_maps = []
        for branch in branches:
            branch_fields, branch_truncated = _effective_top_level_fields(branch)
            truncated = truncated or branch_truncated
            branch_maps.append({field["name"]: field for field in branch_fields})
        for name in sorted(set().union(*(set(branch) for branch in branch_maps))):
            alternatives = [branch[name] for branch in branch_maps if name in branch]
            types = {field["type"] for field in alternatives}
            alternative = {
                "name": name,
                "type": next(iter(types)) if len(types) == 1 else "mixed",
                "required": len(alternatives) == len(branch_maps) and all(field["required"] for field in alternatives),
            }
            current = fields.get(name)
            if not current:
                fields[name] = alternative
            elif current["type"] != alternative["type"]:
                current["type"] = "mixed"

    ordered = [fields[name] for name in sorted(fields)[:_MAX_TOP_LEVEL_FIELDS]]
    return ordered, truncated or len(fields) > _MAX_TOP_LEVEL_FIELDS


def _schema_summary(schema, spec: dict):
    if not isinstance(schema, dict):
        return None
    shape = _schema_shape(schema, spec)
    encoded = json.dumps(shape, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    top_level_fields, fields_truncated = _effective_top_level_fields(shape)
    schema_type = shape.get("type", "unknown")
    if schema_type == "unknown" and top_level_fields:
        schema_type = "object"
    summary = {
        "fingerprint": "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:24],
        "type": schema_type,
        "top_level_fields": top_level_fields,
    }
    if fields_truncated:
        summary["fields_truncated"] = True
    return summary


def _parameter_metadata(path_item: dict, operation: dict, spec: dict) -> dict:
    combined = []
    for source in (path_item.get("parameters", []), operation.get("parameters", [])):
        if isinstance(source, list):
            combined.extend(source)
    names = {"query": set(), "path": set(), "header": set(), "cookie": set()}
    body_schemas = []
    for parameter in combined:
        parameter = _resolve_local_ref(spec, parameter)
        if not isinstance(parameter, dict):
            continue
        location = parameter.get("in")
        name = parameter.get("name")
        if location in names and isinstance(name, str):
            names[location].add(name[:200])
        if location == "body":
            summary = _schema_summary(parameter.get("schema"), spec)
            if summary:
                body_schemas.append(summary)

    request_body = _resolve_local_ref(spec, operation.get("requestBody"))
    if isinstance(request_body, dict):
        content = request_body.get("content", {})
        if isinstance(content, dict):
            for content_type in sorted(content)[:20]:
                media = content.get(content_type)
                summary = _schema_summary(media.get("schema"), spec) if isinstance(media, dict) else None
                if summary:
                    summary = {**summary, "content_types": [str(content_type)[:200]]}
                    body_schemas.append(summary)

    deduped = {}
    for summary in body_schemas:
        key = summary["fingerprint"]
        if key not in deduped:
            deduped[key] = summary
        else:
            content_types = set(deduped[key].get("content_types", []))
            content_types.update(summary.get("content_types", []))
            if content_types:
                deduped[key]["content_types"] = sorted(content_types)[:20]

    return {
        "parameters": {key: sorted(values)[:_MAX_METADATA_ITEMS] for key, values in names.items() if values},
        "request_schemas": [deduped[key] for key in sorted(deduped)[:20]],
    }


def _response_metadata(operation: dict, spec: dict) -> list:
    grouped = {}
    responses = operation.get("responses", {})
    if not isinstance(responses, dict):
        return []
    for status_code in sorted(responses, key=str)[:_MAX_METADATA_ITEMS]:
        response = _resolve_local_ref(spec, responses[status_code])
        if not isinstance(response, dict):
            continue
        candidates = []
        if isinstance(response.get("schema"), dict):
            candidates.append((None, response["schema"]))
        content = response.get("content", {})
        if isinstance(content, dict):
            for content_type in sorted(content)[:20]:
                media = content.get(content_type)
                if isinstance(media, dict) and isinstance(media.get("schema"), dict):
                    candidates.append((str(content_type)[:200], media["schema"]))
        for content_type, schema in candidates:
            summary = _schema_summary(schema, spec)
            if not summary:
                continue
            key = summary["fingerprint"]
            item = grouped.setdefault(key, {**summary, "status_codes": [], "content_types": []})
            code = str(status_code)[:32]
            if code not in item["status_codes"]:
                item["status_codes"].append(code)
            if content_type and content_type not in item["content_types"]:
                item["content_types"].append(content_type)
    result = []
    for key in sorted(grouped)[:50]:
        item = grouped[key]
        item["status_codes"].sort()
        item["content_types"].sort()
        if not item["content_types"]:
            item.pop("content_types")
        result.append(item)
    return result


def _security_metadata(operation: dict, spec: dict) -> dict:
    declared = "security" in operation or "security" in spec
    requirements = operation.get("security") if "security" in operation else spec.get("security")
    if not isinstance(requirements, list):
        requirements = []

    cleaned_requirements = []
    scheme_names = set()
    for requirement in requirements[:20]:
        if not isinstance(requirement, dict):
            continue
        cleaned = {}
        for name in sorted(requirement, key=str)[:20]:
            scopes = requirement.get(name)
            cleaned[str(name)[:200]] = sorted(str(scope)[:200] for scope in scopes[:100]) if isinstance(scopes, list) else []
            scheme_names.add(str(name))
        cleaned_requirements.append(cleaned)

    definitions = spec.get("securityDefinitions", {})
    components = spec.get("components", {})
    if isinstance(components, dict) and isinstance(components.get("securitySchemes"), dict):
        definitions = {**(definitions if isinstance(definitions, dict) else {}), **components["securitySchemes"]}
    schemes = []
    for name in sorted(scheme_names)[:20]:
        definition = _resolve_local_ref(spec, definitions.get(name)) if isinstance(definitions, dict) else None
        descriptor = {"name": name[:200], "type": "unknown"}
        if isinstance(definition, dict):
            descriptor["type"] = str(definition.get("type", "unknown"))[:64]
            for source_key, target_key in (("in", "location"), ("scheme", "scheme"), ("name", "parameter_name")):
                if isinstance(definition.get(source_key), str):
                    descriptor[target_key] = definition[source_key][:64]
            flows = definition.get("flows")
            if isinstance(flows, dict):
                descriptor["oauth_flows"] = sorted(str(flow)[:64] for flow in flows)[:20]
            elif isinstance(definition.get("flow"), str):
                descriptor["oauth_flows"] = [definition["flow"][:64]]
        schemes.append(descriptor)

    if not declared:
        status = "unspecified"
    elif not requirements or any(not requirement for requirement in cleaned_requirements):
        status = "optional_or_anonymous"
    else:
        status = "required"
    return {
        "status": status,
        "requirements": cleaned_requirements,
        "schemes": schemes,
    }


def _operation_research_metadata(path_item: dict, operation: dict, spec: dict) -> dict:
    request = _parameter_metadata(path_item, operation, spec)
    return {
        "auth": _security_metadata(operation, spec),
        "parameters": request["parameters"],
        "request_schemas": request["request_schemas"],
        "response_schemas": _response_metadata(operation, spec),
    }


def _parse_spec_file(
    file_path: Path,
    source_dir: Path,
    verbose: bool,
    include_research_metadata: bool = False,
    source_profile: str = _SOURCE_PROFILE_GENERIC,
) -> tuple:
    """Parse a single spec file and return (list_of_operations, error_or_None).

    Each operation is a dict matching the api-index.json schema.
    """
    if file_path == source_dir or source_dir in file_path.parents:
        # Make spec_file paths relative to the --source directory for consistency
        rel_path = file_path.relative_to(source_dir)
    else:
        # Fallback: keep the original path if it's outside the source tree
        rel_path = file_path

    try:
        spec = _load_spec_document(file_path)
    except (OSError, ValueError, RuntimeError) as exc:
        return [], str(exc)

    if not isinstance(spec, dict):
        return [], None  # Not a spec object — skip silently

    # Accept Swagger 2.0 and OpenAPI 3.x
    is_swagger2 = str(spec.get("swagger", "")).startswith("2")
    is_openapi3 = str(spec.get("openapi", "")).startswith("3")
    if not is_swagger2 and not is_openapi3:
        return [], None  # Not a recognized OpenAPI spec — skip

    host = _detect_host(spec, file_path)
    server_base_path = (
        _detect_server_base_path(spec)
        if source_profile == _SOURCE_PROFILE_MICROSOFT_GRAPH
        else ""
    )
    api_version_from_path = extract_api_version_from_path(str(file_path))
    api_version_from_info = spec.get("info", {}).get("version", "")
    api_version = api_version_from_path if api_version_from_path != "unknown" else api_version_from_info

    paths_blocks = {
        "paths": spec.get("paths", {}),
        "x-ms-paths": spec.get("x-ms-paths", {}),
    }

    operations = []

    for paths_block_key, paths_obj in paths_blocks.items():
        if not isinstance(paths_obj, dict):
            continue

        # "paths" | "x-ms-paths" | "other" — recorded as provenance in each op entry
        source_kind = detect_source_kind(paths_block_key)

        for raw_path_template, path_item in paths_obj.items():
            if not isinstance(path_item, dict):
                continue

            path_template = (
                _join_server_path(server_base_path, raw_path_template)
                if source_profile == _SOURCE_PROFILE_MICROSOFT_GRAPH
                else raw_path_template
            )
            http_methods = ["get", "put", "post", "delete", "options", "head", "patch", "trace"]
            for method_lower in http_methods:
                operation = path_item.get(method_lower)
                if not isinstance(operation, dict):
                    continue

                method = normalize_method(method_lower)
                operation_id = operation.get("operationId", "")
                plane = classify_plane(host, path_template)
                stability = classify_stability(str(file_path), api_version)
                preview = is_preview_version(api_version) or stability == "preview"
                lookup_key = generate_lookup_key(host, method, path_template)

                all_versions = [api_version] if api_version and api_version != "unknown" else []

                entry = {
                    "host": host,
                    "method": method,
                    "path_template": path_template,
                    "operation_id": operation_id,
                    "api_versions": all_versions,
                    "spec_file": str(rel_path).replace("\\", "/"),
                    "source_kind": source_kind,
                    "plane": plane,
                    "is_preview": preview,
                    "lookup_key": lookup_key,
                }
                if source_profile == _SOURCE_PROFILE_MICROSOFT_GRAPH:
                    entry["_provider_namespace"] = _MICROSOFT_GRAPH_PROVIDER_NAMESPACE
                if include_research_metadata:
                    entry["_research_metadata"] = _operation_research_metadata(path_item, operation, spec)
                operations.append(entry)

    if verbose and operations:
        print(f"  [{len(operations):4d} ops] {rel_path}")

    return operations, None


# ---------------------------------------------------------------------------
# Summary helpers
# ---------------------------------------------------------------------------

def _build_summary(operations: list, spec_file_count: int, error_count: int) -> dict:
    provider_set = set()
    for op in operations:
        ns = op.get("_provider_namespace") or extract_provider_namespace(op["path_template"])
        if ns != "unknown":
            provider_set.add(ns)
    providers = sorted(provider_set)
    planes: dict = {}
    for op in operations:
        planes[op["plane"]] = planes.get(op["plane"], 0) + 1

    return {
        "total_operations": len(operations),
        "total_spec_files": spec_file_count,
        "providers": providers,
        "planes": planes,
        "errors": error_count,
    }


# ---------------------------------------------------------------------------
# Grouped export helpers
# ---------------------------------------------------------------------------

def _merge_unique_objects(existing: list, incoming: list, limit: int) -> list:
    keyed = {
        json.dumps(item, sort_keys=True, separators=(",", ":"), ensure_ascii=False): item
        for item in existing if isinstance(item, dict)
    }
    for item in incoming:
        if isinstance(item, dict):
            key = json.dumps(item, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            keyed.setdefault(key, item)
    return [keyed[key] for key in sorted(keyed)[:limit]]


def _merge_schema_summaries(existing: list, incoming: list, limit: int) -> list:
    merged = {item.get("fingerprint"): dict(item) for item in existing if isinstance(item, dict) and item.get("fingerprint")}
    for item in incoming:
        if not isinstance(item, dict) or not item.get("fingerprint"):
            continue
        fingerprint = item["fingerprint"]
        if fingerprint not in merged:
            merged[fingerprint] = dict(item)
            continue
        for field in ("status_codes", "content_types"):
            values = set(merged[fingerprint].get(field, []))
            values.update(item.get(field, []))
            if values:
                merged[fingerprint][field] = sorted(values)[:_MAX_METADATA_ITEMS]
    return [merged[key] for key in sorted(merged)[:limit]]


def _merge_research_metadata(target: dict, metadata: dict) -> None:
    auth = metadata.get("auth", {}) if isinstance(metadata, dict) else {}
    target_auth = target["auth"]
    statuses = {target_auth.get("status", "unspecified"), auth.get("status", "unspecified")}
    statuses.discard("unspecified")
    target_auth["status"] = statuses.pop() if len(statuses) == 1 else ("mixed" if statuses else "unspecified")
    target_auth["requirements"] = _merge_unique_objects(
        target_auth.get("requirements", []), auth.get("requirements", []), 50
    )
    target_auth["schemes"] = _merge_unique_objects(
        target_auth.get("schemes", []), auth.get("schemes", []), 50
    )

    for location, names in metadata.get("parameters", {}).items():
        current = set(target["parameters"].get(location, []))
        if isinstance(names, list):
            current.update(str(name)[:200] for name in names)
        target["parameters"][location] = sorted(current)[:_MAX_METADATA_ITEMS]

    target["request_schemas"] = _merge_schema_summaries(
        target.get("request_schemas", []), metadata.get("request_schemas", []), 20
    )
    target["response_schemas"] = _merge_schema_summaries(
        target.get("response_schemas", []), metadata.get("response_schemas", []), 50
    )


def _path_segments(path_template: str) -> list:
    normalized = normalize_path_template_for_key(path_template)
    if not isinstance(normalized, str):
        return []
    path_only = normalized.split("?", 1)[0]
    return [segment for segment in path_only.strip("/").split("/") if segment]


def _is_template_parameter(segment: str) -> bool:
    return segment.startswith("{") and segment.endswith("}")


def _api_family_metadata(provider_ns: str, path_template: str) -> dict:
    """Derive bounded route-family metadata from structural route segments."""
    if not provider_ns or provider_ns == "unknown":
        return {}

    segments = _path_segments(path_template)
    provider_index = None
    for index, segment in enumerate(segments[:-1]):
        if segment.lower() == "providers" and segments[index + 1].lower() == provider_ns.lower():
            provider_index = index + 1
            break
    if provider_index is None:
        return {}

    all_resource_types = [
        segment[:200]
        for segment in segments[provider_index + 1:]
        if not _is_template_parameter(segment) and segment.lower() != "default"
    ]
    if not all_resource_types:
        return {}

    resource_type_path = all_resource_types[:_MAX_RESOURCE_TYPE_SEGMENTS]
    family_key = f"{provider_ns}/{resource_type_path[0]}"
    resource_key = f"{provider_ns}/{'/'.join(resource_type_path)}"

    metadata = {
        "family_key": family_key,
        "provider_namespace": provider_ns,
        "resource_type_path": resource_type_path,
        "resource_key": resource_key,
        "resource_depth": len(all_resource_types),
    }
    if len(resource_type_path) > 1:
        parent_path = resource_type_path[:-1]
        metadata["parent_resource_type_path"] = parent_path
        metadata["parent_resource_key"] = f"{provider_ns}/{'/'.join(parent_path)}"
    if len(all_resource_types) > _MAX_RESOURCE_TYPE_SEGMENTS:
        metadata["resource_type_path_truncated"] = True
    return metadata


def _version_stability_from_string(api_version: str) -> str:
    version = str(api_version or "")
    if is_preview_version(version):
        return "preview"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", version):
        return "stable"
    return "unknown"


def _version_sort_key(api_version: str) -> tuple:
    version = str(api_version or "")
    match = re.match(r"^(\d{4})-(\d{2})-(\d{2})(.*)$", version)
    if match:
        suffix = match.group(4).lower()
        return (0, int(match.group(1)), int(match.group(2)), int(match.group(3)), suffix, version.lower())
    return (1, version.lower())


def _version_lineage_metadata(versions: dict) -> dict:
    """Return bounded ordered version lineage for a route."""
    ordered_versions = sorted(
        (str(version) for version in versions if version and version != "unknown"),
        key=_version_sort_key,
    )
    if not ordered_versions:
        return {}

    bounded_versions = ordered_versions[:_MAX_METADATA_ITEMS]
    entries = []
    for index, api_version in enumerate(bounded_versions):
        entry = {
            "api_version": api_version,
            "stability": _version_stability_from_string(api_version),
        }
        if index > 0:
            entry["previous_version"] = bounded_versions[index - 1]
        if index + 1 < len(bounded_versions):
            entry["next_version"] = bounded_versions[index + 1]
        entries.append(entry)

    metadata = {"ordered_versions": entries}
    if len(ordered_versions) > _MAX_METADATA_ITEMS:
        metadata["versions_truncated"] = True
    return metadata


def _build_grouped_index(flat_ops: list) -> dict:
    """Transform the flat operations list into a grouped providers structure.

    Structure::

        providers[provider_namespace][hosts][host][routes][route_key] = {
            method, path_template, provider_namespace, plane, lookup_key,
            versions: {
                api_version: {is_preview, spec_files, operation_ids, source_kinds}
            }
        }

    The ``route_key`` is ``"METHOD path_template"`` (e.g. ``"GET /providers/…"``).
    Routes with no recognisable provider namespace are grouped under ``"unknown"``.
    """
    providers: dict = {}

    for op in flat_ops:
        host = op["host"]
        method = op["method"]
        path_template = op["path_template"]
        provider_ns = op.get("_provider_namespace") or extract_provider_namespace(path_template)
        route_key = f"{method} {normalize_path_template_for_key(path_template)}"

        # Navigate / create the nested slots
        if provider_ns not in providers:
            providers[provider_ns] = {"hosts": {}}
        prov = providers[provider_ns]

        if host not in prov["hosts"]:
            prov["hosts"][host] = {"routes": {}}
        host_entry = prov["hosts"][host]

        if route_key not in host_entry["routes"]:
            host_entry["routes"][route_key] = {
                "method": method,
                "path_template": path_template,
                "provider_namespace": provider_ns,
                "plane": op["plane"],
                "lookup_key": op["lookup_key"],
                "versions": {},
            }
        route = host_entry["routes"][route_key]

        # Merge version-specific info.  Use "unknown" when no version was found.
        api_versions = op.get("api_versions") or ["unknown"]
        for api_version in api_versions:
            if not api_version:
                api_version = "unknown"

            if api_version not in route["versions"]:
                route["versions"][api_version] = {
                    "is_preview": op["is_preview"],
                    "spec_files": [],
                    "operation_ids": [],
                    "source_kinds": [],
                    "auth": {"status": "unspecified", "requirements": [], "schemes": []},
                    "parameters": {},
                    "request_schemas": [],
                    "response_schemas": [],
                }
            ver = route["versions"][api_version]
            _merge_research_metadata(ver, op.get("_research_metadata", {}))
            # Combine preview classification across all contributing ops for this version.
            # If any op for (route_key, api_version) is preview, mark the version as preview.
            ver["is_preview"] = bool(ver.get("is_preview")) or bool(op["is_preview"])

            spec_file = op.get("spec_file", "")
            if spec_file and spec_file not in ver["spec_files"]:
                ver["spec_files"].append(spec_file)

            op_id = op.get("operation_id", "")
            if op_id and op_id not in ver["operation_ids"]:
                ver["operation_ids"].append(op_id)

            source_kind = op.get("source_kind", "")
            if source_kind and source_kind not in ver["source_kinds"]:
                ver["source_kinds"].append(source_kind)

    for provider in providers.values():
        for host_entry in provider.get("hosts", {}).values():
            for route in host_entry.get("routes", {}).values():
                api_family = _api_family_metadata(route.get("provider_namespace", ""), route.get("path_template", ""))
                if api_family:
                    route["api_family"] = api_family
                version_lineage = _version_lineage_metadata(route.get("versions", {}))
                if version_lineage:
                    route["version_lineage"] = version_lineage
                for version in route.get("versions", {}).values():
                    auth = version.get("auth", {})
                    if auth.get("status") == "unspecified" and not auth.get("requirements") and not auth.get("schemes"):
                        version.pop("auth", None)
                    parameters = version.get("parameters", {})
                    for location in list(parameters):
                        if not parameters[location]:
                            parameters.pop(location)
                    if not parameters:
                        version.pop("parameters", None)
                    if not version.get("request_schemas"):
                        version.pop("request_schemas", None)
                    if not version.get("response_schemas"):
                        version.pop("response_schemas", None)

    return providers


def _build_grouped_summary(providers: dict, spec_file_count: int, error_count: int) -> dict:
    """Build summary statistics for the grouped export."""
    total_routes = 0
    total_versions = 0
    planes: dict = {}

    for _ns, prov_data in providers.items():
        for _host, host_data in prov_data.get("hosts", {}).items():
            for _route_key, route in host_data.get("routes", {}).items():
                total_routes += 1
                plane = route.get("plane", "unknown")
                planes[plane] = planes.get(plane, 0) + 1
                total_versions += len(route.get("versions", {}))

    provider_list = sorted(ns for ns in providers if ns != "unknown")

    return {
        "total_routes": total_routes,
        "total_versions": total_versions,
        "total_spec_files": spec_file_count,
        "providers": provider_list,
        "planes": planes,
        "errors": error_count,
    }


def _build_shard_summary(prov_data: dict, error_count: int) -> dict:
    """Build summary statistics for a single provider shard."""
    total_routes = 0
    total_versions = 0
    planes: dict = {}
    spec_files: set = set()

    for _host, host_data in prov_data.get("hosts", {}).items():
        for _route_key, route in host_data.get("routes", {}).items():
            total_routes += 1
            plane = route.get("plane", "unknown")
            planes[plane] = planes.get(plane, 0) + 1
            for _ver, ver_data in route.get("versions", {}).items():
                total_versions += 1
                spec_files.update(ver_data.get("spec_files", []))

    return {
        "total_routes": total_routes,
        "total_versions": total_versions,
        "total_spec_files": len(spec_files),
        "planes": planes,
        "errors": error_count,
    }


def _write_sharded_index(
    grouped_providers: dict,
    grouped_metadata: dict,
    output_dir: Path,
    error_count: int,
    minified: bool,
    verbose: bool = False,
) -> None:
    """Write one JSON file per provider namespace into ``{output_dir}/shards/``.

    Each shard file contains the same metadata as the grouped export (with
    ``export_format`` set to ``"sharded"`` and a ``provider_namespace`` field
    added), the provider's ``hosts`` tree, and a per-provider summary.

    File naming: ``{output_dir}/shards/{Provider.Namespace}.json``
    The provider namespace is used as-is as the filename; characters that are
    illegal on common file systems (``/``, ``\\``) are replaced with ``_``.

    Per-shard paths are printed only when *verbose* is True; a single summary
    line is always emitted after all shards are written.
    """
    shards_dir = output_dir / "shards"
    shards_dir.mkdir(parents=True, exist_ok=True)

    files_written = 0

    for provider_ns, prov_data in sorted(grouped_providers.items()):
        shard_metadata = {
            **grouped_metadata,
            "export_format": "sharded",
            "provider_namespace": provider_ns,
        }

        shard_summary = _build_shard_summary(prov_data, error_count)

        shard_payload = {
            "metadata": shard_metadata,
            "provider_namespace": provider_ns,
            "hosts": prov_data.get("hosts", {}),
            "summary": shard_summary,
        }

        # Sanitize provider namespace to a safe filename
        safe_name = provider_ns.replace("/", "_").replace("\\", "_")

        shard_path = shards_dir / f"{safe_name}.json"
        with open(shard_path, "w", encoding="utf-8") as fh:
            json.dump(shard_payload, fh, indent=2, ensure_ascii=False)
        files_written += 1
        if verbose:
            print(f"[SpecRecon] Written: {shard_path}")

        if minified:
            shard_min_path = shards_dir / f"{safe_name}.min.json"
            with open(shard_min_path, "w", encoding="utf-8") as fh:
                json.dump(shard_payload, fh, separators=(",", ":"), ensure_ascii=False)
            files_written += 1
            if verbose:
                print(f"[SpecRecon] Written: {shard_min_path}")

    print(f"[SpecRecon] Written: {files_written} shard file(s) → {shards_dir}")


# ---------------------------------------------------------------------------
# Main export logic
# ---------------------------------------------------------------------------

def run_export(
    source_dir: Path,
    output_dir: Path,
    minified: bool,
    verbose: bool,
    grouped: bool = False,
    sharded: bool = False,
    source_repo: str = "",
    source_branch: str = "",
    source_profile: str = _SOURCE_PROFILE_AUTO,
) -> int:
    """Execute the full export pipeline.  Returns an exit code (0 = success).

    Args:
        source_dir:    Directory containing the OpenAPI/Swagger spec files.
        output_dir:    Directory where output files are written.
        minified:      Also write minified output variants.
        verbose:       Print per-file progress messages.
        grouped:       Also write grouped/deduplicated api-index-grouped.json.
        sharded:       Also write per-provider shard files under output_dir/shards/.
        source_repo:   Identifier for the upstream spec repository (recorded in
                       metadata).  Auto-detected from git when empty.
        source_branch: Branch name used to clone the source repo (recorded in
                       metadata).  Defaults to "main" when empty.
        source_profile: Source-specific deterministic parsing profile. "auto"
                        selects Microsoft Graph only for its official repository.
    """

    print(f"[SpecRecon] Starting API inventory export")
    print(f"[SpecRecon] Source : {source_dir}")
    print(f"[SpecRecon] Output : {output_dir}")

    if not source_dir.is_dir():
        print(f"[ERROR] Source directory not found: {source_dir}", file=sys.stderr)
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)

    # Metadata
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    source_commit = _get_git_commit(source_dir.parent if source_dir.parent.is_dir() else source_dir)

    # Attempt to auto-detect source_repo from the git remote URL when not supplied
    if not source_repo:
        source_repo = _detect_source_repo(source_dir)

    resolved_source_branch = source_branch or _DEFAULT_SOURCE_BRANCH
    resolved_source_profile = _resolve_source_profile(source_profile, source_repo)
    print(f"[SpecRecon] Profile: {resolved_source_profile}")

    metadata = {
        "generated_at": generated_at,
        "source_repo": source_repo,
        "source_branch": resolved_source_branch,
        "source_commit": source_commit,
        "export_scope": source_dir.name,
        "tool_name": TOOL_NAME,
        "tool_component": TOOL_COMPONENT,
        "schema_version": SCHEMA_VERSION,
    }

    # Discover spec files
    print(f"[SpecRecon] Scanning spec files …")
    is_graph_profile = resolved_source_profile == _SOURCE_PROFILE_MICROSOFT_GRAPH
    spec_files = discover_spec_files(
        source_dir,
        include_yaml=is_graph_profile,
        allowed_relative_paths=set(_MICROSOFT_GRAPH_OPENAPI_PATHS) if is_graph_profile else None,
    )
    print(f"[SpecRecon] Found {len(spec_files)} spec files to inspect")

    all_operations = []
    errors = []

    for i, spec_file in enumerate(spec_files, start=1):
        if verbose:
            print(f"[{i}/{len(spec_files)}] {spec_file.name}", end="  ")
        ops, err = _parse_spec_file(
            spec_file,
            source_dir,
            verbose,
            include_research_metadata=grouped or sharded,
            source_profile=resolved_source_profile,
        )
        if err:
            errors.append(err)
            if verbose:
                print(f"[WARN] {err}")
            else:
                print(f"[WARN] {err}", file=sys.stderr)
        all_operations.extend(ops)

    summary = _build_summary(all_operations, len(spec_files), len(errors))

    flat_operations = [
        {key: value for key, value in operation.items() if not key.startswith("_")}
        for operation in all_operations
    ]
    payload = {
        "metadata": metadata,
        "operations": flat_operations,
        "summary": summary,
    }

    # Write full JSON
    full_path = output_dir / "api-index.json"
    with open(full_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
    print(f"[SpecRecon] Written: {full_path}")

    # Write minified JSON (optional)
    if minified:
        min_path = output_dir / "api-index.min.json"
        with open(min_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, separators=(",", ":"), ensure_ascii=False)
        print(f"[SpecRecon] Written: {min_path}")

    # Write grouped / deduplicated JSON (optional)
    if grouped or sharded:
        grouped_providers = _build_grouped_index(all_operations)
        grouped_summary = _build_grouped_summary(grouped_providers, len(spec_files), len(errors))
        grouped_metadata = {
            **metadata,
            "schema_version": GROUPED_SCHEMA_VERSION,
            "export_format": "grouped",
        }
        grouped_payload = {
            "metadata": grouped_metadata,
            "providers": grouped_providers,
            "summary": grouped_summary,
        }

        if grouped:
            grouped_path = output_dir / "api-index-grouped.json"
            with open(grouped_path, "w", encoding="utf-8") as fh:
                json.dump(grouped_payload, fh, indent=2, ensure_ascii=False)
            print(f"[SpecRecon] Written: {grouped_path}")

            if minified:
                grouped_min_path = output_dir / "api-index-grouped.min.json"
                with open(grouped_min_path, "w", encoding="utf-8") as fh:
                    json.dump(grouped_payload, fh, separators=(",", ":"), ensure_ascii=False)
                print(f"[SpecRecon] Written: {grouped_min_path}")

        if sharded:
            _write_sharded_index(
                grouped_providers,
                grouped_metadata,
                output_dir,
                len(errors),
                minified,
                verbose,
            )

    # Print summary
    print()
    print("=" * 60)
    print(f"  SpecRecon API Inventory Export — Summary")
    print("=" * 60)
    print(f"  Spec files processed : {summary['total_spec_files']}")
    print(f"  Operations indexed   : {summary['total_operations']}")
    print(f"  Providers found      : {len(summary['providers'])}")
    print(f"  Plane breakdown      : {summary['planes']}")
    print(f"  Errors / skipped     : {summary['errors']}")
    print("=" * 60)

    return 0


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Export a normalized API inventory from any OpenAPI/Swagger spec directory. "
            "Works with azure-rest-api-specs and any other spec corpus."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--source-config",
        default="",
        metavar="PATH",
        help="Optional source config used to derive source path, provenance, and export profile",
    )
    parser.add_argument(
        "--source",
        default="",
        help="Path to the specifications directory (default: source config or azure-rest-api-specs/specification)",
    )
    parser.add_argument(
        "--output-dir",
        default="inventory/",
        help="Directory to write the output files (default: inventory/)",
    )
    parser.add_argument(
        "--source-repo",
        default="",
        metavar="ORG/REPO",
        help=(
            "Upstream repository identifier recorded in the export metadata "
            "(e.g. 'Azure/azure-rest-api-specs'). "
            "Auto-detected from git when omitted."
        ),
    )
    parser.add_argument(
        "--source-branch",
        default="",
        metavar="BRANCH",
        help=(
            "Branch name recorded in the export metadata (e.g. 'main'). "
            "Defaults to 'main' when omitted."
        ),
    )
    parser.add_argument(
        "--source-profile",
        choices=[
            _SOURCE_PROFILE_AUTO,
            _SOURCE_PROFILE_GENERIC,
            _SOURCE_PROFILE_MICROSOFT_GRAPH,
        ],
        default=_SOURCE_PROFILE_AUTO,
        help=(
            "Source-specific parsing profile. 'auto' selects microsoft-graph "
            "only for source_repo microsoftgraph/msgraph-metadata."
        ),
    )
    parser.add_argument(
        "--minified",
        action="store_true",
        help="Also produce a minified api-index.min.json",
    )
    parser.add_argument(
        "--grouped",
        action="store_true",
        help=(
            "Also produce a grouped/deduplicated api-index-grouped.json "
            "(schema 3.2.0). Routes are grouped by provider → host → route, "
            "with version-specific info nested underneath."
        ),
    )
    parser.add_argument(
        "--sharded",
        action="store_true",
        help=(
            "Also produce per-provider shard files under {output-dir}/shards/. "
            "Each file is named {Provider.Namespace}.json and contains only that "
            "provider's routes in the same grouped (schema 3.2.0) structure."
        ),
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print per-file progress messages",
    )
    return parser


def main():
    parser = _build_parser()
    args = parser.parse_args()

    config = {}
    if args.source_config:
        try:
            config = _load_export_source_config(Path(args.source_config).expanduser())
        except ValueError as exc:
            parser.error(str(exc))

    configured_source = ""
    if config:
        specs_dir = str(config.get("specs_dir", "")).strip()
        spec_path = str(
            config.get("export_spec_path", config.get("default_spec_path", ""))
        ).strip()
        if specs_dir:
            configured_source = str(Path(specs_dir) / spec_path) if spec_path else specs_dir

    source_dir = Path(
        args.source or configured_source or "azure-rest-api-specs/specification"
    ).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    source_repo = args.source_repo or str(config.get("source_repo", ""))
    source_branch = args.source_branch or str(config.get("source_branch", ""))
    source_profile = args.source_profile
    if source_profile == _SOURCE_PROFILE_AUTO and config.get("export_profile"):
        source_profile = str(config["export_profile"])
    if source_profile not in {
        _SOURCE_PROFILE_AUTO,
        _SOURCE_PROFILE_GENERIC,
        _SOURCE_PROFILE_MICROSOFT_GRAPH,
    }:
        parser.error(f"Unsupported export_profile in source config: {source_profile}")

    sys.exit(run_export(
        source_dir,
        output_dir,
        args.minified,
        args.verbose,
        args.grouped,
        args.sharded,
        source_repo=source_repo,
        source_branch=source_branch,
        source_profile=source_profile,
    ))


if __name__ == "__main__":
    main()
