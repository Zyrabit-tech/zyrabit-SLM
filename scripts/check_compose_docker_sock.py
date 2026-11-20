#!/usr/bin/env python3
"""Fail if zyrabit-api mounts the raw Docker socket without a socket proxy."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


class ComposeDockerSockError(Exception):
    pass


_SERVICE_HEADER = re.compile(r"^  ([A-Za-z0-9_-]+):\s*$")


def _service_blocks(compose_text: str) -> dict[str, str]:
    lines = compose_text.splitlines()
    blocks: dict[str, list[str]] = {}
    current: str | None = None
    in_services = False

    for line in lines:
        if line.startswith("services:"):
            in_services = True
            current = None
            continue
        if not in_services:
            continue
        if line and not line.startswith(" ") and not line.startswith("\t"):
            # Top-level key after services (networks/volumes)
            break
        match = _SERVICE_HEADER.match(line)
        if match:
            current = match.group(1)
            blocks[current] = []
            continue
        if current is not None:
            blocks[current].append(line)

    return {name: "\n".join(body) for name, body in blocks.items()}


def assert_api_does_not_mount_raw_docker_sock(compose_text: str) -> None:
    blocks = _service_blocks(compose_text)
    if "zyrabit-api" not in blocks:
        raise ComposeDockerSockError("zyrabit-api service is missing from compose")

    api_block = blocks["zyrabit-api"]
    if re.search(r"/var/run/docker\.sock", api_block):
        raise ComposeDockerSockError(
            "zyrabit-api mounts /var/run/docker.sock; use docker-socket-proxy instead"
        )

    if "DOCKER_HOST=tcp://zyrabit-docker-proxy:2375" not in api_block:
        raise ComposeDockerSockError(
            "zyrabit-api must set DOCKER_HOST=tcp://zyrabit-docker-proxy:2375"
        )

    if "zyrabit-docker-proxy" not in blocks:
        raise ComposeDockerSockError("zyrabit-docker-proxy service is missing from compose")

    proxy_block = blocks["zyrabit-docker-proxy"]
    if "/var/run/docker.sock" not in proxy_block:
        raise ComposeDockerSockError(
            "zyrabit-docker-proxy must mount /var/run/docker.sock (read-only)"
        )
    if "CONTAINERS" not in proxy_block:
        raise ComposeDockerSockError(
            "zyrabit-docker-proxy must enable CONTAINERS for read-only diagnostics"
        )


def assert_chroma_not_published(compose_text: str) -> None:
    blocks = _service_blocks(compose_text)
    if "zyrabit-db" not in blocks:
        raise ComposeDockerSockError("zyrabit-db service is missing from compose")

    db_block = blocks["zyrabit-db"]
    # Host publish looks like "8000:8000" under ports; internal expose is fine.
    if re.search(r'ports:\s*\n(?:[ \t]+-.*\n)*[ \t]+-.*8000:8000', db_block):
        raise ComposeDockerSockError(
            "zyrabit-db publishes host port 8000; Chroma must stay internal-only"
        )
    if re.search(r"['\"][^'\"]*8000:8000['\"]", db_block) and "ports:" in db_block:
        raise ComposeDockerSockError(
            "zyrabit-db publishes host port 8000; Chroma must stay internal-only"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--compose", required=True)
    args = parser.parse_args(argv)
    text = Path(args.compose).read_text(encoding="utf-8")
    try:
        assert_api_does_not_mount_raw_docker_sock(text)
        assert_chroma_not_published(text)
    except ComposeDockerSockError as exc:
        print(f"compose docker sock rejected: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
