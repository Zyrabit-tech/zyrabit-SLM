#!/usr/bin/env python3
"""Reject a Traefik dashboard that is open or unauthenticated."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


class DashboardConfigError(Exception):
    pass


def assert_default_dashboard_closed(compose_text: str) -> None:
    if "api.insecure=true" in compose_text or "api.insecure: true" in compose_text:
        raise DashboardConfigError("the default compose file enables the insecure Traefik API")
    if "8081:8080" in compose_text:
        raise DashboardConfigError("the default compose file publishes the Traefik dashboard")


def assert_optional_dashboard(enabled: bool, auth: str) -> None:
    if not enabled:
        return
    value = auth.strip().strip("'\"")
    user, separator, password = value.partition(":")
    if not separator or not user or not password:
        raise DashboardConfigError(
            "ZYRABIT_TRAEFIK_DASHBOARD requires TRAEFIK_DASHBOARD_AUTH=user:htpasswd_hash"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--compose", required=True)
    parser.add_argument("--enabled", choices=("true", "false"), default="false")
    parser.add_argument("--auth", default="")
    args = parser.parse_args(argv)
    try:
        assert_default_dashboard_closed(Path(args.compose).read_text(encoding="utf-8"))
        assert_optional_dashboard(args.enabled == "true", args.auth)
    except DashboardConfigError as exc:
        print(f"traefik dashboard rejected: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
