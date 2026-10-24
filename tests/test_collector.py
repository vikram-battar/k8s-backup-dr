"""Tests for the collector: parsing, stripping, and secret safety."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from k8s_backup_dr.collector import collect, strip_resource


def _write(tmp_path, name, payload):
    path = tmp_path / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_secret_values_never_land_in_bundle(tmp_path):
    _write(
        tmp_path,
        "secrets.json",
        {
            "items": [
                {
                    "metadata": {"name": "api-creds", "namespace": "shop"},
                    "type": "Opaque",
                    "data": {"token": "cGxhY2Vob2xkZXItdmFsdWU="},
                    "stringData": {"password": "hunter2-placeholder"},
                }
            ]
        },
    )
    bundle = collect(str(tmp_path))
    secret = bundle["resources"]["Secret"][0]
    assert secret["data_keys"] == ["password", "token"]
    assert "data" not in secret and "stringData" not in secret
    assert "placeholder-value" not in json.dumps(bundle)
    assert "hunter2" not in json.dumps(bundle)


def test_volatile_metadata_is_dropped(tmp_path):
    _write(
        tmp_path,
        "deployments.json",
        {
            "items": [
                {
                    "metadata": {
                        "name": "web",
                        "namespace": "shop",
                        "uid": "abc-123",
                        "resourceVersion": "98765",
                        "creationTimestamp": "2026-01-01T00:00:00Z",
                        "labels": {"app": "web"},
                    },
                    "spec": {"replicas": 2},
                }
            ]
        },
    )
    bundle = collect(str(tmp_path))
    deployment = bundle["resources"]["Deployment"][0]
    assert deployment["metadata"] == {"name": "web", "namespace": "shop", "labels": {"app": "web"}}
    assert deployment["spec"] == {"replicas": 2}


def test_unknown_files_are_ignored(tmp_path):
    _write(tmp_path, "notes.txt", {"items": []})
    _write(tmp_path, "weirdkind.json", {"items": [{"metadata": {"name": "x"}}]})
    _write(tmp_path, "namespaces.json", {"items": [{"metadata": {"name": "shop"}}]})
    bundle = collect(str(tmp_path), cluster="test-cluster")
    assert bundle["cluster"] == "test-cluster"
    assert list(bundle["resources"]) == ["Namespace"]
    assert bundle["source_files"] == ["namespaces.json"]


def test_strip_resource_keeps_spec_for_workloads():
    item = {"metadata": {"name": "api", "namespace": "shop"}, "spec": {"replicas": 3}}
    assert strip_resource(item, "Deployment")["spec"] == {"replicas": 3}
