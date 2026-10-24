"""Compare a backup bundle against a fresh live snapshot.

Three buckets, nothing else:

- missing: in the backup, gone from the live cluster.
- extra: live, but not in the backup (new since the backup ran).
- changed: present in both, but the spec (or a Secret's key list) differs.

Volatile metadata (resource versions, timestamps, UIDs) is already
stripped at collect time, so it cannot show up as a false diff.
"""


def _index(bundle):
    index = {}
    for kind, items in bundle["resources"].items():
        for item in items:
            meta = item["metadata"]
            key = (kind, meta.get("namespace", ""), meta.get("name", ""))
            index[key] = item
    return index


def _comparable(item):
    if item["kind"] == "Secret":
        return {"type": item.get("type"), "data_keys": item.get("data_keys", [])}
    return item.get("spec")


def verify(backup, live):
    """Return a report dict with missing, extra, and changed lists."""
    backup_index = _index(backup)
    live_index = _index(live)
    missing, extra, changed = [], [], []
    for key, item in sorted(backup_index.items()):
        if key not in live_index:
            missing.append({"kind": key[0], "namespace": key[1], "name": key[2]})
        elif _comparable(item) != _comparable(live_index[key]):
            changed.append({"kind": key[0], "namespace": key[1], "name": key[2]})
    for key in sorted(live_index):
        if key not in backup_index:
            extra.append({"kind": key[0], "namespace": key[1], "name": key[2]})
    return {"missing": missing, "extra": extra, "changed": changed}


def format_report(report):
    """Render a verify report as human-readable text."""
    lines = []
    for bucket in ("missing", "extra", "changed"):
        items = report[bucket]
        lines.append(f"{bucket}: {len(items)}")
        for item in items:
            lines.append(f"  - {item['kind']}/{item['name']} (ns={item['namespace'] or '-'})")
    total = sum(len(report[b]) for b in report)
    lines.append(f"total differences: {total}")
    return "\n".join(lines)
