"""
Name: Justin Nguyen
File: resolver.py

Description:
This file resolves user input into an account name that the rest of the agent
can use. It supports exact account names, partial account names, and prospect
emails from the funnel table.
"""

from typing import Any

from agent.database import fetch_one_row, fetch_rows
from agent.schema import find_column, find_table


def is_email(user_input: str) -> bool:
    """
    Summary:
    is_email checks whether the user input looks like an email address.

    @param user_input: the raw input entered by the user

    @return: True if the input looks like an email address, otherwise False
    """
    return "@" in user_input and "." in user_input


def resolve_exact_account_name(
    connection,
    schema: dict[str, list[str]],
    user_input: str,
) -> dict[str, Any] | None:
    """
    Summary:
    resolve_exact_account_name tries to find an account by exact account name.

    @param connection: the DuckDB database connection
    @param schema: the inspected database schema
    @param user_input: the account name entered by the user

    @return: the matching account row, or None if no exact match is found
    """
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
        LIMIT 1
        """,
        [user_input],
    )


def resolve_partial_account_name(
    connection,
    schema: dict[str, list[str]],
    user_input: str,
) -> dict[str, Any] | None:
    """
    Summary:
    resolve_partial_account_name tries to find an account by partial company
    name. If there is exactly one match, it returns that account. If there are
    multiple matches, it prints the options and asks the user to be more
    specific instead of guessing.

    @param connection: the DuckDB database connection
    @param schema: the inspected database schema
    @param user_input: the partial account name entered by the user

    @return: the matching account row, or None if no safe match is found
    """
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

    matches = fetch_rows(
        connection,
        f"""
        SELECT *
        FROM marts.{accounts_table}
        WHERE lower({name_column}) LIKE lower(?)
        ORDER BY {name_column}
        LIMIT 5
        """,
        [f"%{user_input}%"],
    )

    if len(matches) == 1:
        return matches[0]

    if len(matches) > 1:
        print("Multiple account matches found. Please be more specific:")

        for match in matches:
            print(f"- {match.get(name_column)}")

        return None

    return None


def resolve_prospect_email(
    connection,
    schema: dict[str, list[str]],
    user_input: str,
) -> dict[str, Any] | None:
    """
    Summary:
    resolve_prospect_email tries to find a lead by email in the funnel table.
    If the lead has a converted_account_id, it resolves that account ID back
    to an account row.

    @param connection: the DuckDB database connection
    @param schema: the inspected database schema
    @param user_input: the prospect email entered by the user

    @return: the connected account row, or None if no connected account is found
    """
    funnel_table = find_table(schema, "funnel")
    accounts_table = find_table(schema, "account")

    if funnel_table is None or accounts_table is None:
        return None

    email_column = find_column(
        schema,
        funnel_table,
        ["email"],
    )

    converted_account_id_column = find_column(
        schema,
        funnel_table,
        ["converted_account_id"],
    )

    if email_column is None or converted_account_id_column is None:
        return None

    lead = fetch_one_row(
        connection,
        f"""
        SELECT *
        FROM marts.{funnel_table}
        WHERE lower({email_column}) = lower(?)
        LIMIT 1
        """,
        [user_input],
    )

    if lead is None:
        return None

    converted_account_id = lead.get(converted_account_id_column)

    if converted_account_id is None:
        print("Prospect email found, but it is not connected to an account yet.")
        return None

    account_id_column = find_column(
        schema,
        accounts_table,
        ["account_id", "accountid"],
    )

    if account_id_column is None:
        return None

    return fetch_one_row(
        connection,
        f"""
        SELECT *
        FROM marts.{accounts_table}
        WHERE {account_id_column} = ?
        LIMIT 1
        """,
        [converted_account_id],
    )


def resolve_account_input(
    connection,
    schema: dict[str, list[str]],
    user_input: str,
) -> dict[str, Any] | None:
    """
    Summary:
    resolve_account_input is the main resolver function used by main.py. It
    cleans the input, checks whether it looks like an email, then tries email
    lookup, exact account-name lookup, and partial account-name lookup.

    @param connection: the DuckDB database connection
    @param schema: the inspected database schema
    @param user_input: the raw account or prospect input entered by the user

    @return: the resolved account row, or None if no account is found
    """
    cleaned_input = user_input.strip()

    if cleaned_input == "":
        return None

    if is_email(cleaned_input):
        account = resolve_prospect_email(
            connection,
            schema,
            cleaned_input,
        )

        if account is not None:
            return account

    account = resolve_exact_account_name(
        connection,
        schema,
        cleaned_input,
    )

    if account is not None:
        return account

    return resolve_partial_account_name(
        connection,
        schema,
        cleaned_input,
    )