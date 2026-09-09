#!/usr/bin/env python3
"""
Case 3 demo: chat intent → policy → HITL → allowlisted webhook → audit.

Does not require the full Zyrabit stack. Models the governed-ops path from
docs/engineering/AGENT_TOOL_RUNTIME_MAP.md so anyone can replicate locally.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out"
OUT.mkdir(exist_ok=True)
AUDIT = OUT / "audit.jsonl"
POLICY_PATH = ROOT / "policy.yml"
WEBHOOK = "http://127.0.0.1:8765/tickets"


def load_policy() -> dict:
    text = POLICY_PATH.read_text(encoding="utf-8")
    if yaml is not None:
        return yaml.safe_load(text)
    # tiny fallback parser for this file's shape (no PyYAML required)
    # Prefer PyYAML when available; otherwise use embedded JSON sibling.
    json_fallback = ROOT / "policy.json"
    if json_fallback.exists():
        return json.loads(json_fallback.read_text(encoding="utf-8"))
    raise SystemExit(
        "PyYAML not installed and policy.json missing. "
        "Run: pip install pyyaml   OR use the bundled policy.json"
    )


def decide(policy: dict, profile: str, tool: str) -> tuple[str, str]:
    prof = policy["profiles"].get(profile) or policy["profiles"]["safe"]
    for rule in prof.get("rules", []):
        if rule.get("tool") == tool:
            return rule.get("decision", prof.get("default", "deny")), rule.get("risk", "unknown")
    return prof.get("default", "deny"), "unknown"


def audit(event: dict) -> None:
    event = {"ts": datetime.now(timezone.utc).isoformat(), **event}
    with AUDIT.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
    print(f"[audit] {event['event']}: {json.dumps(event, ensure_ascii=False)}")


def post_ticket(payload: dict) -> dict:
    req = urllib.request.Request(
        WEBHOOK,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Zyrabit Case 3 HITL ops demo")
    parser.add_argument("--profile", default="ops", choices=["safe", "ops"])
    parser.add_argument("--tool", default="ticket.create")
    parser.add_argument("--title", default="Fallo de login en prod")
    parser.add_argument("--priority", default="high")
    parser.add_argument("--body", default="Usuarios no pueden autenticarse desde 21:00 CT.")
    parser.add_argument("--requester", default="abraham")
    parser.add_argument(
        "--approve",
        choices=["yes", "no", "auto-deny-demo"],
        default="yes",
        help="HITL decision (yes=approve write tools)",
    )
    parser.add_argument(
        "--deny-tool",
        default="",
        help="If set, attempt this tool instead (e.g. nmap.scan) to show deny",
    )
    args = parser.parse_args()

    policy = load_policy()
    tool = args.deny_tool or args.tool
    decision, risk = decide(policy, args.profile, tool)

    print("=== Case 3: Governed ops agent ===")
    print(f"profile={args.profile} tool={tool} risk={risk} policy={decision}")
    audit(
        {
            "event": "tool_proposed",
            "profile": args.profile,
            "tool": tool,
            "risk": risk,
            "policy": decision,
            "args": {"title": args.title, "priority": args.priority},
        }
    )

    if decision == "deny":
        audit({"event": "tool_denied", "tool": tool, "reason": "policy_deny"})
        print("RESULT: DENIED by policy (expected for unsafe tools).")
        return 0

    if decision == "ask_human":
        print(f"HITL required for `{tool}` (risk={risk}).")
        if args.approve != "yes":
            audit({"event": "hitl_rejected", "tool": tool, "by": args.requester})
            print("RESULT: HITL rejected — no side effects.")
            return 0
        audit({"event": "hitl_approved", "tool": tool, "by": args.requester})
        print(f"HITL approved by {args.requester}")

    if tool != "ticket.create":
        audit({"event": "tool_skipped", "tool": tool, "reason": "demo_only_implements_ticket.create"})
        print("RESULT: policy allowed/asked but this demo only executes ticket.create")
        return 0

    try:
        result = post_ticket(
            {
                "title": args.title,
                "priority": args.priority,
                "body": args.body,
                "requester": args.requester,
                "source": "zyrabit-case3-demo",
            }
        )
    except urllib.error.URLError as exc:
        audit({"event": "tool_error", "tool": tool, "error": str(exc)})
        print(
            "ERROR: mock ticket inbox not reachable.\n"
            "Start it in another terminal:\n"
            "  python3 examples/case3-hitl-ops/scripts/mock_ticket_server.py",
            file=sys.stderr,
        )
        return 1

    audit(
        {
            "event": "tool_succeeded",
            "tool": tool,
            "ticket_id": result.get("ticket", {}).get("id"),
            "result_ok": result.get("ok"),
        }
    )
    print("RESULT: ticket created")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"audit log → {AUDIT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
