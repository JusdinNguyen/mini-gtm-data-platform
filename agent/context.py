"""
Name: Justin Nguyen
File: context.py

Description:
This file retrieves the real GTM business context for a given account or
prospect. It builds on database.py to run SQL queries and schema.py to find
the correct table and column names.

This file should gather useful account facts, but it should not decide the
outreach strategy or write the email. Those responsibilities belong to
rules.py and drafter.py.

Functions in this file:
- get_account: finds the main account row using the company name
- get_opportunities: finds sales opportunities or deals connected to the account
- get_calls: finds sales calls or conversation records connected to the account
- get_funnel_activity: finds lead, prospect, or campaign activity for the account
- get_product_usage: finds product usage and engagement data for the account
- build_account_context: combines all retrieved business context into one dictionary
"""

# Any is used because database rows can contain different value types,
# including strings, numbers, dates, booleans, or empty values.
from typing import Any

# These helpers run SQL queries and return clean dictionary results.
from agent.database import fetch_one_row, fetch_rows

# These helpers inspect the schema and find the correct table or column names.
from agent.schema import find_column, find_table


# get_account finds the account row for the company name provided by the user.
# It uses schema.py to find the correct accounts table and name column before
# running the actual account lookup query.
def get_account(
    connection,
    schema: dict[str, list[str]],
    account_name: str,
) -> dict[str, Any] | None:
    accounts_table = find_table(schema, "account")

    if accounts_table is None:
        return None

    name_column = find_column(
        schema,
        accounts_table,
        ["name", "account_name", "company", "company_name"],
    )

    if name_column is None:
        return None

    return fetch_one_row(
        connection,
        f"""
        SELECT *
        FROM marts.{accounts_table}
        WHERE lower({name_column}) = lower(?)
        """,
        [account_name],
    )


# get_opportunities finds sales opportunities connected to the account.
# It uses the account_id from the account row to find related deal records.
def get_opportunities(
    connection,
    schema: dict[str, list[str]],
    account: dict[str, Any],
) -> list[dict[str, Any]]:
    opportunities_table = find_table(schema, "opportun")

    if opportunities_table is None:
        return []

    account_id_column = find_column(
        schema,
        opportunities_table,
        ["account_id", "accountid"],
    )

    if account_id_column is None:
        return []

    account_id = account.get("account_id")

    if account_id is None:
        return []

    return fetch_rows(
        connection,
        f"""
        SELECT *
        FROM marts.{opportunities_table}
        WHERE {account_id_column} = ?
        """,
        [account_id],
    )


# get_calls finds sales call or conversation records connected to the account.
# It uses the account_id from the account row to find related call records.
def get_calls(
    connection,
    schema: dict[str, list[str]],
    account: dict[str, Any],
) -> list[dict[str, Any]]:
    calls_table = find_table(schema, "call")

    if calls_table is None:
        return []

    account_id_column = find_column(
        schema,
        calls_table,
        ["account_id", "accountid"],
    )

    if account_id_column is None:
        return []

    account_id = account.get("account_id")

    if account_id is None:
        return []

    return fetch_rows(
        connection,
        f"""
        SELECT *
        FROM marts.{calls_table}
        WHERE {account_id_column} = ?
        """,
        [account_id],
    )


# get_funnel_activity finds lead, prospect, or campaign activity connected
# to the account. The funnel table may use converted_account_id for converted
# leads or company for unconverted leads, so this function tries both paths.
def get_funnel_activity(
    connection,
    schema: dict[str, list[str]],
    account: dict[str, Any],
) -> list[dict[str, Any]]:
    funnel_table = find_table(schema, "funnel")

    if funnel_table is None:
        return []

    account_id = account.get("account_id")
    account_name = account.get("name")

    converted_account_id_column = find_column(
        schema,
        funnel_table,
        ["converted_account_id"],
    )

    if converted_account_id_column is not None and account_id is not None:
        funnel_rows = fetch_rows(
            connection,
            f"""
            SELECT *
            FROM marts.{funnel_table}
            WHERE {converted_account_id_column} = ?
            """,
            [account_id],
        )

        if len(funnel_rows) > 0:
            return funnel_rows

    company_column = find_column(
        schema,
        funnel_table,
        ["company", "company_name", "account_name"],
    )

    if company_column is None or account_name is None:
        return []

    return fetch_rows(
        connection,
        f"""
        SELECT *
        FROM marts.{funnel_table}
        WHERE lower({company_column}) = lower(?)
        """,
        [account_name],
    )


# get_product_usage finds product engagement data connected to the account.
# It uses the account_id from the account row to find related usage records.
def get_product_usage(
    connection,
    schema: dict[str, list[str]],
    account: dict[str, Any],
) -> list[dict[str, Any]]:
    usage_table = find_table(schema, "usage")

    if usage_table is None:
        return []

    account_id_column = find_column(
        schema,
        usage_table,
        ["account_id", "accountid"],
    )

    if account_id_column is None:
        return []

    account_id = account.get("account_id")

    if account_id is None:
        return []

    return fetch_rows(
        connection,
        f"""
        SELECT *
        FROM marts.{usage_table}
        WHERE {account_id_column} = ?
        """,
        [account_id],
    )


# build_account_context gathers all business context for one account.
# It first finds the main account row, then uses that account to find
# related opportunities, calls, funnel activity, and product usage.
def build_account_context(
    connection,
    schema: dict[str, list[str]],
    account_name: str,
) -> dict[str, Any]:
    account = get_account(connection, schema, account_name)

    if account is None:
        return {
            "account": None,
            "opportunities": [],
            "calls": [],
            "funnel_activity": [],
            "product_usage": [],
        }

    return {
        "account": account,
        "opportunities": get_opportunities(connection, schema, account),
        "calls": get_calls(connection, schema, account),
        "funnel_activity": get_funnel_activity(connection, schema, account),
        "product_usage": get_product_usage(connection, schema, account),
    }