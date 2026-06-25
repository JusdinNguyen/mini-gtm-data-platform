"""
Name: Justin Nguyen
File: main.py

Description:
This file is the entry point for the GTM outreach agent. It connects the
separate parts of the project together: database access, schema inspection,
account input resolution, account context retrieval, rules-based outreach
strategy, evidence building, and email drafting.

The main flow is:
1. Read the account or prospect input from the command line
2. Connect to the local DuckDB warehouse
3. Inspect the marts schema
4. Resolve the input into an account
5. Build account context from the GTM tables
6. Apply outreach rules
7. Draft the email
8. Print the outreach angle, evidence, subject, and body
"""

import argparse

from agent.context import build_account_context
from agent.database import connect_to_database
from agent.drafter import draft_email
from agent.resolver import resolve_account_input
from agent.rules import apply_rules
from agent.schema import inspect_marts_schema


# parse_arguments reads command-line inputs from the user.
# The account input is required, while the database path has a default value.
def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Draft a personalized GTM outreach email for an account or prospect."
    )

    parser.add_argument(
        "account_name",
        help="Account name, partial account name, or prospect email to draft outreach for.",
    )

    parser.add_argument(
        "--database-path",
        default="warehouse/data.duckdb",
        help="Path to the local DuckDB database.",
    )

    return parser.parse_args()


# print_evidence displays the evidence facts used by the agent.
# This makes the output easier to inspect and debug.
def print_evidence(evidence) -> None:
    if len(evidence) == 0:
        print("No evidence found.")
        return

    print("Evidence:")

    for fact in evidence:
        print(f"- [{fact.source}] {fact.text}")


# main runs the full GTM outreach agent workflow.
def main() -> None:
    args = parse_arguments()

    connection = connect_to_database(args.database_path)
    schema = inspect_marts_schema(connection)

    resolved_account = resolve_account_input(
        connection,
        schema,
        args.account_name,
    )

    if resolved_account is None:
        print(f"No account found for: {args.account_name}")
        return

    resolved_account_name = resolved_account.get("name")

    account_context = build_account_context(
        connection,
        schema,
        resolved_account_name,
    )

    account = account_context.get("account")

    if account is None:
        print(f"No account found for: {args.account_name}")
        return

    rules_result = apply_rules(account_context)
    outreach_angle = rules_result["outreach_angle"]
    evidence = rules_result["evidence"]

    email = draft_email(
        account_name=account.get("name"),
        outreach_angle=outreach_angle,
        evidence=evidence,
    )

    print(f"Account: {account.get('name')}")
    print(f"Outreach angle: {outreach_angle}")
    print()

    print_evidence(evidence)
    print()

    print(f"Subject: {email.subject}")
    print()
    print(email.body)


if __name__ == "__main__":
    main()