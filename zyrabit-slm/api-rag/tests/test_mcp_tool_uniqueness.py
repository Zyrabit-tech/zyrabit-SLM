"""Regression: MCP docker_* tools must register once; PDF code uses pymupdf."""

from __future__ import annotations

import ast
import re
from collections import Counter
from pathlib import Path

API_RAG = Path(__file__).resolve().parents[1]
MCP_SERVICE = API_RAG / "app" / "domain" / "services" / "mcp_service.py"
PDF_SOURCES = (
    API_RAG / "app" / "node" / "parsers.py",
    API_RAG / "app" / "infrastructure" / "persistence" / "pdf_processor.py",
)
DOCKER_TOOLS = (
    "docker_list_containers",
    "docker_get_logs",
    "docker_inspect_container",
)


def _async_function_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return [
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]


def test_docker_mcp_tools_defined_once():
    names = [name for name in _async_function_names(MCP_SERVICE) if name in DOCKER_TOOLS]
    counts = Counter(names)
    assert counts == Counter({name: 1 for name in DOCKER_TOOLS}), (
        f"Expected each docker_* MCP tool once, got {dict(counts)}"
    )


def test_mcp_module_tool_names_are_unique():
    """Importing mcp_service must not re-register duplicate FastMCP tool names."""
    from app.domain.services import mcp_service

    manager = getattr(mcp_service.mcp, "_tool_manager", None)
    if manager is None:
        # Lightweight FastMCP stub used when the package is absent — uniqueness
        # is still enforced by the AST check above.
        return

    tools = getattr(manager, "_tools", None) or getattr(manager, "tools", None)
    if tools is None:
        listed = manager.list_tools() if hasattr(manager, "list_tools") else []
        names = [getattr(t, "name", t) for t in listed]
    else:
        names = list(tools.keys()) if isinstance(tools, dict) else [
            getattr(t, "name", str(t)) for t in tools
        ]

    for tool_name in DOCKER_TOOLS:
        assert names.count(tool_name) == 1, (
            f"Tool {tool_name!r} registered {names.count(tool_name)} times: {names}"
        )
    assert len(names) == len(set(names)), f"Duplicate MCP tool names: {names}"


def test_pdf_modules_import_pymupdf_as_fitz():
    bare_fitz = re.compile(r"(?m)^\s*import\s+fitz\s*(?:#.*)?$")
    pymupdf_alias = re.compile(r"(?m)^\s*import\s+pymupdf\s+as\s+fitz\s*(?:#.*)?$")

    for path in PDF_SOURCES:
        source = path.read_text(encoding="utf-8")
        assert not bare_fitz.search(source), (
            f"{path} still uses deprecated bare `import fitz`"
        )
        assert pymupdf_alias.search(source), (
            f"{path} must use `import pymupdf as fitz`"
        )
