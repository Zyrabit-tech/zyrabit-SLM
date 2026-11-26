"""Regression tests for provider-aware ``zyra.sh status --json`` / verify (#102, #212)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

FAKE_DOCKER = """#!/usr/bin/env bash
set -euo pipefail
cmd="$1"; shift
target="${@: -1}"
state="$(grep "^${target}=" "${FAKE_DOCKER_STATE}" 2>/dev/null | head -1 | cut -d= -f2- || true)"
ports="$(grep "^${target}:ports=" "${FAKE_DOCKER_STATE}" 2>/dev/null | head -1 | cut -d= -f2- || true)"
health="$(grep "^${target}:health=" "${FAKE_DOCKER_STATE}" 2>/dev/null | head -1 | cut -d= -f2- || true)"
case "${cmd}" in
  compose)
    exit 0
    ;;
  logs)
    exit 0
    ;;
  inspect)
    fmt="$*"
    if [[ "${fmt}" == *"NetworkSettings.Ports"* ]]; then
      if [[ -n "${ports}" ]]; then
        for p in ${ports//,/ }; do printf '%s\\n' "${p}"; done
      fi
      exit 0
    fi
    if [[ -z "${state}" || "${state}" == "not_found" ]]; then
      exit 1
    fi
    if [[ "${fmt}" == *"State.Health"* || "${fmt}" == *".State.Health.Status"* ]]; then
      if [[ -n "${health}" ]]; then
        printf '%s\\n' "${health}"
      else
        printf 'N/A\\n'
      fi
      exit 0
    fi
    # Bare status inspect ({{.State.Status}}) — exit 1 when not running so
    # docker_container_status falls back to not_found.
    if [[ "${state}" != "running" ]]; then
      exit 1
    fi
    printf '%s\\n' "${state}"
    ;;
  *) exit 1 ;;
esac
"""

FAKE_CURL = "#!/usr/bin/env bash\nexit 1\n"

CORE_RUNNING = (
    "zyrabit-api=running\nzyrabit-api:ports=8082\n"
    "zyrabit-web=running\nzyrabit-web:ports=8080\n"
    "zyrabit-db=running\n"
    "zyrabit-mcp=running\n"
)


def _prepare_root(tmp_path: Path, provider: str, docker_state: str) -> tuple[Path, dict[str, str]]:
    root = tmp_path / "root"
    (root / "zyrabit-slm").mkdir(parents=True)
    shutil.copy2(REPO_ROOT / "zyra.sh", root / "zyra.sh")
    shutil.copy2(REPO_ROOT / "VERSION", root / "VERSION")
    (root / "zyrabit-slm" / ".env").write_text(f"INFERENCE_PROVIDER={provider}\n")

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    state_file = tmp_path / "docker-state"
    state_file.write_text(docker_state)
    (bin_dir / "docker").write_text(FAKE_DOCKER)
    (bin_dir / "docker").chmod(0o755)
    (bin_dir / "curl").write_text(FAKE_CURL)
    (bin_dir / "curl").chmod(0o755)

    env = {
        **os.environ,
        "PATH": f"{bin_dir}:{os.environ.get('PATH', '')}",
        "FAKE_DOCKER_STATE": str(state_file),
    }
    return root, env


def _run_status(tmp_path: Path, provider: str, docker_state: str) -> tuple[dict, int]:
    root, env = _prepare_root(tmp_path, provider, docker_state)
    proc = subprocess.run(
        ["bash", str(root / "zyra.sh"), "status", "--json"],
        capture_output=True,
        text=True,
        env=env,
        cwd=root,
        timeout=30,
    )
    assert proc.returncode in (0, 1), proc.stderr
    return json.loads(proc.stdout), proc.returncode


def _run_verify(tmp_path: Path, provider: str, docker_state: str) -> tuple[str, int]:
    root, env = _prepare_root(tmp_path, provider, docker_state)
    env = {
        **env,
        "VERIFY_STARTING_TIMEOUT_SECONDS": "0",
        "VERIFY_DOC_TIMEOUT_SECONDS": "1",
    }
    proc = subprocess.run(
        ["bash", str(root / "zyra.sh"), "verify"],
        capture_output=True,
        text=True,
        env=env,
        cwd=root,
        timeout=30,
    )
    return proc.stdout + proc.stderr, proc.returncode


def test_embedded_metal_requires_full_core_stack(tmp_path: Path) -> None:
    # embedded_metal has no engine container, but api/web/db/mcp must still be up.
    payload, code = _run_status(tmp_path, "embedded_metal", CORE_RUNNING)

    assert payload["platform"]["container"] == "zyrabit-web"
    assert payload["platform"]["status"] == "running"
    assert payload["platform"]["ports"] == [8080]
    assert payload["api"]["status"] == "running"
    assert payload["db"]["status"] == "running"
    assert payload["mcp"]["status"] == "running"
    assert payload["engine"]["status"] == "running"
    assert payload["engine"]["ports"] == []
    assert payload["healthy"] is True
    assert code == 0


def test_web_and_engine_alone_are_not_healthy(tmp_path: Path) -> None:
    # Regression #212: status used to report healthy with only web+engine.
    payload, code = _run_status(
        tmp_path,
        "ollama_docker",
        "zyrabit-web=running\nzyrabit-web:ports=8080\n"
        "zyrabit-engine=running\nzyrabit-engine:ports=11434\n",
    )

    assert payload["platform"]["status"] == "running"
    assert payload["engine"]["status"] == "running"
    assert payload["api"]["status"] == "not_found"
    assert payload["healthy"] is False
    assert code == 1


def test_stopped_containers_stay_not_found_and_unhealthy(tmp_path: Path) -> None:
    payload, code = _run_status(tmp_path, "ollama_docker", "")

    assert payload["platform"]["status"] == "not_found"
    assert payload["platform"]["ports"] == []
    assert payload["api"]["status"] == "not_found"
    assert payload["engine"]["status"] == "not_found"
    assert payload["engine"]["ports"] == []
    assert payload["healthy"] is False
    assert code == 1


def test_cuda_reports_healthy_only_with_full_stack(tmp_path: Path) -> None:
    payload, code = _run_status(
        tmp_path,
        "cuda",
        CORE_RUNNING + "zyrabit-engine=running\nzyrabit-engine:ports=11434\n",
    )
    assert payload["engine"]["status"] == "running"
    assert payload["engine"]["ports"] == [11434]
    assert payload["healthy"] is True
    assert code == 0


def test_cuda_without_engine_container_stays_unhealthy(tmp_path: Path) -> None:
    payload, code = _run_status(tmp_path, "cuda", CORE_RUNNING)
    assert payload["engine"]["status"] == "not_found"
    assert payload["healthy"] is False
    assert code == 1


def test_running_engine_container_reports_its_published_port(tmp_path: Path) -> None:
    payload, code = _run_status(
        tmp_path,
        "ollama_docker",
        CORE_RUNNING + "zyrabit-engine=running\nzyrabit-engine:ports=11434\n",
    )

    assert payload["engine"]["status"] == "running"
    assert payload["engine"]["ports"] == [11434]
    assert payload["healthy"] is True
    assert code == 0


def test_verify_fails_when_health_stuck_starting(tmp_path: Path) -> None:
    out, code = _run_verify(
        tmp_path,
        "ollama_docker",
        CORE_RUNNING
        + "zyrabit-engine=running\nzyrabit-engine:ports=11434\n"
        + "zyrabit-api:health=starting\n",
    )
    assert code == 1
    assert "still starting" in out or "starting" in out
