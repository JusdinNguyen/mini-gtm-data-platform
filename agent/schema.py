"""
Name: Justin Nguyen
File: schema.py

Description: This file defines and understands the database schema for the
agent. It does not retrieve account-specific business data. Instead, it
inspects the marts schema to understand which tables and columns exist.
This helps the agent learn the correct table and column names before later
files retrieve business data.
"""

# These helpers come from database.py. schema.py uses them to run SQL
# without rewriting database connection or query logic.
from agent.database import fetch_rows


# inspect_marts_schema looks at the database structure for the marts schema.
# The marts schema contains the cleaned business records used by the agent.
#
# Expected table types:
# - accounts: company details like name, industry, segment, and ARR
# - opportunities: sales deal details like stage, amount, and next step
# - calls: recent conversations, risks, and buying signals
# - funnel: prospect activity like lead score and campaign source
# - product usage: active users, events, and feature usage
#
# This function does not retrieve company-specific data. It returns the
# available table names and their column names so later files can query them.
def inspect_marts_schema(connection) -> dict[str, list[str]]:
    schema_rows = fetch_rows(
        connection,
        """
        SELECT table_name, column_name
        FROM information_schema.columns
        WHERE table_schema = 'marts'
        ORDER BY table_name, ordinal_position
        """,
    )

    schema = {}

    for row in schema_rows:
        table_name = row["table_name"]
        column_name = row["column_name"]

        if table_name not in schema:
            schema[table_name] = []

        schema[table_name].append(column_name)

    return schema


# find_table looks for a table name that contains an expected keyword.
# This helps the agent find tables like dim_accounts or
# fct_opportunities without knowing the exact table name.
def find_table(
    schema: dict[str, list[str]],
    expected_keyword: str,
) -> str | None:

    for table_name in schema.keys():
        if expected_keyword.lower() in table_name.lower():
            return table_name

    return None


# find_column looks inside one table and finds a column that matches one
# of the expected names. This helps the agent handle small naming
# differences, such as name vs account_name or arr vs
# annual_recurring_revenue.
def find_column(
    schema: dict[str, list[str]],
    table_name: str,
    expected_names: list[str],
) -> str | None:
    columns = schema.get(table_name, [])

    for column_name in columns:
        column_name_lower = column_name.lower()

        for expected_name in expected_names:
            if expected_name.lower() == column_name_lower:
                return column_name

    return None