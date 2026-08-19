#!/usr/bin/env python3
"""Fail CI when pip-audit findings are missing from the visible risk register."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: verify_dependency_risks.py PIP_AUDIT_JSON RISK_REGISTER", file=sys.stderr)
        return 2
    report = json.loads(Path(sys.argv[1]).read_text())
    register = Path(sys.argv[2]).read_text()
    advisory_ids = {
        vulnerability["id"]
        for dependency in report.get("dependencies", [])
        for vulnerability in dependency.get("vulns", [])
    }
    undocumented = sorted(advisory for advisory in advisory_ids if advisory not in register)
    if undocumented:
        print("Undocumented dependency risks: " + ", ".join(undocumented), file=sys.stderr)
        return 1
    print(f"All {len(advisory_ids)} pip-audit findings are recorded in the dependency risk register.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
