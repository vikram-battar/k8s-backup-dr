"""Turn kubectl JSON dumps into a single backup bundle.

Input: a directory of files named after the resource kind, one per file,
for example ``deployments.json`` produced by::

    kubectl get deployments -A -o json > deployments.json

Output: a bundle dict with format ``k8s-backup-dr/v1``.

Secret values are never kept. For a Secret the bundle records only the
name, namespace, type, and the sorted list of data key names. If a value
ever shows up in a bundle, that is a bug, not a feature.
"""

import json
import os
from datetime import datetime, timezone

# File name (lowercase, plural, as kubectl prints it) -> Kind name.
KIND_BY_FILE = {
    "namespaces": "Namespace",
    "deployments": "Deployment",
    "statefulsets": "StatefulSet",
    "daemonsets": "DaemonSet",
    "services": "Service",
    "configmaps": "ConfigMap",
    "secrets": "Secret",
    "persistentvolumeclaims": "PersistentVolumeClaim",
    "ingresses": "Ingress",
    "jobs": "Job",
    "cronjobs": "CronJob",
}


def _kept_metadata(item):
    """Keep identity metadata only; drop timestamps, UIDs, managed fields."""
    meta = item.get("metadata") or {}
    kept = {}
    for key in ("name", "namespace", "labels", "annotations"):
        if meta.get(key) is not None:
            kept[key] = meta[key]
    return kept


def strip_resource(item, kind):
    """Reduce one kubectl item to what a restore actually needs."""
    meta = _kept_metadata(item)
    if kind == "Secret":
        data = item.get("data") or {}
        string_data = item.get("stringData") or {}
        keys = sorted(set(data) | set(string_data))
        return {
            "kind": "Secret",
            "metadata": meta,
            "type": item.get("type", "Opaque"),
            "data_keys": keys,
            "note": "values not stored; re-create from your secret store",
        }
    out = {"kind": kind, "metadata": meta}
    if item.get("spec") is not None:
        out["spec"] = item["spec"]
    return out


def collect(input_dir, cluster="unknown-cluster"):
    """Build a bundle from every recognised ``*.json`` file in input_dir."""
    resources = {}
    files_seen = []
    for filename in sorted(os.listdir(input_dir)):
        if not filename.endswith(".json"):
            continue
        stem = filename[:-5]
        if stem not in KIND_BY_FILE:
            continue
        kind = KIND_BY_FILE[stem]
        with open(os.path.join(input_dir, filename), encoding="utf-8") as fh:
            payload = json.load(fh)
        items = payload.get("items", [])
        resources[kind] = [strip_resource(item, kind) for item in items]
        files_seen.append(filename)
    bundle = {
        "format": "k8s-backup-dr/v1",
        "cluster": cluster,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "source_files": files_seen,
        "resources": resources,
    }
    return bundle


def count_resources(bundle):
    """Return {kind: count} for a bundle, plus a ``_total`` entry."""
    counts = {kind: len(items) for kind, items in bundle["resources"].items()}
    counts["_total"] = sum(counts.values())
    return counts
