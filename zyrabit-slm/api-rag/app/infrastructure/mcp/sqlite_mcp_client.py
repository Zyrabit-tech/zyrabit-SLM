import re
import sqlite3
from pathlib import Path
from typing import Any
from urllib.parse import quote

from app.infrastructure.shared.config import DOCS_DIR


class SQLiteMCPClient:
    """
    Read-only SQLite adapter for MCP.

    SQLite databases are restricted to the configured
    local workspace and are always opened in read-only mode.
    """

    ALLOWED_SUFFIXES = {".db", ".sqlite", ".sqlite3"}
    MAX_ROW_LIMIT = 500

    def __init__(self, workspace_root: str | Path = DOCS_DIR):
        self.workspace_root = Path(workspace_root).resolve()

    @staticmethod
    def _validate_query(sql_query: str) -> str:
        """Allow only SELECT and EXPLAIN queries."""

        if not sql_query or not sql_query.strip():
            raise ValueError("sql_query is required.")

        query = sql_query.strip()

        # Remove leading SQL comments.
        query_without_comments = re.sub(
            r"^(?:\s|--[^\n]*(?:\n|$)|/\*.*?\*/)*",
            "",
            query,
            flags=re.DOTALL,
        ).strip()

        normalized_query = query_without_comments.rstrip(";").strip()

        if not normalized_query:
            raise ValueError("sql_query is required.")

        # Only SELECT and EXPLAIN are allowed.
        if not re.match(
            r"^(SELECT|EXPLAIN)\b",
            normalized_query,
            re.IGNORECASE,
        ):
            raise PermissionError(
                "Only SELECT and EXPLAIN queries are allowed."
            )

        # Explicitly reject mutating/configuration statements.
        forbidden = re.search(
            r"\b("
            r"INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|"
            r"ATTACH|DETACH|VACUUM|REINDEX|PRAGMA"
            r")\b",
            normalized_query,
            re.IGNORECASE,
        )

        if forbidden:
            raise PermissionError(
                f"SQL statement '{forbidden.group(1).upper()}' "
                "is not allowed."
            )

        # Reject multiple statements.
        if ";" in normalized_query:
            raise PermissionError(
                "Multiple SQL statements are not allowed."
            )

        return normalized_query

    def _validate_db_path(self, db_path: str) -> Path:
        """Validate SQLite database path."""

        if not db_path or not str(db_path).strip():
            raise ValueError("db_path is required.")

        path = Path(db_path).resolve(strict=False)

        if path.suffix.lower() not in self.ALLOWED_SUFFIXES:
            raise ValueError(
                "Only .db, .sqlite, and .sqlite3 files are allowed."
            )

        # Check workspace confinement BEFORE checking whether
        # the file exists. This prevents information disclosure
        # about paths outside the allowed workspace.
        try:
            path.relative_to(self.workspace_root)
        except ValueError:
            raise PermissionError(
                "SQLite database must be inside the configured workspace."
            )

        if not path.exists() or not path.is_file():
            raise FileNotFoundError(
                f"SQLite database not found: {db_path}"
            )

        return path

    @staticmethod
    def _connect_read_only(db_path: Path) -> sqlite3.Connection:
        """Open SQLite database in read-only mode."""

        # Encode URI-special characters such as '#', '?', and '%'
        # so they cannot alter the SQLite URI semantics.
        encoded_path = quote(db_path.as_posix(), safe="/:")

        uri = f"file:{encoded_path}?mode=ro"

        connection = sqlite3.connect(
            uri,
            uri=True,
            timeout=5,
        )

        # Additional SQLite-level protection against writes.
        connection.execute("PRAGMA query_only = ON")

        return connection

    def get_schema(self, db_path: str) -> list[dict[str, Any]]:
        """Return tables and their column schemas."""

        path = self._validate_db_path(db_path)
        connection = self._connect_read_only(path)

        try:
            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                AND name NOT LIKE 'sqlite_%'
                ORDER BY name
                """
            )

            tables = []

            for (table_name,) in cursor.fetchall():
                safe_table_name = table_name.replace('"', '""')

                cursor.execute(
                    f'PRAGMA table_info("{safe_table_name}")'
                )

                columns = []

                for row in cursor.fetchall():
                    columns.append(
                        {
                            "name": row[1],
                            "type": row[2],
                            "not_null": bool(row[3]),
                            "default": row[4],
                            "primary_key": bool(row[5]),
                        }
                    )

                tables.append(
                    {
                        "table": table_name,
                        "columns": columns,
                    }
                )

            return tables

        finally:
            connection.close()

    def execute_query(
        self,
        db_path: str,
        sql_query: str,
        max_rows: int = MAX_ROW_LIMIT,
    ) -> dict[str, Any]:
        """Execute a bounded read-only SELECT or EXPLAIN query."""

        if max_rows < 1:
            raise ValueError("max_rows must be greater than zero.")

        path = self._validate_db_path(db_path)
        query = self._validate_query(sql_query)

        connection = self._connect_read_only(path)

        try:
            cursor = connection.cursor()
            cursor.execute(query)

            fetched_rows = cursor.fetchmany(max_rows + 1)
            truncated = len(fetched_rows) > max_rows
            rows = fetched_rows[:max_rows]

            columns = (
                [description[0] for description in cursor.description]
                if cursor.description
                else []
            )

            return {
                "columns": columns,
                "rows": [list(row) for row in rows],
                "row_count": len(rows),
                "truncated": truncated,
                "warning": (
                    f"Query exceeded max limit of {max_rows} rows and was truncated."
                    if truncated
                    else None
                ),
            }

        finally:
            connection.close()


sqlite_client = SQLiteMCPClient()
