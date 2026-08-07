"""Durable SQLite metadata, FTS and session adapter for one local node."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Sequence

from app.node.domain import EvidenceUnit, IngestionJob, Source, utcnow


class SQLiteNodeStore:
    def __init__(self, path: str):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def _connect(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize(self) -> None:
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS node_sources (
                  id TEXT PRIMARY KEY, filename TEXT NOT NULL, media_type TEXT NOT NULL,
                  sha256 TEXT NOT NULL UNIQUE, size_bytes INTEGER NOT NULL, stored_path TEXT NOT NULL,
                  created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS node_documents (
                  id TEXT PRIMARY KEY, source_id TEXT NOT NULL, version INTEGER NOT NULL DEFAULT 1,
                  parser TEXT NOT NULL, status TEXT NOT NULL, error TEXT, created_at TEXT NOT NULL,
                  UNIQUE(source_id, version)
                );
                CREATE TABLE IF NOT EXISTS node_evidence (
                  id TEXT PRIMARY KEY, document_id TEXT NOT NULL, content TEXT NOT NULL,
                  ordinal INTEGER NOT NULL, locator_json TEXT NOT NULL, metadata_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_node_evidence_document ON node_evidence(document_id, ordinal);
                CREATE VIRTUAL TABLE IF NOT EXISTS node_evidence_fts USING fts5(
                  evidence_id UNINDEXED, document_id UNINDEXED, content, tokenize='unicode61'
                );
                CREATE TABLE IF NOT EXISTS node_jobs (
                  id TEXT PRIMARY KEY, source_id TEXT NOT NULL, status TEXT NOT NULL, stage TEXT NOT NULL,
                  error TEXT, metrics_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS node_sessions (
                  id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL, role TEXT NOT NULL,
                  content TEXT NOT NULL, created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_node_sessions ON node_sessions(session_id, id);
                CREATE TABLE IF NOT EXISTS node_audit_events (
                  id TEXT PRIMARY KEY, event_type TEXT NOT NULL, subject_id TEXT NOT NULL,
                  payload_json TEXT NOT NULL, created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS node_capabilities (
                  name TEXT PRIMARY KEY, status TEXT NOT NULL, detail TEXT NOT NULL, checked_at TEXT NOT NULL
                );
            """)

    def create_source(self, source: Source) -> None:
        with self._connect() as conn:
            conn.execute("INSERT OR IGNORE INTO node_sources VALUES (?, ?, ?, ?, ?, ?, ?)",
                         (source.id, source.filename, source.media_type, source.sha256, source.size_bytes, source.stored_path, source.created_at))

    def source_by_hash(self, sha256: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM node_sources WHERE sha256 = ?", (sha256,)).fetchone()
            return dict(row) if row else None

    def create_document(self, document_id: str, source_id: str, parser: str) -> None:
        with self._connect() as conn:
            conn.execute("""INSERT INTO node_documents (id, source_id, version, parser, status, created_at)
                VALUES (?, ?, COALESCE((SELECT MAX(version) + 1 FROM node_documents WHERE source_id = ?), 1), ?, 'queued', ?)""",
                         (document_id, source_id, source_id, parser, utcnow()))

    def set_document_status(self, document_id: str, status: str, error: str | None = None) -> None:
        with self._connect() as conn:
            conn.execute("UPDATE node_documents SET status = ?, error = ? WHERE id = ?", (status, error, document_id))

    def save_evidence(self, evidence: Sequence[EvidenceUnit]) -> None:
        with self._connect() as conn:
            for item in evidence:
                conn.execute("INSERT OR REPLACE INTO node_evidence VALUES (?, ?, ?, ?, ?, ?)",
                    (item.id, item.document_id, item.content, item.ordinal, json.dumps(item.locator), json.dumps(item.metadata)))
                conn.execute("INSERT INTO node_evidence_fts (evidence_id, document_id, content) VALUES (?, ?, ?)",
                    (item.id, item.document_id, item.content))

    def create_job(self, job: IngestionJob) -> None:
        with self._connect() as conn:
            conn.execute("INSERT INTO node_jobs VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (job.id, job.source_id, job.status, job.stage, job.error, json.dumps(job.metrics), job.created_at, job.updated_at))

    def update_job(self, job_id: str, status: str, stage: str, error: str | None = None, metrics: dict | None = None) -> None:
        with self._connect() as conn:
            conn.execute("UPDATE node_jobs SET status=?, stage=?, error=?, metrics_json=COALESCE(?, metrics_json), updated_at=? WHERE id=?",
                         (status, stage, error, json.dumps(metrics) if metrics is not None else None, utcnow(), job_id))

    def get_job(self, job_id: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM node_jobs WHERE id=?", (job_id,)).fetchone()
            if not row: return None
            result = dict(row); result["metrics"] = json.loads(result.pop("metrics_json")); return result

    def get_document(self, document_id: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute("""SELECT d.*, s.filename, s.media_type, s.size_bytes, s.sha256
                FROM node_documents d JOIN node_sources s ON s.id=d.source_id WHERE d.id=?""", (document_id,)).fetchone()
            if not row: return None
            result = dict(row)
            result["evidence_count"] = conn.execute("SELECT count(*) FROM node_evidence WHERE document_id=?", (document_id,)).fetchone()[0]
            return result

    def list_documents(self) -> list[dict]:
        with self._connect() as conn:
            # The library represents sources, not every failed/reindexed attempt.
            # Keep only the newest version per source and expose its state.
            rows = conn.execute("""SELECT d.id, d.version, d.status, d.error, d.created_at,
                s.filename, s.size_bytes, s.media_type
                FROM node_documents d JOIN node_sources s ON s.id=d.source_id
                WHERE d.version = (SELECT MAX(candidate.version) FROM node_documents candidate WHERE candidate.source_id=d.source_id)
                ORDER BY d.created_at DESC""").fetchall()
        return [dict(row) for row in rows]

    def latest_ready_document_for(self, document_id: str) -> dict | None:
        """Resolve an old document-version selection to the ready version of its source."""
        with self._connect() as conn:
            row = conn.execute("""SELECT d.*, s.filename, s.media_type, s.size_bytes, s.sha256
                FROM node_documents selected
                JOIN node_documents d ON d.source_id=selected.source_id
                JOIN node_sources s ON s.id=d.source_id
                WHERE selected.id=? AND d.status='ready'
                ORDER BY d.version DESC LIMIT 1""", (document_id,)).fetchone()
        return dict(row) if row else None

    def source_for_document(self, document_id: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute("""SELECT s.* FROM node_documents d
                JOIN node_sources s ON s.id=d.source_id WHERE d.id=?""", (document_id,)).fetchone()
        return dict(row) if row else None

    def search_lexical(self, query: str, limit: int = 8, document_id: str | None = None) -> list[EvidenceUnit]:
        tokens = [token.replace('"', '') for token in query.split() if len(token) > 2]
        if not tokens: return []
        expression = " OR ".join(f'"{token}"' for token in tokens)
        sql = """SELECT e.*, bm25(node_evidence_fts) AS score FROM node_evidence_fts f
            JOIN node_evidence e ON e.id=f.evidence_id WHERE node_evidence_fts MATCH ?"""
        params: list = [expression]
        if document_id:
            sql += " AND e.document_id=?"; params.append(document_id)
        sql += " ORDER BY score LIMIT ?"; params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [EvidenceUnit(id=row["id"], document_id=row["document_id"], content=row["content"], ordinal=row["ordinal"],
                locator=json.loads(row["locator_json"]), metadata={**json.loads(row["metadata_json"]), "score": row["score"]}) for row in rows]

    def append_message(self, session_id: str, role: str, content: str) -> None:
        with self._connect() as conn:
            conn.execute("INSERT INTO node_sessions (session_id, role, content, created_at) VALUES (?, ?, ?, ?)", (session_id, role, content, utcnow()))

    def get_history(self, session_id: str, limit: int = 8) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute("SELECT role, content FROM node_sessions WHERE session_id=? ORDER BY id DESC LIMIT ?", (session_id, limit)).fetchall()
        return [dict(row) for row in reversed(rows)]

    def clear_history(self, session_id: str) -> None:
        with self._connect() as conn: conn.execute("DELETE FROM node_sessions WHERE session_id=?", (session_id,))

    def capability(self, name: str, status: str, detail: str = "") -> None:
        with self._connect() as conn:
            conn.execute("INSERT OR REPLACE INTO node_capabilities VALUES (?, ?, ?, ?)", (name, status, detail, utcnow()))

    def capabilities(self) -> list[dict]:
        with self._connect() as conn: return [dict(row) for row in conn.execute("SELECT * FROM node_capabilities ORDER BY name")]
