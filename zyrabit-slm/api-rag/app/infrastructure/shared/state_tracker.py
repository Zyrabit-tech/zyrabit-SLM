import os
import sqlite3
import logging
import hashlib
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("zyrabit.api")

DEFAULT_SOUL_PROMPT = """
## Soul

What You Are:
Not a chatbot. Not an assistant. You are the co-piloto de confianza de Abraham — la persona que conoce el contexto, anticipa lo que necesita, y ejecuta sin que le pidan permiso para cada paso.

## How You Show Up:
- Directo y cálido. No uses "¡Hola! ¿En qué puedo ayudarte hoy?". Entra con el contexto. Si ya sabes que está en fundraising, pregúntale "¿Cómo va el deck?" o "¿Necesitas que revise el término de este SAFE?".
- Celebra los wins como lo haría un co-founder: "Ese PR a awesome-ai-agents ya entró. Buena jugada."
- Sé honesto cuando algo no está bien. Si una idea es mala, dilo sin rodeos: "Eso no va a funcionar por X. Mejor intentemos Y."
- Proactivo, no reactivo. Si detectas un patrón, actúa (ej. buscar contactos o redactar emails). Construye cosas: tablas, drafts, listas, cronogramas. No solo sugieras.
- Técnico por defecto. Usa jerga técnica precisa (ej. "QAT 4-bit" en lugar de "versión ligera"). Detalla riesgos técnicos y omite lo obvio.
- Bilingüe natural. Responde en el idioma de la consulta. Si escribe en español, respondes en español. Usa términos técnicos estándar en inglés sin traducirlos mal.

## How You Work:
1. Actúa primero, pregunta después. Asume suposiciones razonables (ej. "envíame el reporte mañana" -> 9:00 AM CST, formato breve). Menciona las suposiciones y haz máximo una pregunta de clarificación por consulta.
2. Investiga antes de pedir. Revisa contexto, memoria, archivos y conversaciones pasadas.
3. Cuida la frontera interna/externa: Interno (leer, organizar, redactar drafts) es seguro, actúa libremente. Externo (enviar emails, posts públicos) es de riesgo, pregunta siempre antes.
4. Privacidad absoluta. Sin excepciones.
5. Memoria viva. Cada sesión comienza con el contexto acumulado.

## What You Don't Do:
- No uses lenguaje corporativo ("sinergizar", etc.).
- No seas un yes-man.
- No interrogues. Deduce 4 datos de 5 y pregunta solo 1.
- No entregues solo texto cuando una tabla, un cronograma o un script sería más útil.
- No finjas emociones.
""".strip()


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
            # Performance index for session-based lookups
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversation_session
                ON conversation_memory(session_id)
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

            # Migration: Add system_prompt if missing
            try:
                conn.execute("ALTER TABLE user_profile ADD COLUMN system_prompt TEXT DEFAULT ''")
            except sqlite3.OperationalError:
                pass # Column exists

            # Seed default profile if empty
            cursor = conn.execute("SELECT COUNT(*) FROM user_profile")
            if cursor.fetchone()[0] == 0:
                conn.execute("""
                    INSERT INTO user_profile (id, name, email, role, interests, persona, preferred_model, tone, assistant_name, system_prompt, onboarding_completed)
                    VALUES (1, 'Abraham', 'abraham@zyrabit.com', 'Co-Founder / Architect', 'Docker, SLMs, quantization, agent architectures', 'soul', 'qwen2.5:7b', 'warm-direct', 'Zyra', ?, 1)
                """, (DEFAULT_SOUL_PROMPT,))
                logger.info("Seeded default Abraham 'Soul' profile.")

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
        cls._ensure_db()
        with sqlite3.connect(cls.DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM user_profile WHERE id = 1")
            row = cursor.fetchone()
            if row:
                return dict(row)
            return {}

    @classmethod
    def update_user_profile(cls, name: str, role: str, interests: str, email: str = "contact@zyrabit.com", persona: str = 'general', preferred_model: str = 'qwen2.5:7b', tone: str = 'professional', assistant_name: str = 'Zyra', system_prompt: str = ''):
        with sqlite3.connect(cls.DB_PATH) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO user_profile (id, name, email, role, interests, persona, preferred_model, tone, assistant_name, system_prompt, onboarding_completed)
                VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (name, email, role, interests, persona, preferred_model, tone, assistant_name, system_prompt))




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
        cls._ensure_db()
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

                # SECURITY: Sanitize each token before building the FTS5 match expression.
                # FTS5 treats AND, OR, NOT, and quoted phrases as operators.
                # We strip any character that is not alphanumeric or a hyphen,
                # then use the 'token*' prefix-match form which is always safe.
                def _safe_fts_token(t: str) -> str:
                    # Keep only alphanumeric and hyphens; quote remaining via FTS5 double-quote escaping
                    sanitized = ''.join(c for c in t if c.isalnum() or c == '-')
                    return sanitized

                tokens = [
                    _safe_fts_token(t)
                    for t in query.split()
                    if len(t) > 2
                ]
                # Drop empty tokens that became empty after sanitization
                tokens = [t for t in tokens if t]
                fts_query = " OR ".join(f"{t}*" for t in tokens)

                if not fts_query:
                    return []

                cursor = conn.execute("""
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
        cls._ensure_db()
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
        cls._ensure_db()
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
        cls._ensure_db()
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
        cls._ensure_db()
        with sqlite3.connect(cls.DB_PATH) as conn:
            conn.execute("DELETE FROM conversation_memory WHERE session_id = ?", (session_id,))
            logger.info(f"🧹 Session {session_id} cleared from Sovereign State.")

    @classmethod
    def _ensure_db(cls):
        try:
            with sqlite3.connect(cls.DB_PATH) as conn:
                conn.execute("SELECT 1 FROM conversation_memory LIMIT 1")
        except sqlite3.OperationalError:
            cls.init_db()
