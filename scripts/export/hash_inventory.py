#!/usr/bin/env python3
"""Compute a deterministic semantic hash for generated API inventory output."""

import argparse
import hashlib
import json
from pathlib import Path


_VOLATILE_METADATA_FIELDS = frozenset({"generated_at"})


def _canonical_payload(path: Path) -> bytes:
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    metadata = payload.get("metadata")
    if isinstance(metadata, dict):
        for field in _VOLATILE_METADATA_FIELDS:
            metadata.pop(field, None)
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def inventory_files(inventory_dir: Path, export_format: str) -> list[Path]:
    if export_format == "grouped":
        minified = inventory_dir / "api-index-grouped.min.json"
        pretty = inventory_dir / "api-index-grouped.json"
        if minified.is_file():
            return [minified]
        if pretty.is_file():
            return [pretty]
        raise FileNotFoundError("grouped inventory output not found")

    shards_dir = inventory_dir / "shards"
    minified_shards = sorted(shards_dir.glob("*.min.json"))
    if minified_shards:
        return minified_shards
    pretty_shards = sorted(
        path for path in shards_dir.glob("*.json")
        if not path.name.endswith(".min.json")
    )
    if pretty_shards:
        return pretty_shards
    raise FileNotFoundError("sharded inventory output not found")


def compute_inventory_hash(inventory_dir: Path, export_format: str) -> str:
    digest = hashlib.sha256()
    for path in inventory_files(inventory_dir, export_format):
        relative = path.relative_to(inventory_dir).as_posix().encode("utf-8")
        payload_digest = hashlib.sha256(_canonical_payload(path)).digest()
        digest.update(relative)
        digest.update(b"\0")
        digest.update(payload_digest)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory-dir", default="inventory", type=Path)
    parser.add_argument("--format", choices=["grouped", "sharded"], required=True)
    args = parser.parse_args()
    print(compute_inventory_hash(args.inventory_dir, args.format))


if __name__ == "__main__":
    main()
