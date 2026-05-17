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
    import unittest.mock as mock
    FastMCP = mock.MagicMock()

from app.infrastructure.shared.state_tracker import SovereignStateManager
from app.infrastructure.shared.config import DOCS_DIR

logger = logging.getLogger("zyrabit.api")

# Initialize FastMCP Server
mcp = FastMCP("Zyrabit Sovereign Core")

@mcp.tool()
async def import_to_vault(source_path: str, destination_name: str) -> str:
    """
    Securely move an external file into the Zyrabit Vault.
    Validates that the file does not contain executable scripts.
    """
    src = Path(source_path)
    if not src.exists():
        return f"Error: Source file {source_path} not found."

    # SECURITY CHECK: Block executable patterns
    try:
        with open(src, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read(10000) # Check first 10k characters
            
            forbidden_patterns = [
                "#!/bin/", "#!/usr/bin/", "os.system(", "subprocess.run(", 
                "<script>", "eval(", "exec(", "import os"
            ]
            
            for pattern in forbidden_patterns:
                if pattern in content:
                    logger.warning(f"🛡️ Security Block: Executable pattern '{pattern}' detected in {source_path}")
                    return f"Security Alert: File {source_path} contains potentially executable code and was rejected."
    except Exception as e:
        return f"Error during security scan: {e}"

    # Move to Vault
    dest_path = Path(DOCS_DIR) / destination_name
    try:
        shutil.copy2(src, dest_path)
        logger.info(f"📥 Vault: Imported {destination_name} successfully.")
        return f"Success: File imported to Vault as {destination_name}"
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

@mcp.tool()
async def send_telegram_notification(message: str) -> str:
    """
    Sends a secure notification to the user's Telegram.
    Intercepts and masks PII via Gatekeeper before transmission.
    """
    import httpx
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
    """Directly query the sovereign SLM via the secure RAG pipeline."""
    # This will be wired to the global chat use case during app startup
    return "This tool is a bridge to the Zyrabit RAG Engine."

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


# LEGACY SHIMS FOR V1.0 COMPATIBILITY
async def handle_jsonrpc(request_dict: dict) -> dict:
    """Legacy shim for V1.0 compatibility."""
    return {"error": "Use V2.0 MCP Bridge via /mcp/rpc"}

def set_mcp_app_state(state):
    """Legacy shim for V1.0 compatibility."""
    pass

