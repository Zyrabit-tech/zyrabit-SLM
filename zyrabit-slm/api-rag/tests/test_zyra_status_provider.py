"""Regression tests for provider-aware ``zyra.sh status --json`` (#102)."""

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
case "${cmd}" in
  compose)
    exit 0
    ;;
  inspect)
    if [[ "$*" == *"NetworkSettings.Ports"* ]]; then
      if [[ -n "${ports}" ]]; then
        for p in ${ports//,/ }; do printf '%s\\n' "${p}"; done
      fi
      exit 0
    fi
    if [[ "${state}" != "running" ]]; then exit 1; fi
    printf '%s\\n' "${state}"
    ;;
  *) exit 1 ;;
esac
"""

FAKE_CURL = "#!/usr/bin/env bash\nexit 1\n"


def _run_status(tmp_path: Path, provider: str, docker_state: str) -> tuple[dict, int]:
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


def test_embedded_metal_reports_a_running_native_engine(tmp_path: Path) -> None:
    # embedded_metal has no engine container. The platform process serves the
    # engine, so status must not report not_found and must stay healthy.
    payload, code = _run_status(
        tmp_path,
        "embedded_metal",
        "zyrabit-web=running\nzyrabit-web:ports=8080\n",
    )

    assert payload["platform"]["status"] == "running"
    assert payload["platform"]["ports"] == [8080]
    assert payload["engine"]["status"] == "running"
    assert payload["engine"]["ports"] == []
    assert payload["healthy"] is True
    assert code == 0


def test_stopped_containers_stay_not_found_and_unhealthy(tmp_path: Path) -> None:
    # A stopped Docker provider keeps the docker-reported statuses: nothing is
    # inferred as running just because a host service could theoretically exist.
    payload, code = _run_status(tmp_path, "ollama_docker", "")

    assert payload["platform"]["status"] == "not_found"
    assert payload["platform"]["ports"] == []
    assert payload["engine"]["status"] == "not_found"
    assert payload["engine"]["ports"] == []
    assert payload["healthy"] is False
    assert code == 1


def test_running_engine_container_reports_its_published_port(tmp_path: Path) -> None:
    payload, code = _run_status(
        tmp_path,
        "ollama_docker",
        "zyrabit-web=running\nzyrabit-web:ports=8080\n"
        "zyrabit-engine=running\nzyrabit-engine:ports=11434\n",
    )

    assert payload["engine"]["status"] == "running"
    assert payload["engine"]["ports"] == [11434]
    assert payload["healthy"] is True
    assert code == 0
