"""Tests for semantic inventory hashing used by export workflows."""

import json
import sys
from pathlib import Path

_EXPORT_DIR = Path(__file__).parent.parent / "scripts" / "export"
sys.path.insert(0, str(_EXPORT_DIR))

import hash_inventory


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _payload(generated_at: str, route: str = "GET /things") -> dict:
    return {
        "metadata": {
            "generated_at": generated_at,
            "source_commit": "abc123",
            "schema_version": "3.2.0",
        },
        "providers": {
            "Example.Service": {
                "hosts": {
                    "api.example.com": {
                        "routes": {route: {"method": "GET"}},
                    }
                }
            }
        },
    }


def test_grouped_hash_ignores_generated_timestamp(tmp_path):
    output = tmp_path / "inventory"
    path = output / "api-index-grouped.min.json"
    _write(path, _payload("2026-09-20T01:00:00Z"))
    first = hash_inventory.compute_inventory_hash(output, "grouped")
    _write(path, _payload("2026-09-20T02:00:00Z"))
    second = hash_inventory.compute_inventory_hash(output, "grouped")
    assert first == second


def test_grouped_hash_changes_with_semantic_content(tmp_path):
    output = tmp_path / "inventory"
    path = output / "api-index-grouped.min.json"
    _write(path, _payload("2026-09-20T01:00:00Z"))
    first = hash_inventory.compute_inventory_hash(output, "grouped")
    _write(path, _payload("2026-09-20T01:00:00Z", route="GET /other"))
    second = hash_inventory.compute_inventory_hash(output, "grouped")
    assert first != second


def test_sharded_hash_is_stable_across_file_creation_order(tmp_path):
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    _write(first_dir / "shards" / "B.min.json", _payload("2026-09-20T01:00:00Z", "GET /b"))
    _write(first_dir / "shards" / "A.min.json", _payload("2026-09-20T01:00:00Z", "GET /a"))
    _write(second_dir / "shards" / "A.min.json", _payload("2026-09-21T01:00:00Z", "GET /a"))
    _write(second_dir / "shards" / "B.min.json", _payload("2026-09-21T01:00:00Z", "GET /b"))
    assert hash_inventory.compute_inventory_hash(first_dir, "sharded") == hash_inventory.compute_inventory_hash(second_dir, "sharded")


def test_sharded_hash_changes_when_file_set_changes(tmp_path):
    output = tmp_path / "inventory"
    _write(output / "shards" / "A.min.json", _payload("2026-09-20T01:00:00Z", "GET /a"))
    first = hash_inventory.compute_inventory_hash(output, "sharded")
    _write(output / "shards" / "B.min.json", _payload("2026-09-20T01:00:00Z", "GET /b"))
    second = hash_inventory.compute_inventory_hash(output, "sharded")
    assert first != second
