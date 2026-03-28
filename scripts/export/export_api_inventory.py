#!/usr/bin/env python3
"""
export_api_inventory.py — SpecRecon API Inventory Export

Walks the azure-rest-api-specs/specification/ directory tree, parses every
OpenAPI/Swagger JSON spec file, and produces a normalized api-index.json that
can later be used for "spec vs reality" comparison of Azure REST API calls.

Usage:
    python3 scripts/export/export_api_inventory.py [options]

Options:
    --source      Path to the specifications directory (default: azure-rest-api-specs/specification)
    --output-dir  Directory where the output files are written (default: inventory/)
    --minified    Also produce a minified api-index.min.json (no indentation)
    --grouped     Also produce a grouped/deduplicated api-index-grouped.json (schema 3.0.0)
    --sharded     Also produce per-provider shards under {output-dir}/shards/ (schema 3.0.0)
    --verbose     Print per-file progress messages

Output files:
    api-index.json                     Flat pretty-printed index (schema 2.1.0)
    api-index.min.json                 Flat minified index (with --minified)
    api-index-grouped.json             Grouped/deduplicated index (with --grouped, schema 3.0.0)
    api-index-grouped.min.json         Grouped minified index (with --grouped --minified)
    shards/{Provider.Namespace}.json   Per-provider shard (with --sharded, schema 3.0.0)
    shards/{Provider.Namespace}.min.json  Minified per-provider shard (with --sharded --minified)
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

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
GROUPED_SCHEMA_VERSION = "3.0.0"  # grouped/deduplicated format
SOURCE_REPO = "Azure/azure-rest-api-specs"
SOURCE_BRANCH = "main"

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


# ---------------------------------------------------------------------------
# Spec-file discovery
# ---------------------------------------------------------------------------

def _should_skip_dir(dir_name: str) -> bool:
    """Return True when a directory should be excluded from traversal."""
    return dir_name.lower() in _SKIP_DIRS


def discover_spec_files(source_dir: Path) -> list:
    """Yield all JSON spec files under *source_dir*, skipping skip-listed dirs."""
    spec_files = []
    for root, dirs, files in os.walk(source_dir):
        # Prune directories in-place so os.walk doesn't descend into them
        dirs[:] = [d for d in dirs if not _should_skip_dir(d)]
        for fname in files:
            if fname.endswith(".json"):
                spec_files.append(Path(root) / fname)
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
            # Strip scheme and path to get just the host
            stripped = first_url.split("//", 1)[-1].split("/")[0].strip()
            if stripped:
                return stripped.lower()

    return "unknown"


def _parse_spec_file(file_path: Path, source_dir: Path, verbose: bool) -> tuple:
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
        with open(file_path, "r", encoding="utf-8", errors="replace") as fh:
            spec = json.load(fh)
    except json.JSONDecodeError as exc:
        return [], f"JSON decode error in {file_path}: {exc}"
    except OSError as exc:
        return [], f"Cannot read {file_path}: {exc}"

    if not isinstance(spec, dict):
        return [], None  # Not a spec object — skip silently

    # Accept Swagger 2.0 and OpenAPI 3.x
    is_swagger2 = str(spec.get("swagger", "")).startswith("2")
    is_openapi3 = str(spec.get("openapi", "")).startswith("3")
    if not is_swagger2 and not is_openapi3:
        return [], None  # Not a recognized OpenAPI spec — skip

    host = _detect_host(spec, file_path)
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

        for path_template, path_item in paths_obj.items():
            if not isinstance(path_item, dict):
                continue

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
        ns = extract_provider_namespace(op["path_template"])
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
        provider_ns = extract_provider_namespace(path_template)
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
                }
            ver = route["versions"][api_version]
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

def run_export(source_dir: Path, output_dir: Path, minified: bool, verbose: bool, grouped: bool = False, sharded: bool = False) -> int:
    """Execute the full export pipeline.  Returns an exit code (0 = success)."""

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

    metadata = {
        "generated_at": generated_at,
        "source_repo": SOURCE_REPO,
        "source_branch": SOURCE_BRANCH,
        "source_commit": source_commit,
        "export_scope": source_dir.name,
        "tool_name": TOOL_NAME,
        "tool_component": TOOL_COMPONENT,
        "schema_version": SCHEMA_VERSION,
    }

    # Discover spec files
    print(f"[SpecRecon] Scanning spec files …")
    spec_files = discover_spec_files(source_dir)
    print(f"[SpecRecon] Found {len(spec_files)} JSON files to inspect")

    all_operations = []
    errors = []

    for i, spec_file in enumerate(spec_files, start=1):
        if verbose:
            print(f"[{i}/{len(spec_files)}] {spec_file.name}", end="  ")
        ops, err = _parse_spec_file(spec_file, source_dir, verbose)
        if err:
            errors.append(err)
            if verbose:
                print(f"[WARN] {err}")
            else:
                print(f"[WARN] {err}", file=sys.stderr)
        all_operations.extend(ops)

    summary = _build_summary(all_operations, len(spec_files), len(errors))

    payload = {
        "metadata": metadata,
        "operations": all_operations,
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
        description="Export a normalized API inventory from Azure REST API specs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--source",
        default="azure-rest-api-specs/specification",
        help="Path to the specifications directory (default: azure-rest-api-specs/specification)",
    )
    parser.add_argument(
        "--output-dir",
        default="inventory/",
        help="Directory to write the output files (default: inventory/)",
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
            "(schema 3.0.0). Routes are grouped by provider → host → route, "
            "with version-specific info nested underneath."
        ),
    )
    parser.add_argument(
        "--sharded",
        action="store_true",
        help=(
            "Also produce per-provider shard files under {output-dir}/shards/. "
            "Each file is named {Provider.Namespace}.json and contains only that "
            "provider's routes in the same grouped (schema 3.0.0) structure."
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

    source_dir = Path(args.source).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()

    sys.exit(run_export(source_dir, output_dir, args.minified, args.verbose, args.grouped, args.sharded))


if __name__ == "__main__":
    main()
