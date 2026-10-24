#!/usr/bin/env bash
# Dump one namespace (or everything with -A) into a directory the CLI can read.
# Usage: ./examples/collect.sh shop ./backups/2026-10-24
# Pass "all" as the namespace to dump every namespace.
set -euo pipefail

NAMESPACE="${1:-shop}"
OUT_DIR="${2:-./backups/$(date +%F)}"
mkdir -p "$OUT_DIR"

if [ "$NAMESPACE" = "all" ]; then
  SCOPE="-A"
else
  SCOPE="-n $NAMESPACE"
fi

# shellcheck disable=SC2086
for kind in namespaces deployments statefulsets daemonsets services configmaps secrets persistentvolumeclaims ingresses jobs cronjobs; do
  kubectl get "$kind" $SCOPE -o json > "$OUT_DIR/$kind.json" || echo "skipping $kind (not available)"
done

echo "dumps written to $OUT_DIR"
echo "next: PYTHONPATH=src python3 -m k8s_backup_dr collect --input-dir $OUT_DIR --output backup.json"
