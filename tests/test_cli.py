"""End-to-end CLI tests over temporary kubectl dump directories."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from k8s_backup_dr.cli import main


def _dump(tmp_path, name, items):
    (tmp_path / name).write_text(json.dumps({"items": items}), encoding="utf-8")


def test_collect_plan_verify_round_trip(tmp_path, capsys):
    src = tmp_path / "live"
    src.mkdir()
    _dump(src, "namespaces.json", [{"metadata": {"name": "shop"}}])
    _dump(src, "deployments.json", [
        {"metadata": {"name": "web", "namespace": "shop"}, "spec": {"replicas": 2}}
    ])
    bundle_path = tmp_path / "backup.json"
    assert main(["collect", "--input-dir", str(src), "--output", str(bundle_path),
                 "--cluster", "demo"]) == 0
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    assert bundle["format"] == "k8s-backup-dr/v1"
    assert bundle["resources"]["Deployment"][0]["spec"] == {"replicas": 2}

    assert main(["plan", "--backup", str(bundle_path)]) == 0
    plan_out = capsys.readouterr().out
    assert "create Namespace/shop" in plan_out
    assert "create Deployment/web" in plan_out

    # Same live state: verify passes.
    assert main(["verify", "--backup", str(bundle_path), "--live-dir", str(src)]) == 0

    # Scale the deployment: verify now reports drift and exits 1.
    _dump(src, "deployments.json", [
        {"metadata": {"name": "web", "namespace": "shop"}, "spec": {"replicas": 5}}
    ])
    assert main(["verify", "--backup", str(bundle_path), "--live-dir", str(src)]) == 1
    verify_out = capsys.readouterr().out
    assert "changed: 1" in verify_out


def test_collect_writes_bundle_to_stdout_when_no_output(tmp_path, capsys):
    _dump(tmp_path, "namespaces.json", [{"metadata": {"name": "shop"}}])
    assert main(["collect", "--input-dir", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert json.loads(out)["resources"]["Namespace"][0]["metadata"]["name"] == "shop"
