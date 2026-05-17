import os
import sqlite3
import logging
import hashlib
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("zyrabit.api")

class SovereignStateManager:
    """
    V2.0 Sovereign State: Manages Vault Indexing (Hashing) and Conversation Memory.
    Uses SQLite WAL mode for high-concurrency async environments.
    """
    DB_PATH = os.getenv("DB_PATH", "/app/db_data/sovereign_state.db")

    @classmethod
    def init_db(cls, db_path: str | None = None):
        if db_path:
            cls.DB_PATH = db_path
        
        # Ensure directory exists
        Path(cls.DB_PATH).parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(cls.DB_PATH) as conn:
            # ACTIVATE WAL MODE for FastAPI concurrency
            conn.execute("PRAGMA journal_mode=WAL;")
            
            # 1. Vault Index (Obsidian Sync)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS vault_index (
                    file_path TEXT PRIMARY KEY,
                    file_hash TEXT,
                    token_count INTEGER,
                    last_indexed TIMESTAMP
                )
            """)

            # 2. Conversation Memory (Shadow Context)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversation_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    role TEXT,
                    content TEXT,
                    timestamp TIMESTAMP
                )
            """)

            # 3. User Profile (Onboarding & Persona)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_profile (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    email TEXT,
                    role TEXT,
                    interests TEXT,
                    persona TEXT DEFAULT 'general',
                    preferred_model TEXT DEFAULT 'qwen2.5:7b',
                    tone TEXT DEFAULT 'professional',
                    onboarding_completed INTEGER DEFAULT 0
                )
            """)
            
            # Migration: Add assistant_name if missing
            try:
                conn.execute("ALTER TABLE user_profile ADD COLUMN assistant_name TEXT DEFAULT 'Zyra'")
            except sqlite3.OperationalError:
                pass # Column exists

            # 4. FTS5 Virtual Table for Zero-Lag Hybrid RAG
            try:
                conn.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS fts_vault USING fts5(
                        file_path,
                        content,
                        tokenize='porter'
                    )
                """)
            except sqlite3.OperationalError as e:
                logger.warning(f"⚠️ FTS5 might not be supported on this SQLite version: {e}")

            logger.info(f"🏛️ Sovereign DB Initialized at {cls.DB_PATH} [WAL Mode Active]")


    @classmethod
    def get_user_profile(cls) -> dict:

        with sqlite3.connect(cls.DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM user_profile WHERE id = 1")
            row = cursor.fetchone()
            if row:
                return dict(row)
            return {}

    @classmethod
    def update_user_profile(cls, name: str, role: str, interests: str, email: str = "contact@zyrabit.com", persona: str = 'general', preferred_model: str = 'qwen2.5:7b', tone: str = 'professional', assistant_name: str = 'Zyra'):
        with sqlite3.connect(cls.DB_PATH) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO user_profile (id, name, email, role, interests, persona, preferred_model, tone, assistant_name, onboarding_completed)
                VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (name, email, role, interests, persona, preferred_model, tone, assistant_name))




    @classmethod
    def get_file_hash(cls, file_path: str) -> str:
        """Calculate SHA-256 hash of a file."""
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.error(f"Error hashing file {file_path}: {e}")
            return ""

    @classmethod
    def needs_reindexing(cls, file_path: str) -> bool:
        """Check if file hash has changed since last indexing."""
        current_hash = cls.get_file_hash(file_path)
        if not current_hash: return False

        with sqlite3.connect(cls.DB_PATH) as conn:
            cursor = conn.execute("SELECT file_hash FROM vault_index WHERE file_path = ?", (file_path,))
            row = cursor.fetchone()
            if row and row[0] == current_hash:
                return False
        return True

    @classmethod
    def update_vault_index(cls, file_path: str, token_count: int, full_text_content: str = ""):
        current_hash = cls.get_file_hash(file_path)
        with sqlite3.connect(cls.DB_PATH) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO vault_index (file_path, file_hash, token_count, last_indexed)
                VALUES (?, ?, ?, ?)
            """, (file_path, current_hash, token_count, datetime.now().isoformat()))
            
            # Sync to FTS5 for ultra-fast retrieval
            if full_text_content:
                conn.execute("DELETE FROM fts_vault WHERE file_path = ?", (file_path,))
                conn.execute("""
                    INSERT INTO fts_vault (file_path, content)
                    VALUES (?, ?)
                """, (file_path, full_text_content))

    @classmethod
    def search_fts(cls, query: str, limit: int = 3) -> list:
        """Zero-Lag Keyword Search using FTS5."""
        try:
            with sqlite3.connect(cls.DB_PATH) as conn:
                conn.row_factory = sqlite3.Row
                # Escape query to prevent FTS syntax errors (basic protection)
                safe_query = query.replace('"', '""').replace("'", "''")
                # FTS requires exact match or wildcard, we use OR strategy
                tokens = safe_query.split()
                fts_query = " OR ".join(f"{t}*" for t in tokens if len(t) > 2)
                
                if not fts_query:
                    return []
                    
                cursor = conn.execute(f"""
                    SELECT file_path, snippet(fts_vault, 1, '<b>', '</b>', '...', 64) as snippet, rank 
                    FROM fts_vault 
                    WHERE fts_vault MATCH ? 
                    ORDER BY rank LIMIT ?
                """, (fts_query, limit))
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.OperationalError as e:
            logger.warning(f"⚠️ FTS Search failed: {e}")
            return []


    @classmethod
    def store_message(cls, session_id: str, role: str, content: str):
        with sqlite3.connect(cls.DB_PATH) as conn:
            conn.execute("""
                INSERT INTO conversation_memory (session_id, role, content, timestamp)
                VALUES (?, ?, ?, ?)
            """, (session_id, role, content, datetime.now().isoformat()))

            
            # FIFO: Clean old messages (keep last 50 per session for safety)
            conn.execute("""
                DELETE FROM conversation_memory 
                WHERE session_id = ? AND id NOT IN (
                    SELECT id FROM conversation_memory 
                    WHERE session_id = ? 
                    ORDER BY id DESC LIMIT 50
                )
            """, (session_id, session_id))

    @classmethod
    def get_history(cls, session_id: str, limit: int = 10):
        with sqlite3.connect(cls.DB_PATH) as conn:
            cursor = conn.execute("""
                SELECT role, content FROM conversation_memory 
                WHERE session_id = ? 
                ORDER BY id DESC LIMIT ?
            """, (session_id, limit))
            # Reverse to get chronological order
            return [{"role": r[0], "content": r[1]} for r in cursor.fetchall()][::-1]

    @classmethod
    def get_stats(cls) -> dict:
        """Returns infrastructure and vault metrics."""
        with sqlite3.connect(cls.DB_PATH) as conn:
            cursor = conn.execute("SELECT COUNT(*), SUM(token_count) FROM vault_index")
            vault_count, total_tokens = cursor.fetchone()
            
            cursor = conn.execute("SELECT COUNT(*) FROM conversation_memory")
            msg_count = cursor.fetchone()[0]
            
            return {
                "vault_files": vault_count or 0,
                "total_tokens": total_tokens or 0,
                "total_messages": msg_count or 0,
                "db_path": cls.DB_PATH
            }

    @classmethod
    def clear_session(cls, session_id: str):
        """Resets the conversation memory for a session."""
        with sqlite3.connect(cls.DB_PATH) as conn:
            conn.execute("DELETE FROM conversation_memory WHERE session_id = ?", (session_id,))
            logger.info(f"🧹 Session {session_id} cleared from Sovereign State.")

