# k8s-backup-dr

I built this because I have watched restores go wrong in the same boring way
more than once: someone deletes a namespace, or a bad deploy wipes a set of
workloads, and the recovery turns into a scramble through old manifests.
Nobody remembers the exact order things need to come back in, and nobody is
sure what changed since the last good state. This tool answers those two
questions before you need them, not during the incident.

It does three things, and nothing else:

1. **Collect** — turns `kubectl` JSON dumps into one backup bundle.
2. **Plan** — prints the restore order: namespaces first, then storage and
   config, then workloads, then services and ingress.
3. **Verify** — compares a bundle against fresh live state and reports what
   is missing, what is new, and what changed.

## The one rule that matters

Secret values are never stored. The bundle records a Secret's name,
namespace, type, and key names only. If you see a real secret value in a
bundle, that is a bug — open an issue. Restoring secrets is your job, from
your secret store, and the plan step for each Secret says so out loud.

This is a portfolio reference implementation built from my own side-project
experience, not code or data from any employer.

## Requirements

- Python 3.9 or newer. No third-party runtime dependencies — the tool uses
  only the standard library.
- `kubectl` with access to the cluster you want to back up.
- `pytest` if you want to run the tests.

## Quick start

Clone the repo and dump a namespace:

```bash
git clone https://github.com/vikram-battar/k8s-backup-dr.git
cd k8s-backup-dr
./examples/collect.sh shop ./backups/2026-10-24
```

That script writes one JSON file per resource kind into the backup
directory. Then build the bundle:

```bash
PYTHONPATH=src python3 -m k8s_backup_dr collect \
  --input-dir ./backups/2026-10-24 \
  --output backup.json \
  --cluster my-eks-cluster
```

You will see a count per kind on stderr, like this:

```text
collected 6 resources from ./backups/2026-10-24
  ConfigMap: 1
  Deployment: 1
  Namespace: 1
  PersistentVolumeClaim: 1
  Secret: 1
  Service: 1
```

## Get the restore plan

```bash
PYTHONPATH=src python3 -m k8s_backup_dr plan --backup backup.json
```

Output looks like this:

```text
  1. create Namespace/shop (ns=-) -- namespaces must exist before anything lands in them
  2. create PersistentVolumeClaim/web-data (ns=shop) -- claims bind before pods that mount them start
  3. create ConfigMap/web-cfg (ns=shop) -- config must exist before workloads mount it
  4. create Secret/api-creds (ns=shop) -- re-create from your secret store; values are not in the bundle
  5. create Deployment/web (ns=shop) -- workloads after their config and storage exist
  6. create Service/web-svc (ns=shop) -- services after the pods they select exist
```

Work through the steps in order with `kubectl apply` against your own
manifests. The tool plans the order; it does not apply anything for you.
That is deliberate. An automatic restore that guesses wrong can do more
damage than the outage it is fixing.

To save the plan as JSON instead of text:

```bash
PYTHONPATH=src python3 -m k8s_backup_dr plan --backup backup.json --output plan.json
```

## Check for drift

Dump the live state again, then compare:

```bash
./examples/collect.sh shop ./backups/live-now
PYTHONPATH=src python3 -m k8s_backup_dr verify \
  --backup backup.json \
  --live-dir ./backups/live-now
```

Output:

```text
missing: 0
extra: 0
changed: 1
  - Deployment/web (ns=shop)
total differences: 1
```

`verify` exits 0 when backup and live match and 1 when they differ, so you
can run it in CI or as a pre-restore check. A `--live-bundle` option takes
a bundle file instead of a dump directory, and `--output` writes the report
as JSON.

## Try it without a cluster

The `examples/` directory holds small kubectl dumps for a fake `shop`
namespace. No cluster needed:

```bash
PYTHONPATH=src python3 -m k8s_backup_dr collect --input-dir examples --output /tmp/backup.json
PYTHONPATH=src python3 -m k8s_backup_dr plan --backup /tmp/backup.json
PYTHONPATH=src python3 -m k8s_backup_dr verify --backup /tmp/backup.json --live-dir examples
```

The last command should exit 0: the example bundle compared against itself
has no drift.

## What this does not do

- It does not talk to your cluster. You run `kubectl` yourself, which means
  it works with whatever auth and context you already trust, and it never
  needs cluster credentials of its own.
- It does not back up persistent volume data. It records the claim. Your
  volume snapshots are a separate job — see `docs/restore-runbook.md`.
- It does not restore secret values. See the rule above.
- It does not replace Velero or a managed backup service. If you run
  Velero, keep running it. This tool is for the gap Velero leaves: a
  plain, readable record of what your cluster looked like, in an order you
  can restore by hand when the fancy tooling is not available.

## Project layout

```text
src/k8s_backup_dr/
  collector.py   kubectl JSON -> bundle (strips secrets and volatile metadata)
  planner.py     bundle -> ordered restore steps
  verifier.py    bundle vs live -> missing / extra / changed
  cli.py         collect / plan / verify commands
tests/           pytest suite (collector, planner, verifier, CLI round trip)
examples/        sample kubectl dumps, collect.sh, generated example bundle
docs/            restore runbook
.github/workflows/ci.yml
```

## Tests

```bash
pip install pytest
PYTHONPATH=src pytest -q
```

## License

MIT. See `LICENSE`.
