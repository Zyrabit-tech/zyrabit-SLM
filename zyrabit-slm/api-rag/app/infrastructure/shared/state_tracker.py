import sqlite3
import logging
from datetime import datetime

logger = logging.getLogger("uvicorn.error")

class IngestionTracker:
    """
    KISS State Tracker: Tracks document ingestion to ensure self-healing.
    """
    DB_PATH = "/app/ingestion_state.db"
    _initialized = False

    @classmethod
    def init_db(cls, db_path: str = None):
        if db_path:
            cls.DB_PATH = db_path
        
        with sqlite3.connect(cls.DB_PATH) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ingests (
                    doc_id TEXT PRIMARY KEY,
                    filename TEXT,
                    status TEXT,
                    created_at TIMESTAMP
                )
            """)

    @classmethod
    def register_ingest(cls, doc_id: str, filename: str):
        with sqlite3.connect(cls.DB_PATH) as conn:
            conn.execute(
                "INSERT INTO ingests (doc_id, filename, status, created_at) VALUES (?, ?, ?, ?)",
                (doc_id, filename, "PENDING", datetime.now())
            )

    @classmethod
    def complete_ingest(cls, doc_id: str):
        with sqlite3.connect(cls.DB_PATH) as conn:
            conn.execute("UPDATE ingests SET status = 'COMPLETED' WHERE doc_id = ?", (doc_id,))

    @classmethod
    def get_stale_ingests(cls):
        """Returns doc_ids that are stuck in PENDING."""
        with sqlite3.connect(cls.DB_PATH) as conn:
            cursor = conn.execute("SELECT doc_id FROM ingests WHERE status = 'PENDING'")
            return [row[0] for row in cursor.fetchall()]

    @classmethod
    def clear_stale(cls, doc_id: str):
        with sqlite3.connect(cls.DB_PATH) as conn:
            conn.execute("DELETE FROM ingests WHERE doc_id = ?", (doc_id,))
