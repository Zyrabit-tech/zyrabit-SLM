import sqlite3

import pytest

from app.infrastructure.mcp.sqlite_mcp_client import SQLiteMCPClient


@pytest.fixture
def sqlite_db(tmp_path):
    db_path = tmp_path / "test.db"

    connection = sqlite3.connect(db_path)
    try:
        connection.execute(
            "CREATE TABLE students (id INTEGER PRIMARY KEY, name TEXT, marks INTEGER)"
        )
        connection.executemany(
            "INSERT INTO students (name, marks) VALUES (?, ?)",
            [
                ("Alice", 85),
                ("Bob", 90),
            ],
        )
        connection.commit()
    finally:
        connection.close()

    return db_path


@pytest.fixture
def client(tmp_path):
    return SQLiteMCPClient(tmp_path)


def test_sqlite_schema_returns_tables_and_columns(client, sqlite_db):
    result = client.get_schema(str(sqlite_db))

    assert len(result) == 1
    assert result[0]["table"] == "students"

    columns = result[0]["columns"]
    column_names = [column["name"] for column in columns]

    assert column_names == ["id", "name", "marks"]


def test_sqlite_query_select_returns_rows(client, sqlite_db):
    result = client.execute_query(
        str(sqlite_db),
        "SELECT name, marks FROM students ORDER BY id",
    )

    assert result["columns"] == ["name", "marks"]
    assert result["rows"] == [
        ["Alice", 85],
        ["Bob", 90],
    ]
    assert result["row_count"] == 2
    assert result["truncated"] is False
    assert result["warning"] is None


def test_sqlite_query_truncates_rows_at_default_limit(client, sqlite_db):
    connection = sqlite3.connect(sqlite_db)
    try:
        connection.executemany(
            "INSERT INTO students (name, marks) VALUES (?, ?)",
            [(f"Student {index}", index) for index in range(598)],
        )
        connection.commit()
    finally:
        connection.close()

    result = client.execute_query(
        str(sqlite_db),
        "SELECT id, name, marks FROM students ORDER BY id",
    )

    assert result["row_count"] == 500
    assert len(result["rows"]) == 500
    assert result["truncated"] is True
    assert result["warning"] == (
        "Query exceeded max limit of 500 rows and was truncated."
    )


def test_sqlite_query_supports_custom_row_limit(client, sqlite_db):
    result = client.execute_query(
        str(sqlite_db),
        "SELECT name, marks FROM students ORDER BY id",
        max_rows=1,
    )

    assert result["rows"] == [["Alice", 85]]
    assert result["row_count"] == 1
    assert result["truncated"] is True
    assert result["warning"] == (
        "Query exceeded max limit of 1 rows and was truncated."
    )


def test_sqlite_query_rejects_non_positive_row_limit(client, sqlite_db):
    with pytest.raises(ValueError, match="max_rows must be greater than zero"):
        client.execute_query(
            str(sqlite_db),
            "SELECT * FROM students",
            max_rows=0,
        )


def test_sqlite_query_allows_explain(client, sqlite_db):
    result = client.execute_query(
        str(sqlite_db),
        "EXPLAIN SELECT * FROM students",
    )

    assert result["row_count"] > 0


@pytest.mark.parametrize(
    "query",
    [
        "INSERT INTO students (name, marks) VALUES ('Eve', 95)",
        "UPDATE students SET marks = 100",
        "DELETE FROM students",
        "DROP TABLE students",
        "ALTER TABLE students ADD COLUMN age INTEGER",
        "CREATE TABLE users (id INTEGER)",
    ],
)
def test_sqlite_query_rejects_mutating_statements(client, sqlite_db, query):
    with pytest.raises(PermissionError):
        client.execute_query(str(sqlite_db), query)


def test_sqlite_query_rejects_database_outside_workspace(client, tmp_path):
    outside_db = tmp_path.parent / "outside.db"

    connection = sqlite3.connect(outside_db)
    try:
        connection.execute("CREATE TABLE test (id INTEGER)")
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(PermissionError):
        client.execute_query(
            str(outside_db),
            "SELECT * FROM test",
        )


def test_sqlite_query_rejects_non_sqlite_extension(client, tmp_path):
    bad_path = tmp_path / "test.txt"
    bad_path.write_text("not a database")

    with pytest.raises(ValueError):
        client.execute_query(
            str(bad_path),
            "SELECT * FROM test",
        )


def test_sqlite_connection_is_read_only_for_uri_special_characters(
    client,
    tmp_path,
):
    db_path = tmp_path / "data#1.db"

    connection = sqlite3.connect(db_path)
    try:
        connection.execute(
            "CREATE TABLE students (id INTEGER PRIMARY KEY, name TEXT)"
        )
        connection.execute(
            "INSERT INTO students (name) VALUES ('Alice')"
        )
        connection.commit()
    finally:
        connection.close()

    read_only_connection = client._connect_read_only(db_path)

    try:
        with pytest.raises(sqlite3.OperationalError):
            read_only_connection.execute(
                "UPDATE students SET name = 'Hacked'"
            )
    finally:
        read_only_connection.close()
