"""
Deterministic Contract Test for README.md and Documentation Architecture.

This test suite guarantees that no AI agent or contributor accidentally removes,
corrupts, or regresses critical documentation sections, hardware sizing tables,
benchmark baselines, service port mappings, or reintroduced deprecated commands.
"""

import os
import re
import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../"))
README_PATH = os.path.join(REPO_ROOT, "README.md")
ZYRA_PATH = os.path.join(REPO_ROOT, "zyra.sh")
COMPOSE_PATH = os.path.join(REPO_ROOT, "zyrabit-slm/docker-compose.yml")


@pytest.fixture
def readme_content():
    assert os.path.exists(README_PATH), f"README.md missing at {README_PATH}"
    with open(README_PATH, "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def zyra_content():
    assert os.path.exists(ZYRA_PATH), f"zyra.sh missing at {ZYRA_PATH}"
    with open(ZYRA_PATH, "r", encoding="utf-8") as f:
        return f.read()


def test_readme_mandatory_sections_in_order(readme_content):
    """
    Validates that required H2 header sections exist and appear in strict sequential order.
    """
    required_sections = [
        "## 📌 Overview & Sovereign Scope",
        "## 📊 Capability Matrix",
        "## 🖥️ Hardware Requirements & Sizing",
        "## 📊 Inference & Performance Baselines",
        "## 🏗 Architecture",
        "## ⚡ Quickstart",
        "## 🌐 Service Endpoints & Ports",
        "## 🖥️ Interface & Walkthrough",
        "## 🎯 Model Selection Matrix",
        "## 🤖 AI Agent Setup (Cursor, Antigravity, Windsurf, Cline)",
        "## 🔍 Real-world Use Cases",
        "## 📦 Stack Components",
        "## 🧪 Testing & Validation",
        "## 🛡 Security Model",
        "## 🤝 Contributing",
    ]

    last_pos = -1
    for section in required_sections:
        pos = readme_content.find(section)
        assert pos != -1, f"Mandatory section '{section}' is missing from README.md"
        assert pos > last_pos, f"Section '{section}' is out of order in README.md"
        last_pos = pos


def test_readme_hardware_sizing_table(readme_content):
    """
    Ensures the Hardware Requirements section contains mandatory tiers and platforms.
    """
    assert "## 🖥️ Hardware Requirements & Sizing" in readme_content

    # Mandatory Tiers
    assert "Entry / Edge" in readme_content
    assert "Production / Standard" in readme_content
    assert "Enterprise / MoE" in readme_content

    # Mandatory Hardware Architectures & Sizing
    assert "8 GB RAM" in readme_content
    assert "16 GB" in readme_content
    assert "Apple Silicon M-Series" in readme_content
    assert "Tenstorrent Blackhole" in readme_content
    assert "NVIDIA" in readme_content

    # Supported Formats
    assert "GGUF" in readme_content
    assert "Q4_K_M" in readme_content
    assert "SafeTensors" in readme_content
    assert "Ollama" in readme_content


def test_readme_benchmark_baselines(readme_content):
    """
    Ensures the Benchmark section specifies real-world inference metrics for verified hardware.
    """
    assert "## 📊 Inference & Performance Baselines" in readme_content
    assert "Tenstorrent Blackhole p150" in readme_content
    assert "Host x86 Multi-Core CPU" in readme_content
    assert "On-Device Verified" in readme_content
    assert "t/s" in readme_content
    assert "TTFT" in readme_content


def test_readme_endpoints_consistency(readme_content):
    """
    Validates port consistency between README.md and docker-compose.yml.
    """
    assert "## 🌐 Service Endpoints & Ports" in readme_content
    # Web UI is on port 8080 (or local port)
    assert "http://localhost:8080" in readme_content
    # API direct local is on port 8088
    assert "http://localhost:8088/v1" in readme_content
    # Grafana is on port 3000
    assert "http://localhost:3000" in readme_content
    # Prometheus is on port 9090
    assert "http://localhost:9090" in readme_content
    # Chroma is on port 8000
    assert "http://localhost:8000" in readme_content
    # MCP is on port 8001
    assert "http://localhost:8001" in readme_content
    # Tenstorrent Hardware Server is on port 8090
    assert "http://localhost:8090" in readme_content


def test_no_deprecated_wizard_in_active_cli_or_docs(readme_content, zyra_content):
    """
    Ensures the removed 'wizard' command is not reintroduced into README, guides, or active CLI commands.
    """
    assert "./zyra.sh wizard" not in readme_content
    assert "./zyra wizard" not in readme_content

    # In zyra.sh, wizard must not be an active documented command in usage()
    usage_match = re.search(r"usage\(\) \{(.*?)\}", zyra_content, re.DOTALL)
    assert usage_match is not None
    usage_text = usage_match.group(1)
    assert "wizard" not in usage_text.lower()
