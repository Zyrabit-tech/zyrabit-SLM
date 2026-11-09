#!/usr/bin/env python3
"""Decide whether a git ref may publish Zyrabit images.

Beta tags publish prerelease identifiers and never move ``latest``.
Stable tags publish ``latest`` only when the tagged commit is on ``main``
and the tag matches ``VERSION``. Published version tags are immutable;
this script only names them. The workflow refuses to move an existing one.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

STABLE = re.compile(r"^v(\d+\.\d+\.\d+)$")
BETA = re.compile(r"^v(\d+\.\d+\.\d+)-beta\.(\d+)$")


class ReleaseRefError(Exception):
    """The ref is a release tag, but it is not allowed to publish."""


def next_beta_tag(version: str, existing_tags: set[str]) -> str | None:
    """Return the single prerelease tag for a VERSION, never a stable ``vX.Y.Z`` tag.

    ``v2.4.8`` and any later stable tag stay untouched. A second push of the
    same VERSION does not allocate ``beta.2``; the operator bumps VERSION
    when a prerelease must be rebuilt, because published tags are immutable.
    """
    version = version.strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ReleaseRefError(f"VERSION {version} is not X.Y.Z")
    tag = f"v{version}-beta.1"
    stable = f"v{version}"
    if stable in existing_tags and tag in existing_tags:
        return None
    if tag in existing_tags:
        return None
    return tag


def resolve_release_channel(ref_name: str, version_file: str, commit_on_main: bool) -> dict:
    """Return the publish plan for a git ref.

    Non-release refs return ``channel=skip`` so a branch dispatch cannot
    move ``latest``. A stable tag whose commit is not on ``main``, or whose
    number disagrees with ``VERSION``, raises ``ReleaseRefError``.
    """
    version_file = version_file.strip()
    beta = BETA.fullmatch(ref_name)
    if beta:
        version = beta.group(1)
        prerelease = f"{version}-beta.{beta.group(2)}"
        return {
            "channel": "beta",
            "version": version,
            "git_tag": ref_name,
            "immutable_tags": prerelease,
            "mutable_tags": "beta",
            "prerelease": "true",
        }

    stable = STABLE.fullmatch(ref_name)
    if stable:
        version = stable.group(1)
        if version != version_file:
            raise ReleaseRefError(
                f"stable tag {ref_name} does not match VERSION {version_file}"
            )
        if not commit_on_main:
            raise ReleaseRefError(
                f"stable tag {ref_name} does not point at a commit on main"
            )
        return {
            "channel": "stable",
            "version": version,
            "git_tag": ref_name,
            "immutable_tags": version,
            "mutable_tags": "latest",
            "prerelease": "false",
        }

    return {
        "channel": "skip",
        "version": version_file,
        "git_tag": ref_name,
        "immutable_tags": "",
        "mutable_tags": "",
        "prerelease": "false",
    }


def format_ledger(plan: dict, sha: str, digests: dict[str, str]) -> str:
    """Render the version, tag, SHA, and image digests that were published."""
    missing = [arch for arch in ("amd64", "arm64") if arch not in digests]
    if missing:
        raise ReleaseRefError(
            "both amd64 and arm64 digests are required before a manifest is published; "
            f"missing {', '.join(missing)}"
        )
    record = {
        "channel": plan["channel"],
        "version": plan["version"],
        "git_tag": plan["git_tag"],
        "sha": sha,
        "immutable_tags": plan["immutable_tags"],
        "mutable_tags": plan["mutable_tags"],
        "digests": digests,
    }
    return json.dumps(record, indent=2, sort_keys=True) + "\n"


def read_digests(digest_dir: Path) -> dict[str, str]:
    found: dict[str, str] = {}
    for arch in ("amd64", "arm64"):
        path = digest_dir / f"{arch}.digest"
        if not path.is_file():
            continue
        value = path.read_text(encoding="utf-8").strip()
        if value:
            found[arch] = value
    return found


def write_github_output(plan: dict, path: Path | None) -> None:
    lines = [f"{key}={value}" for key, value in plan.items()]
    text = "\n".join(lines) + "\n"
    sys.stdout.write(text)
    if path is not None:
        path.write_text(text, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ref", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--on-main", choices=("true", "false"), default="false")
    parser.add_argument("--github-output")
    parser.add_argument("--sha", default="")
    parser.add_argument("--digest-dir")
    parser.add_argument("--ledger")
    parser.add_argument("--next-beta-tag", action="store_true")
    parser.add_argument("--existing-tags", default="")
    args = parser.parse_args(argv)

    if args.next_beta_tag:
        existing = {tag for tag in args.existing_tags.split() if tag}
        try:
            tag = next_beta_tag(args.version, existing)
        except ReleaseRefError as exc:
            print(f"release channel rejected: {exc}", file=sys.stderr)
            return 1
        if tag:
            print(tag)
        return 0

    try:
        plan = resolve_release_channel(args.ref, args.version, args.on_main == "true")
        if args.ledger:
            if not args.sha:
                raise ReleaseRefError("a full SHA is required to record a release")
            if plan["channel"] == "skip":
                raise ReleaseRefError(f"{args.ref} is not a release tag")
            digests = read_digests(Path(args.digest_dir or ""))
            Path(args.ledger).write_text(format_ledger(plan, args.sha, digests), encoding="utf-8")
        write_github_output(plan, Path(args.github_output) if args.github_output else None)
    except ReleaseRefError as exc:
        print(f"release channel rejected: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
