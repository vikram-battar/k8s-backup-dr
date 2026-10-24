"""k8s-backup-dr: backup, restore planning, and drift checks for Kubernetes.

The package never talks to a cluster itself. You hand it kubectl JSON
output, and it builds a bundle, a restore plan, and a drift report.
"""

__version__ = "0.1.0"
