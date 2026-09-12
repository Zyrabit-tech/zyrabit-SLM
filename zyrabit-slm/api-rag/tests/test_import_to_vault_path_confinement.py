"""Regression tests for GHSA-r4q8-hjfc-ggp2 (CWE-22) import_to_vault confinement."""
from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest


@pytest.fixture()
def vault_env(tmp_path, monkeypatch):
    vault = tmp_path / "vault"
    staging = tmp_path / "staging"
    vault.mkdir()
    staging.mkdir()
    monkeypatch.setenv("DOCS_DIR", str(vault))
    monkeypatch.setenv("VAULT_IMPORT_ALLOWLIST", str(staging))
    # Reload config + mcp_service with new env
    import importlib
    import app.infrastructure.shared.config as config
    importlib.reload(config)
    import app.domain.services.mcp_service as mcp_service
    importlib.reload(mcp_service)
    return vault, staging, mcp_service


def _run(coro):
    return asyncio.run(coro)


def test_rejects_relative_traversal_destination(vault_env):
    vault, staging, mcp_service = vault_env
    src = staging / "ok.txt"
    src.write_text("hello vault")
    result = _run(mcp_service.import_to_vault(str(src), "../../../../tmp/PWNED_relative"))
    assert "Security Alert" in result
    # Nothing written outside vault
    outside = vault.parent / "PWNED_relative"
    assert not outside.exists()
    assert list(vault.iterdir()) == []


def test_rejects_absolute_destination(vault_env, tmp_path):
    vault, staging, mcp_service = vault_env
    src = staging / "ok.txt"
    src.write_text("hello vault")
    abs_target = str(tmp_path / "PWNED_absolute")
    result = _run(mcp_service.import_to_vault(str(src), abs_target))
    assert "Security Alert" in result
    assert not Path(abs_target).exists()


def test_rejects_source_outside_allowlist(vault_env, tmp_path):
    vault, staging, mcp_service = vault_env
    secret = tmp_path / "secret.env"
    secret.write_text("TOKEN=supersecret")
    result = _run(mcp_service.import_to_vault(str(secret), "leaked.md"))
    assert "Security Alert" in result
    assert not (vault / "leaked.md").exists()


def test_allows_safe_basename_from_allowlist(vault_env):
    vault, staging, mcp_service = vault_env
    src = staging / "note.txt"
    src.write_text("safe content for vault")
    result = _run(mcp_service.import_to_vault(str(src), "note.txt"))
    assert result.startswith("Success:")
    assert (vault / "note.txt").read_text() == "safe content for vault"


def test_confine_destination_helpers(vault_env):
    _, _, mcp_service = vault_env
    assert isinstance(mcp_service._confine_destination("../x"), str)
    assert isinstance(mcp_service._confine_destination("/tmp/x"), str)
    assert isinstance(mcp_service._confine_destination("good.md"), Path)
