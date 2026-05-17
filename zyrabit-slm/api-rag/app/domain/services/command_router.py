import logging
from typing import Optional, Dict, Any
from app.infrastructure.shared.state_tracker import SovereignStateManager

logger = logging.getLogger("zyrabit.commands")

class CommandRouter:
    """
    V2.0 Zero-Lag Command Router.
    Intercepts /commands to provide instant responses without LLM inference.
    """
    
    @staticmethod
    async def handle(text: str, source: str = "WEB", session_id: str = "default") -> Optional[Dict[str, Any]]:
        if not text.startswith("/"):
            return None

        cmd = text.split()[0].lower()
        logger.info(f"⚡ Intercepting command: {cmd} from {source}")

        if cmd == "/stats":
            stats = SovereignStateManager.get_stats()
            response = f"""### 🏛️ Sovereign Infrastructure Stats
- **Vault Files**: {stats['vault_files']}
- **Total Tokens Indexed**: {stats['total_tokens']:,}
- **Conversation History**: {stats['total_messages']} messages
- **Sovereign DB**: `{stats['db_path']}`
- **Source Channel**: {source}
- **Latency**: ⚡ < 15ms (Intercepted)
"""
            return {
                "response": response,
                "metadata": {"decision": "command_intercept", "command": "/stats"}
            }

        if cmd == "/vault":
            parts = text.split()
            sub = parts[1].lower() if len(parts) > 1 else ""
            
            if sub == "sync":
                from app.main import _global_app
                from app.domain.services.obsidian_service import ObsidianService
                ingest_use_case = _global_app.state.ingest_use_case
                stats = await ObsidianService.sync_vault(ingest_use_case)
                response = f"""### 🔄 Obsidian Vault Sync Complete
- **Notes Scanned**: {stats['scanned']}
- **New/Modified Notes Indexed**: {stats['indexed']}
- **Skipped (Up to date)**: {stats['skipped']}
- **Errors**: {stats['errors']}
- **Status**: 🟢 Knowledge Base updated successfully!
"""
                return {
                    "response": response,
                    "metadata": {"decision": "command_intercept", "command": "/vault sync"}
                }
                
            if sub == "reflect":
                from app.main import _global_app
                from app.domain.services.obsidian_service import ObsidianService
                inference_provider = _global_app.state.inference_provider
                result = await ObsidianService.generate_reflective_note(session_id, inference_provider)
                return {
                    "response": f"### 🧠 AutoLearner Reflection\n\n{result}",
                    "metadata": {"decision": "command_intercept", "command": "/vault reflect"}
                }

            return {
                "response": "📂 Opening Sovereign Vault management...",
                "metadata": {"decision": "command_intercept", "command": "/vault", "action": "ui_open_vault"}
            }


        if cmd == "/clear":
            SovereignStateManager.clear_session(session_id)
            return {
                "response": "🧹 Memory cleared. Zyra is ready for a fresh session.",
                "metadata": {"decision": "command_intercept", "command": "/clear"}
            }

        if cmd == "/tools":
            # This will be more dynamic in Phase 4
            return {
                "response": "🟢 Active Tools:\n- import_to_vault\n- send_telegram_notification\n- vault_stats\n- search_rag",
                "metadata": {"decision": "command_intercept", "command": "/tools"}
            }

        return {
            "response": f"❌ Unknown command: {cmd}. Type /tools for a list of available commands.",
            "metadata": {"decision": "command_intercept", "error": "unknown_command"}
        }
