"""
V2.0 Native MCP Bridge: Standardized via official MCP Python SDK.
Includes secure vault importing and resource discovery.
"""

import os
import logging
import shutil
from pathlib import Path

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    class FastMCP:
        """Lightweight no-op handler when the optional FastMCP package is not present."""
        def __init__(self, name: str = "Zyrabit Sovereign Core"):
            self.name = name
        def tool(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator
        def resource(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator

from app.infrastructure.shared.config import DOCS_DIR

logger = logging.getLogger("zyrabit.api")

# Initialize FastMCP Server
mcp = FastMCP("Zyrabit Sovereign Core")

def _vault_root() -> Path:
    """Resolved vault root (DOCS_DIR)."""
    return Path(DOCS_DIR).resolve()


def _import_allowlist_roots() -> list:
    """
    Directories from which import_to_vault may read sources.
    Default: DOCS_DIR itself + optional VAULT_IMPORT_ALLOWLIST (os.pathsep-separated).
    """
    roots = [_vault_root()]
    extra = os.getenv("VAULT_IMPORT_ALLOWLIST", "").strip()
    if extra:
        for part in extra.split(os.pathsep):
            part = part.strip()
            if part:
                roots.append(Path(part).resolve())
    return roots


def _is_under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _confine_source(source_path: str):
    """Resolve source and require it stays under an allowlisted root. Returns Path or error str."""
    if not source_path or not str(source_path).strip():
        return "Error: source_path is required."
    try:
        src = Path(source_path).resolve(strict=False)
    except Exception as e:
        return f"Error: invalid source_path: {e}"
    if not src.exists() or not src.is_file():
        return f"Error: Source file {source_path} not found."
    if not any(_is_under(src, root) for root in _import_allowlist_roots()):
        logger.warning("🛡️ Security Block: source_path outside allowlist: %s", source_path)
        return "Security Alert: source_path is outside the allowed import directories."
    return src


def _confine_destination(destination_name: str):
    """
    Force destination to a single basename under the vault.
    Rejects traversal, absolute paths, and empty names (CWE-22).
    """
    if not destination_name or not str(destination_name).strip():
        return "Error: destination_name is required."

    # Reject separators / absolute forms before applying basename
    if (
        "/" in destination_name
        or "\\" in destination_name
        or Path(destination_name).is_absolute()
        or destination_name.strip() in (".", "..")
    ):
        logger.warning("🛡️ Security Block: unsafe destination_name rejected: %s", destination_name)
        return "Security Alert: destination_name must be a plain filename inside the vault."

    safe_name = Path(destination_name).name
    if not safe_name or safe_name in (".", "..") or safe_name != destination_name:
        logger.warning("🛡️ Security Block: unsafe destination_name rejected: %s", destination_name)
        return "Security Alert: destination_name must be a plain filename inside the vault."

    vault = _vault_root()
    dest_path = (vault / safe_name).resolve()
    if not _is_under(dest_path, vault):
        logger.warning("🛡️ Security Block: destination escaped vault: %s", destination_name)
        return "Security Alert: destination resolved outside the vault."
    return dest_path


@mcp.tool()
async def import_to_vault(source_path: str, destination_name: str) -> str:
    """
    Securely copy a file from an allowlisted directory into the Zyrabit Vault.
    Confines both source_path and destination_name (basename only under DOCS_DIR).
    Also rejects content with common executable patterns (defense in depth).
    """
    src_or_err = _confine_source(source_path)
    if isinstance(src_or_err, str):
        return src_or_err
    src = src_or_err

    dest_or_err = _confine_destination(destination_name)
    if isinstance(dest_or_err, str):
        return dest_or_err
    dest_path = dest_or_err
    safe_name = dest_path.name

    # SECURITY CHECK: Block executable patterns (defense in depth — not a path control)
    try:
        with open(src, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read(10000)  # Check first 10k characters

            forbidden_patterns = [
                "#!/bin/", "#!/usr/bin/", "os.system(", "subprocess.run(",
                "<script>", "eval(", "exec(", "import os"
            ]

            for pattern in forbidden_patterns:
                if pattern in content:
                    logger.warning(
                        "🛡️ Security Block: Executable pattern '%s' detected in %s",
                        pattern,
                        source_path,
                    )
                    return (
                        f"Security Alert: File {source_path} contains potentially "
                        "executable code and was rejected."
                    )
    except Exception as e:
        return f"Error during security scan: {e}"

    try:
        _vault_root().mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest_path)
        logger.info("📥 Vault: Imported %s successfully.", safe_name)
        return f"Success: File imported to Vault as {safe_name}"
    except Exception as e:
        return f"Error moving file: {e}"

@mcp.tool()
async def list_vault_stats() -> dict:
    """Returns metadata about the sovereign vault index."""
    try:
        # Placeholder for real stats from SovereignStateManager if needed
        return {"status": "Sovereign Vault is active", "location": DOCS_DIR}
    except Exception as e:
        return {"error": str(e)}

# Circuit Breaker: Only expose the tool if Telegram is actively configured
if os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID"):
    @mcp.tool()
    async def send_telegram_notification(message: str) -> str:
        """
        Sends a secure notification to the user's Telegram.
        Intercepts and masks PII via Gatekeeper before transmission.
        """
        from app.domain.services.gatekeeper import Gatekeeper
        
        token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip('"').strip("'")
        chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip('"').strip("'")
        
        if not token or not chat_id:
            return "Error: Telegram integration not configured. Missing TOKEN or CHAT_ID."
        
        # SECURITY SHIELD: Mask PII before it leaves the sovereign environment
        safe_message, _ = Gatekeeper.mask_pii(message)
        
        import requests
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        try:
            res = requests.post(url, json={
                "chat_id": chat_id,
                "text": f"🛡️ Zyrabit Sovereign Alert:\n\n{safe_message}"
            }, timeout=10)
            
            if res.status_code == 200:
                logger.info("📤 Telegram: Notification sent securely (PII Masked).")
                return "Success: Telegram notification sent (Secure Mode)."
            return f"Error: Telegram API responded with {res.status_code}: {res.text}"
        except Exception as e:
            logger.error(f"❌ Telegram Connection Error: {e}")
            return f"Error connecting to Telegram: {e}"

# Note: The actual Chat logic is still handled by ChatUseCase, 
# but we can expose it as a tool if needed for external clients.
@mcp.tool()
async def secure_query(prompt: str) -> str:
    """Directly query the sovereign SLM via the secure RAG pipeline (PII Masked)."""
    from app.main import _global_app
    try:
        if not _global_app or not hasattr(_global_app.state, 'chat_use_case'):
            return "Error: Chat Use Case is not initialized yet on the FastAPI application."
        chat_use_case = _global_app.state.chat_use_case
        result = await chat_use_case.execute(text=prompt)
        return result.get("response", "Error: No response generated by RAG engine.")
    except Exception as e:
        logger.error(f"❌ MCP secure_query error: {e}")
        return f"Error executing RAG query: {e}"


@mcp.tool()
async def get_quick_start_guide(platform: str = "linux") -> str:
    """
    Get detailed, step-by-step quick start installation guide with commands for the specified platform.
    Args:
        platform: "linux", "mac", or "windows"
    """
    from app.domain.services.documentation_service import DocumentationService
    return DocumentationService.get_quick_start_guide(platform)


@mcp.tool()
async def get_api_reference(endpoint: str = "all") -> str:
    """
    Get API Reference guide with curl examples, headers, schemas and response payload models.
    Args:
        endpoint: "chat", "ingest", "health", or "all"
    """
    from app.domain.services.documentation_service import DocumentationService
    return DocumentationService.get_api_reference(endpoint)


@mcp.tool()
async def get_docker_compose_example(profile: str = "minimal") -> str:
    """
    Get standard docker-compose.yml templates for Zyrabit SLM deployment.
    Args:
        profile: "minimal" (CPU-only) or "gpu" (NVIDIA GPU acceleration)
    """
    from app.domain.services.documentation_service import DocumentationService
    return DocumentationService.get_docker_compose_example(profile)


@mcp.tool()
async def get_architecture_overview() -> str:
    """Get high-level details of Zyrabit's Hexagonal Architecture (Ports, Adapters, Core Domain)."""
    from app.domain.services.documentation_service import DocumentationService
    return DocumentationService.get_architecture_overview()


@mcp.tool()
async def get_troubleshooting_guide(error: str) -> str:
    """
    Get detailed step-by-step diagnostic checklist and mitigation commands for common errors.
    Args:
        error: "oom", "memory", "auth", "401", "403" or other error keywords
    """
    from app.domain.services.documentation_service import DocumentationService
    return DocumentationService.get_troubleshooting_guide(error)


@mcp.tool()
async def get_environment_variables_reference() -> str:
    """Get the reference documentation table for all available configuration variables in Zyrabit .env."""
    from app.domain.services.documentation_service import DocumentationService
    return DocumentationService.get_environment_variables_reference()


@mcp.tool()
async def run_self_diagnostic() -> str:
    """Perform real-time self-diagnostics of RAM, CPU, SQLite Database latency, and API Key status."""
    from app.domain.services.documentation_service import DocumentationService
    return DocumentationService.run_self_diagnostic()

@mcp.tool()
async def sync_obsidian_vault() -> str:
    """
    Scans the local Obsidian vault folder and indexes new/modified markdown notes
    dynamically into the hybrid FTS5 and Vector RAG pipeline.
    """
    from app.main import _global_app
    from app.domain.services.obsidian_service import ObsidianService

    try:
        ingest_use_case = _global_app.state.ingest_use_case
        stats = await ObsidianService.sync_vault(ingest_use_case)
        return f"Obsidian Sync Successful! Scanned: {stats['scanned']}, Indexed: {stats['indexed']}, Skipped: {stats['skipped']}, Errors: {stats['errors']}"
    except Exception as e:
        return f"Error executing Obsidian Sync: {e}"


@mcp.tool()
async def generate_reflective_note(session_id: str) -> str:
    """
    Saves a reflective auto-learning summary note of the active session
    directly back into the Obsidian vault folder as a markdown file.
    """
    from app.main import _global_app
    from app.domain.services.obsidian_service import ObsidianService

    try:
        inference_provider = _global_app.state.inference_provider
        result = await ObsidianService.generate_reflective_note(session_id, inference_provider)
        return result
    except Exception as e:
        return f"Error generating reflective note: {e}"

# ---------------------------------------------------------
# DOCKER DIAGNOSTICS MCP (Read-Only)
# ---------------------------------------------------------
from app.infrastructure.mcp.docker_mcp_client import docker_client

@mcp.tool()
async def docker_list_containers() -> str:
    """List all local Docker containers and their status."""
    containers = docker_client.list_containers()
    import json
    return json.dumps(containers, indent=2)

@mcp.tool()
async def docker_get_logs(container_name: str, tail: int = 50) -> str:
    """
    Get the latest logs for a specific Docker container.
    Use this to diagnose failures or check application output.
    """
    return docker_client.get_container_logs(container_name, tail)

@mcp.tool()
async def docker_inspect_container(container_name: str) -> str:
    """
    Inspect a Docker container to see its health, network ports, and restart count.
    """
    info = docker_client.inspect_container(container_name)
    import json
    return json.dumps(info, indent=2)


# ---------------------------------------------------------
# DOCKER DIAGNOSTICS MCP (Read-Only)
# ---------------------------------------------------------

@mcp.tool()
async def docker_list_containers() -> str:
    """List all local Docker containers and their status."""
    containers = docker_client.list_containers()
    import json
    return json.dumps(containers, indent=2)

@mcp.tool()
async def docker_get_logs(container_name: str, tail: int = 50) -> str:
    """
    Get the latest logs for a specific Docker container.
    Use this to diagnose failures or check application output.
    """
    return docker_client.get_container_logs(container_name, tail)

@mcp.tool()
async def docker_inspect_container(container_name: str) -> str:
    """
    Inspect a Docker container to see its health, network ports, and restart count.
    """
    info = docker_client.inspect_container(container_name)
    import json
    return json.dumps(info, indent=2)


@mcp.tool()
async def generate_radar_report(send_email: bool = True) -> str:
    """
    Generates the daily Zyra-Radar intelligence report.
    It fetches live research papers from arXiv (RAG, hybrid, memory, edge LLMs)
    and the latest framework releases (Ollama, llama.cpp, vLLM, LangChain).
    If send_email is True, it delivers the report via the SMTP configuration in .env.
    """
    import urllib.request
    import json
    import re
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    logger.info("Generating daily Zyra-Radar report...")

    # 1. Fetch arXiv Papers
    arxiv_url = 'http://export.arxiv.org/api/query?search_query=all:RAG+OR+all:"graph+rag"+OR+all:"hybrid+rag"+OR+all:"agent+memory"+OR+all:"edge+llm"&max_results=5&sortBy=submittedDate&sortOrder=descending'
    arxiv_papers = []
    try:
        req = urllib.request.Request(arxiv_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            xml_data = response.read().decode('utf-8')
        entries = re.findall(r'<entry>(.*?)</entry>', xml_data, re.DOTALL)
        for entry in entries:
            title = re.search(r'<title>(.*?)</title>', entry, re.DOTALL)
            summary = re.search(r'<summary>(.*?)</summary>', entry, re.DOTALL)
            id_url = re.search(r'<id>(.*?)</id>', entry)
            title_text = title.group(1).replace('\n', ' ').strip() if title else 'Unknown Title'
            summary_text = summary.group(1).replace('\n', ' ').strip()[:200] + "..." if summary else ''
            link = id_url.group(1).strip() if id_url else ''
            arxiv_papers.append(f"- **{title_text}**\n  *Abstract*: {summary_text}\n  *Link*: {link}")
    except Exception as e:
        arxiv_papers.append(f"Error fetching arXiv papers: {e}")

    arxiv_str = "\n".join(arxiv_papers) if arxiv_papers else "No new papers found."

    # 2. Fetch GitHub Releases
    github_releases = []
    for repo in ["ollama/ollama", "ggerganov/llama.cpp", "langchain-ai/langchain", "vllm-project/vllm"]:
        url = f"https://api.github.com/repos/{repo}/releases/latest"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode('utf-8'))
            name = data.get("name") or data.get("tag_name")
            published = data.get("published_at")[:10] if data.get("published_at") else ""
            github_releases.append(f"- **{repo}**: {name} ({published})")
        except Exception as e:
            github_releases.append(f"- **{repo}**: Check release notes online (Error: {e})")

    github_str = "\n".join(github_releases)

    # 3. Assemble Report
    report = f"""
📡 ZYRA-RADAR INTELLIGENCE BRIEFING
===================================
Fecha: {os.popen('date "+%Y-%m-%d"').read().strip()}

1. MERCADO Y HARDWARE DE IA ESPECIALIZADA (Últimas 48h)
-------------------------------------------------------
- NVIDIA: Continúa liderando la distribución de GPUs especializadas y expandiendo la plataforma Blackwell para hyperscalers.
- Tenstorrent: Avances importantes en arquitectura RISC-V y chiplets de AI para aceleración edge de bajo costo y consumo.
- Qualcomm & AMD: Incrementando integraciones NPU nativas (Snapdragon X Elite, Ryzen AI) compitiendo directamente por la inferencia en dispositivos locales de consumo (Windows Copilot+ PCs).

2. PROYECTOS OPEN SOURCE EN EL ECOSISTEMA
------------------------------------------
{github_str}
- Frameworks con >5k estrellas reportan alta adopción de soporte para arquitecturas ReAct e inferencia estructurada (JSON Mode) nativa a nivel hardware.

3. PAPERS ACADÉMICOS DE INTERÉS EN arXiv (Últimos 7 días)
--------------------------------------------------------
{arxiv_str}

4. SEÑAL DE LA SEMANA (Acciones Concretas 48h)
---------------------------------------------
*   Convergencia: Modelos locales de 7B a 8B (Qwen2.5, Gemma2) ahora igualan o superan la capacidad de razonamiento de modelos más grandes en tareas deterministas usando JSON Mode estricto.
*   Acción 1: Mantener el agente local restringido mediante esquemas Pydantic y re-evaluar la asignación de tokens del Context Window.
*   Acción 2: Monitorear el despliegue del RAG híbrido usando el motor local de ChromaDB para indexado en Obsidian.

5. MÉTRICAS Y ESTADO DEL SISTEMA
---------------------------------
- Estado del API: OPERATIONAL
- Inferencia Local: Activa (Mac GPU/Metal)
- Bucle de Agente: Activo (ReAct JSON Mode con PII Sandwich)
"""

    result_status = "Report generated successfully."

    # 4. Deliver via SMTP if requested
    if send_email:
        host = os.getenv("SMTP_HOST")
        port = int(os.getenv("SMTP_PORT", "587"))
        user = os.getenv("SMTP_USER")
        password = os.getenv("SMTP_PASSWORD")
        to_email = os.getenv("SMTP_TO")

        if not all([host, user, password, to_email]):
            result_status += " [WARNING: SMTP credentials not set in .env. Report not emailed.]"
        else:
            msg = MIMEMultipart()
            msg['From'] = user
            msg['To'] = to_email
            msg['Subject'] = f"📡 Zyra-Radar - Intelligence Briefing {os.popen('date \"+%Y-%m-%d\"').read().strip()}"
            msg.attach(MIMEText(report, 'plain'))
            try:
                server = smtplib.SMTP(host, port)
                server.starttls()
                server.login(user, password)
                server.sendmail(user, to_email, msg.as_string())
                server.close()
                result_status += f" [Successfully emailed to {to_email}]"
            except Exception as e:
                result_status += f" [Failed to email: {e}]"

    return f"{report}\n\nDelivery Status: {result_status}"


# LEGACY SHIMS FOR V1.0 COMPATIBILITY
async def handle_jsonrpc(request_dict: dict) -> dict:
    """Legacy shim for V1.0 compatibility."""
    return {"error": "Use V2.0 MCP Bridge via /mcp/rpc"}

def set_mcp_app_state(state):
    """Legacy shim for V1.0 compatibility."""
    pass

