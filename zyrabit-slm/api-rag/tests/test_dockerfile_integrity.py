"""
Security and Integrity Guardrail for Project Dockerfiles.

This test suite acts as an automated lock to prevent:
1. Accidental or arbitrary modifications to container build configurations.
2. Performance regressions on GitHub Actions runners (OOM from excessive C++ parallel jobs).
3. Drifting from pinned tool versions (PNPM, UV, Python, Node).
4. Unsafe practices (e.g. apt-get upgrade, running as root).
"""

import hashlib
import json
from pathlib import Path
import pytest


def get_repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").exists() and (parent / "zyrabit-slm").exists():
            return parent
    raise RuntimeError("Failed to locate repository root directory.")


REPO_ROOT = get_repo_root()
LOCK_FILE = REPO_ROOT / "zyrabit-slm" / "dockerfiles.lock.json"


def test_dockerfiles_lock_manifest_exists():
    """Verify that the integrity lock manifest exists in the repository."""
    assert LOCK_FILE.exists(), f"Lock manifest file {LOCK_FILE} does not exist."


def test_dockerfiles_integrity_checksums():
    """
    HASH INTEGRITY LOCK (SHA256):
    If this test fails, a Dockerfile was modified.
    If the modification is intentional and verified, update 'zyrabit-slm/dockerfiles.lock.json'.
    If it was accidental or unapproved, revert with 'git checkout <file>'.
    """
    with open(LOCK_FILE, "r", encoding="utf-8") as f:
        lock_data = json.load(f)

    expected_hashes = lock_data.get("hashes", {})
    assert expected_hashes, "No hashes found in dockerfiles.lock.json"

    for rel_path, expected_hash in expected_hashes.items():
        file_path = REPO_ROOT / rel_path
        assert file_path.exists(), f"Dockerfile not found: {rel_path}"

        content = file_path.read_bytes()
        actual_hash = hashlib.sha256(content).hexdigest()

        error_msg = (
            f"\n🚨 DOCKERFILE INTEGRITY VIOLATION:\n"
            f"File '{rel_path}' has been modified and does not match the blessed hash.\n"
            f"  Expected hash: {expected_hash}\n"
            f"  Actual hash:   {actual_hash}\n\n"
            f"🛠️ ACTION REQUIRED:\n"
            f"1. If this change was NOT intended: run 'git checkout -- {rel_path}' to revert.\n"
            f"2. If this change IS deliberate and approved: update the hash in 'zyrabit-slm/dockerfiles.lock.json'."
        )
        assert actual_hash == expected_hash, error_msg


def test_dockerfiles_invariants_rules():
    """
    MANDATORY BUILD AND SECURITY INVARIANTS:
    Ensures that minimum required engineering standards are enforced across all Dockerfiles.
    """
    with open(LOCK_FILE, "r", encoding="utf-8") as f:
        lock_data = json.load(f)

    rules = lock_data.get("rules", {})
    pnpm_version = rules.get("pnpm_version", "10.34.5")
    cmake_parallel = rules.get("cmake_parallel_level", 2)

    # 1. Verify root Dockerfile and Dockerfile.platform
    for dfile_name in ["Dockerfile", "Dockerfile.platform"]:
        content = (REPO_ROOT / dfile_name).read_text(encoding="utf-8")

        # PNPM rule
        assert f"pnpm@{pnpm_version}" in content, (
            f"{dfile_name}: Must pin stable version pnpm@{pnpm_version}"
        )
        assert "pnpm install --frozen-lockfile" in content, (
            f"{dfile_name}: Must use --frozen-lockfile with pnpm"
        )
        assert "--mount=type=cache,target=/root/.local/share/pnpm/store" in content, (
            f"{dfile_name}: Must use BuildKit cache mount for pnpm store"
        )

        # Python UV & C++ rules
        assert f"CMAKE_BUILD_PARALLEL_LEVEL={cmake_parallel}" in content, (
            f"{dfile_name}: Must limit CMAKE_BUILD_PARALLEL_LEVEL to {cmake_parallel} to prevent CI runner OOM"
        )
        assert "uv sync --frozen --no-dev --no-install-project" in content, (
            f"{dfile_name}: Must sync uv dependencies with --frozen"
        )
        assert "--mount=type=cache,target=/root/.cache/uv" in content, (
            f"{dfile_name}: Must use BuildKit cache mount for uv"
        )

        # Security rules
        assert "USER nonroot" in content, (
            f"{dfile_name}: Must run under nonroot user"
        )
        assert "apt-get upgrade" not in content, (
            f"{dfile_name}: Using 'apt-get upgrade' is prohibited (breaks layer cache and build determinism)"
        )

    # 2. Verify API-RAG Dockerfile
    api_dockerfile = (REPO_ROOT / "zyrabit-slm" / "api-rag" / "Dockerfile").read_text(encoding="utf-8")
    assert f"CMAKE_BUILD_PARALLEL_LEVEL={cmake_parallel}" in api_dockerfile
    assert "uv sync --frozen --no-dev --no-install-project" in api_dockerfile
    assert "USER nonroot" in api_dockerfile
    assert "apt-get upgrade" not in api_dockerfile

    # 3. Verify Web-UI Dockerfile
    web_dockerfile = (REPO_ROOT / "zyrabit-slm" / "web-ui" / "Dockerfile").read_text(encoding="utf-8")
    assert f"pnpm@{pnpm_version}" in web_dockerfile
    assert "pnpm install --frozen-lockfile" in web_dockerfile
    assert "--mount=type=cache,target=/root/.local/share/pnpm/store" in web_dockerfile
