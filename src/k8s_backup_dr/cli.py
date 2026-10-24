"""Command line interface for k8s-backup-dr.

Subcommands:

    collect   input-dir -> bundle JSON
    plan      bundle JSON -> ordered restore steps
    verify    bundle JSON + live input-dir (or live bundle) -> drift report

verify exits 0 when backup and live match, 1 when they differ, so it
can gate a CI job or a pre-restore check.
"""

import argparse
import json
import sys

from .collector import collect, count_resources
from .planner import build_plan, format_plan
from .verifier import format_report, verify


def _load_bundle(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _write_json(path, payload):
    if path:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, sort_keys=True)
            fh.write("\n")
    else:
        json.dump(payload, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")


def cmd_collect(args):
    bundle = collect(args.input_dir, cluster=args.cluster)
    _write_json(args.output, bundle)
    counts = count_resources(bundle)
    total = counts.pop("_total")
    print(f"collected {total} resources from {args.input_dir}", file=sys.stderr)
    for kind in sorted(counts):
        print(f"  {kind}: {counts[kind]}", file=sys.stderr)
    return 0


def cmd_plan(args):
    bundle = _load_bundle(args.backup)
    steps = build_plan(bundle)
    if args.output:
        _write_json(args.output, steps)
    else:
        print(format_plan(steps))
    print(f"{len(steps)} restore steps", file=sys.stderr)
    return 0


def cmd_verify(args):
    backup = _load_bundle(args.backup)
    if args.live_dir:
        live = collect(args.live_dir, cluster=backup.get("cluster", "live"))
    else:
        live = _load_bundle(args.live_bundle)
    report = verify(backup, live)
    if args.output:
        _write_json(args.output, report)
    else:
        print(format_report(report))
    differences = sum(len(report[b]) for b in report)
    return 1 if differences else 0


def build_parser():
    parser = argparse.ArgumentParser(
        prog="k8s-backup-dr",
        description="Back up Kubernetes state from kubectl dumps, "
        "plan restores, and check drift.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_collect = sub.add_parser("collect", help="build a bundle from kubectl JSON files")
    p_collect.add_argument("--input-dir", required=True)
    p_collect.add_argument("--output", help="bundle JSON path (default: stdout)")
    p_collect.add_argument("--cluster", default="unknown-cluster")
    p_collect.set_defaults(func=cmd_collect)

    p_plan = sub.add_parser("plan", help="print the ordered restore plan for a bundle")
    p_plan.add_argument("--backup", required=True)
    p_plan.add_argument("--output", help="plan JSON path (default: stdout text)")
    p_plan.set_defaults(func=cmd_plan)

    p_verify = sub.add_parser("verify", help="compare a bundle against live state")
    p_verify.add_argument("--backup", required=True)
    group = p_verify.add_mutually_exclusive_group(required=True)
    group.add_argument("--live-dir", help="directory of fresh kubectl JSON files")
    group.add_argument("--live-bundle", help="bundle JSON built from live state")
    p_verify.add_argument("--output", help="report JSON path (default: stdout text)")
    p_verify.set_defaults(func=cmd_verify)

    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
