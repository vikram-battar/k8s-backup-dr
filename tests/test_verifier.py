"""Tests for drift detection: missing, extra, and changed."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from k8s_backup_dr.verifier import format_report, verify


def _bundle(replicas=2, extra=False, secret_keys=("token",)):
    resources = {
        "Deployment": [
            {"kind": "Deployment", "metadata": {"name": "web", "namespace": "shop"},
             "spec": {"replicas": replicas}}
        ],
        "Secret": [
            {"kind": "Secret", "metadata": {"name": "api-creds", "namespace": "shop"},
             "type": "Opaque", "data_keys": list(secret_keys)}
        ],
    }
    if extra:
        resources["ConfigMap"] = [
            {"kind": "ConfigMap", "metadata": {"name": "new-cfg", "namespace": "shop"},
             "spec": {"data": {"k": "v"}}}
        ]
    return {"resources": resources}


def test_identical_bundles_report_no_drift():
    report = verify(_bundle(), _bundle())
    assert report == {"missing": [], "extra": [], "changed": []}


def test_missing_changed_and_extra_are_separated():
    backup = _bundle()
    live = _bundle(replicas=3, extra=True)
    live["resources"]["Secret"][0]["data_keys"] = ["token", "new-key"]
    report = verify(backup, live)
    assert [c["name"] for c in report["changed"]] == ["web", "api-creds"]
    assert [c["name"] for c in report["extra"]] == ["new-cfg"]
    assert report["missing"] == []


def test_deleted_resource_shows_as_missing():
    backup = _bundle()
    live = {"resources": {"Deployment": backup["resources"]["Deployment"]}}
    report = verify(backup, live)
    assert [c["name"] for c in report["missing"]] == ["api-creds"]


def test_format_report_counts_everything():
    report = verify(_bundle(), _bundle(replicas=5))
    text = format_report(report)
    assert "changed: 1" in text
    assert "total differences: 1" in text
