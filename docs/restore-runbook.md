# Restore runbook

A short checklist for the day you actually need the backup. Print it or
keep it next to your bundles.

## Before you touch anything

1. Confirm what is broken. Run `verify` against a fresh live dump first —
   a partial outage and a full namespace loss call for different restores.
2. Tell the team the cluster is in restore mode. Nobody else should be
   deploying while you work through the plan.
3. Copy the bundle somewhere safe before you start. Do not work off the
   only copy.

## Restore order

Follow the plan output in order. In short:

1. Namespace.
2. PersistentVolumeClaims. If the underlying volumes are gone, restore
   volume snapshots first — this tool records claims, not volume data.
3. ConfigMaps.
4. Secrets, re-created from your secret store. Check every key name in
   the bundle against the store before moving on.
5. Workloads (Deployments, StatefulSets, DaemonSets).
6. Services.
7. Ingress.
8. Jobs and CronJobs last, and only after you confirm the workloads
   they depend on are healthy.

## After the restore

1. Run `verify` again. Missing should be 0. Extra items need a human
   decision: keep them or delete them, one by one.
2. Check pod status, then service endpoints, then ingress routes, in
   that order.
3. Write down what caused the outage and what the restore missed. Feed
   the gaps back into the backup schedule.

## Backup schedule suggestion

- Nightly `collect` for every production namespace, kept for 30 days.
- A `verify` run in CI once a day against the previous night's bundle,
  so drift shows up as a failing check instead of a surprise.
- A restore drill once a quarter on a throwaway namespace. A backup you
  have never restored from is a guess, not a backup.
