"""Tests for restore ordering: namespaces first, ingress last."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from k8s_backup_dr.planner import build_plan, format_plan


def _bundle():
    return {
        "resources": {
            "Ingress": [{"metadata": {"name": "web-ing", "namespace": "shop"}}],
            "Deployment": [{"metadata": {"name": "web", "namespace": "shop"}}],
            "Namespace": [{"metadata": {"name": "shop"}}],
            "ConfigMap": [{"metadata": {"name": "web-cfg", "namespace": "shop"}}],
            "Secret": [{"metadata": {"name": "web-sec", "namespace": "shop"}}],
            "Service": [{"metadata": {"name": "web-svc", "namespace": "shop"}}],
        }
    }


def test_plan_orders_by_dependency_not_input_order():
    kinds = [step["kind"] for step in build_plan(_bundle())]
    assert kinds == ["Namespace", "ConfigMap", "Secret", "Deployment", "Service", "Ingress"]


def test_plan_steps_are_numbered_from_one():
    steps = build_plan(_bundle())
    assert [step["step"] for step in steps] == [1, 2, 3, 4, 5, 6]
    assert all(step["action"] == "create" for step in steps)


def test_secret_step_warns_values_are_not_in_bundle():
    steps = build_plan(_bundle())
    secret = [s for s in steps if s["kind"] == "Secret"][0]
    assert "not in the bundle" in secret["why"]


def test_format_plan_is_readable():
    text = format_plan(build_plan(_bundle()))
    assert "1. create Namespace/shop" in text
    assert "6. create Ingress/web-ing" in text
