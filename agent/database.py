"""
Name: Justin Nguyen
File: database.py

Description:
This file contains the low-level DuckDB helper functions for the GTM outreach
agent. It is responsible for opening the database connection and running SQL
queries in a reusable way. This file does not contain business logic about
accounts, opportunities, lead scores, or email drafting.
"""

from pathlib import Path
from typing import Any

import duckdb


def connect_to_database(database_path: str) -> duckdb.DuckDBPyConnection:
    """
    Summary:
    connect_to_database opens the local DuckDB warehouse for reading. It also
    checks that the database file exists before trying to connect.

    @param database_path: the path to the DuckDB database file

    @return: a read-only DuckDB database connection
    """
    database_file = Path(database_path)

    if not database_file.exists():
        raise FileNotFoundError(f"Database file not found: {database_path}")

    return duckdb.connect(database_path, read_only=True)


def fetch_rows(
    connection: duckdb.DuckDBPyConnection,
    sql: str,
    parameters: list[Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Summary:
    fetch_rows runs a SQL query and returns all rows from the result as
    dictionaries. Each dictionary uses column names as keys.

    @param connection: the open DuckDB database connection
    @param sql: the SQL query to run
    @param parameters: optional values to safely pass into the SQL query

    @return: a list of dictionary rows from the query result
    """
    query_result = connection.execute(sql, parameters or [])
    column_names = [column[0] for column in query_result.description]

    return [
        dict(zip(column_names, row))
        for row in query_result.fetchall()
    ]


def fetch_one_row(
    connection: duckdb.DuckDBPyConnection,
    sql: str,
    parameters: list[Any] | None = None,
) -> dict[str, Any] | None:
    """
    Summary:
    fetch_one_row runs a SQL query and returns only the first matching row.
    This is useful when the agent needs to look up one account or prospect.

    @param connection: the open DuckDB database connection
    @param sql: the SQL query to run
    @param parameters: optional values to safely pass into the SQL query

    @return: the first matching dictionary row, or None if no rows are found
    """
    matching_rows = fetch_rows(connection, sql, parameters)

    if len(matching_rows) == 0:
        return None

    return matching_rows[0]