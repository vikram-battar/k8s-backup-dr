"""Allow ``python -m k8s_backup_dr`` as an entry point."""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
