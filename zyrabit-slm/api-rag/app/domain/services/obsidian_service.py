import os
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
from app.infrastructure.shared.state_tracker import SovereignStateManager
from app.infrastructure.shared.config import DOCS_DIR

logger = logging.getLogger("zyrabit.obsidian")

class ObsidianService:
    """
    V2.0 Obsidian Sovereign Brain Sync & AutoLearner Service.
    Automatically indexes Obsidian vaults and generates structured Reflective Notes.
    """
    VAULT_PATH = Path(os.getenv("OBSIDIAN_VAULT_PATH", f"{DOCS_DIR}/obsidian"))

    @classmethod
    def init_vault(cls):
        """Ensure the Obsidian Vault directory structure exists."""
        cls.VAULT_PATH.mkdir(parents=True, exist_ok=True)
        # Create reflective subfolder
        (cls.VAULT_PATH / "Reflective Notes").mkdir(parents=True, exist_ok=True)
        logger.info(f"📂 Obsidian Vault initialized at: {cls.VAULT_PATH}")

    @classmethod
    async def sync_vault(cls, ingest_use_case) -> Dict[str, Any]:
        """
        Scans all Markdown files in the vault and indexes new or changed files into Hybrid RAG (FTS5 + Vector).
        """
        cls.init_vault()
        scanned = 0
        indexed = 0
        skipped = 0
        errors = 0

        logger.info(f"🔄 Scanning Obsidian Vault: {cls.VAULT_PATH}...")
        
        # Recursively search for markdown files
        for md_file in cls.VAULT_PATH.rglob("*.md"):
            # Skip Reflective Notes folder to avoid circular indexing loops
            if "Reflective Notes" in md_file.parts:
                continue
                
            scanned += 1
            file_str = str(md_file)
            
            try:
                # Check hashing to avoid redundant indexing
                if SovereignStateManager.needs_reindexing(file_str):
                    logger.info(f"📥 Obsidian Sync: Ingesting changed note -> {md_file.name}")
                    res = await ingest_use_case.execute(file_str, domain="obsidian")
                    if res.get("status") == "success":
                        indexed += 1
                    else:
                        errors += 1
                else:
                    skipped += 1
            except Exception as e:
                logger.error(f"❌ Failed to sync Obsidian note {md_file.name}: {e}")
                errors += 1

        logger.info(f"✅ Obsidian Sync Complete: Scanned {scanned}, Indexed {indexed}, Skipped {skipped}, Errors {errors}")
        return {
            "scanned": scanned,
            "indexed": indexed,
            "skipped": skipped,
            "errors": errors
        }

    @classmethod
    async def generate_reflective_note(cls, session_id: str, inference_provider) -> str:
        """
        Gathers conversation history, uses the LLM to summarize key insights,
        and saves a clean, Obsidian-compatible reflective note to the vault.
        """
        cls.init_vault()
        
        # 1. Fetch History from Sovereign State
        history = SovereignStateManager.get_history(session_id)
        if not history:
            return "No conversation history found for this session."

        # Format history for LLM
        formatted_chat = []
        for msg in history:
            role = "User" if msg["role"] == "user" else "Assistant"
            formatted_chat.append(f"{role}: {msg['content']}")
        chat_str = "\n".join(formatted_chat)

        # Get User Profile to personalize the note metadata
        profile = SovereignStateManager.get_user_profile()
        user_name = profile.get("name", "Abraham Gomez")
        assistant_name = profile.get("assistant_name", "Zyra")

        # 2. Build Synthesis Prompt
        synthesis_prompt = f"""You are the Reflective Memory system of {assistant_name}.
Your job is to synthesize the following conversation with {user_name} into a structured Markdown note for their personal Obsidian vault.

Be insightful, highlight key decisions, technological discoveries, concepts discussed, and extract next actionable steps.
Ensure you use Obsidian tags and standard frontmatter.

### CONVERSATION MEMORY:
{chat_str}

### INSTRUCTIONS:
Create a beautiful, highly structured Markdown note in Spanish.
Include:
1. Frontmatter (tags: [zyrabit, auto-learning, reflexiones], date, session_id)
2. Executive Summary (Resumen Ejecutivo)
3. Key Technical Decisions (Decisiones Técnicas Clave)
4. Knowledge Graph Connections (Conceptos clave con enlaces [[Obsidian]])
5. Action Items (Próximos Pasos en formato - [ ] )
"""

        # 3. Request LLM Inference
        from app.domain.entities.inference import InferenceRequest
        try:
            req = InferenceRequest(
                model=profile.get("preferred_model", "qwen2.5:7b"),
                prompt=synthesis_prompt,
                system_prompt="You are a precise, reflective AI writing system."
            )
            response = inference_provider.generate(req)
            note_content = response.text
        except Exception as e:
            logger.error(f"❌ LLM Synthesis failed: {e}. Generating fallback markdown.")
            # Fallback template if inference fails
            note_content = f"""---
tags: [zyrabit, auto-learning, fallback]
date: {datetime.now().strftime('%Y-%m-%d')}
session: {session_id}
---
# Reflexión de Sesión (Fallback)
- **Usuario**: {user_name}
- **Asistente**: {assistant_name}

La síntesis mediante IA falló, pero la memoria de la conversación se mantiene intacta en SQLite.
"""

        # 4. Save to Vault under "Reflective Notes"
        date_str = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        note_name = f"reflective_{session_id}_{date_str}.md"
        note_path = cls.VAULT_PATH / "Reflective Notes" / note_name
        
        try:
            with open(note_path, "w", encoding="utf-8") as f:
                f.write(note_content)
            logger.info(f"🧠 Reflective Memory Note saved to: {note_path}")
            return f"Reflective Note successfully created: [[Reflective Notes/{note_name[:-3]}]]"
        except Exception as e:
            logger.error(f"❌ Failed to save Reflective Note: {e}")
            return f"Error saving reflective note to vault: {e}"

    @classmethod
    async def start_auto_learner_loop(cls, inference_provider, interval_seconds: int = 600):
        """Periodically scans active sessions and writes reflective notes."""
        logger.info("🧠 AutoLearner Background Service active.")
        import asyncio
        import sqlite3
        while True:
            await asyncio.sleep(interval_seconds)
            try:
                # Find all distinct sessions that have conversation history
                with sqlite3.connect(SovereignStateManager.DB_PATH) as conn:
                    cursor = conn.execute("SELECT DISTINCT session_id FROM conversation_memory")
                    sessions = [row[0] for row in cursor.fetchall() if row[0] != "default"]
                
                for sid in sessions:
                    logger.info(f"🧠 AutoLearner: Synthesizing memory for session {sid}...")
                    await cls.generate_reflective_note(sid, inference_provider)
            except Exception as e:
                logger.error(f"⚠️ AutoLearner background task error: {e}")

