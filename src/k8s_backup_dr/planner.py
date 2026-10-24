"""Turn a backup bundle into an ordered restore plan.

The order is the part people get wrong when they restore by hand:
namespaces and storage first, then config, then workloads, then the
things that expose them. A plan step is a plain dict so it can be
printed, saved as JSON, or fed to a script that runs ``kubectl apply``.
"""

# Lower restores first. Secrets sit after ConfigMaps because workloads
# that mount both should find their config already in place.
RESTORE_ORDER = {
    "Namespace": 0,
    "PersistentVolumeClaim": 1,
    "ConfigMap": 2,
    "Secret": 3,
    "ServiceAccount": 4,
    "Deployment": 5,
    "StatefulSet": 5,
    "DaemonSet": 5,
    "Service": 6,
    "Ingress": 7,
    "Job": 8,
    "CronJob": 8,
}

WHY = {
    "Namespace": "namespaces must exist before anything lands in them",
    "PersistentVolumeClaim": "claims bind before pods that mount them start",
    "ConfigMap": "config must exist before workloads mount it",
    "Secret": "re-create from your secret store; values are not in the bundle",
    "ServiceAccount": "workloads reference service accounts at start",
    "Deployment": "workloads after their config and storage exist",
    "StatefulSet": "workloads after their config and storage exist",
    "DaemonSet": "workloads after their config and storage exist",
    "Service": "services after the pods they select exist",
    "Ingress": "ingress last, once services are up",
    "Job": "jobs run after the platform pieces are in place",
    "CronJob": "jobs run after the platform pieces are in place",
}


def build_plan(bundle):
    """Return a list of ordered plan steps for every resource in bundle."""
    flat = []
    for kind, items in bundle["resources"].items():
        for item in items:
            meta = item["metadata"]
            flat.append(
                {
                    "kind": kind,
                    "name": meta.get("name", ""),
                    "namespace": meta.get("namespace", ""),
                    "order": RESTORE_ORDER.get(kind, 9),
                }
            )
    flat.sort(key=lambda r: (r["order"], r["namespace"], r["name"]))
    steps = []
    for i, resource in enumerate(flat, start=1):
        steps.append(
            {
                "step": i,
                "action": "create",
                "kind": resource["kind"],
                "namespace": resource["namespace"],
                "name": resource["name"],
                "why": WHY.get(resource["kind"], "restore in dependency order"),
            }
        )
    return steps


def format_plan(steps):
    """Render plan steps as human-readable lines."""
    lines = []
    for step in steps:
        where = step["namespace"] or "-"
        lines.append(
            f"{step['step']:>3}. create {step['kind']}/{step['name']} "
            f"(ns={where}) -- {step['why']}"
        )
    return "\n".join(lines)
