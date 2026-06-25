"""
Name: Justin Nguyen
File: database.py

Description:
This file contains the low-level DuckDB helper functions for the GTM outreach
agent. It is responsible for opening the database connection and running SQL
queries in a reusable way. This file does not contain business logic about
accounts, opportunities, lead scores, or email drafting.
"""

# Path helps the agent work with file paths in a clean way.
# I use it to check that the DuckDB database file exists before opening it.
from pathlib import Path

# Any is used for type hints when a value can be more than one type.
# Database rows can contain strings, numbers, dates, booleans, or empty values.
from typing import Any

# duckdb is the database library used to open and query warehouse/data.duckdb.
# The agent uses this connection to read the GTM tables from the local warehouse.
import duckdb


# connect_to_database opens the local DuckDB warehouse for reading.
# database_path is the path to the database file, usually warehouse/data.duckdb.
def connect_to_database(database_path: str) -> duckdb.DuckDBPyConnection:
    database_file = Path(database_path)

    if not database_file.exists():
        raise FileNotFoundError(f"Database file not found: {database_path}")

    return duckdb.connect(database_path, read_only=True)


# fetch_rows runs a SQL query and returns all rows from the result.
# connection is the open DuckDB connection, sql is the query to run, and
# parameters holds optional values that should be safely passed into the query.
def fetch_rows(
    connection: duckdb.DuckDBPyConnection,
    sql: str,
    parameters: list[Any] | None = None,
) -> list[dict[str, Any]]:
    query_result = connection.execute(sql, parameters or [])
    column_names = [column[0] for column in query_result.description]

    return [
        dict(zip(column_names, row))
        for row in query_result.fetchall()
    ]


# fetch_one_row runs a SQL query and returns only the first matching row.
# This is useful when the agent needs to look up one account or prospect.
def fetch_one_row(
    connection: duckdb.DuckDBPyConnection,
    sql: str,
    parameters: list[Any] | None = None,
) -> dict[str, Any] | None:
    matching_rows = fetch_rows(connection, sql, parameters)

    if len(matching_rows) == 0:
        return None

    return matching_rows[0]