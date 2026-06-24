#!/usr/bin/env python3
"""Simple GTM outreach agent for the Mini GTM Data Platform."""

from __future__ import annotations

import argparse
from datetime import date, datetime
from pathlib import Path
from typing import Any

import duckdb


DB_PATH = "warehouse/data.duckdb"
TABLES = {
    "accounts": "marts.dim_accounts",
    "opportunities": "marts.fct_opportunities",
    "calls": "marts.fct_calls",
    "funnel": "marts.fct_funnel",
    "usage": "marts.fct_product_usage",
}


def fmt(value: Any, default: str = "unknown") -> str:
    if value is None:
        return default
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return f"{int(value):,}" if value.is_integer() else f"{value:,.2f}"
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


def money(value: Any) -> str:
    if value is None:
        return "unknown"
    return f"${float(value):,.0f}"


# DuckDB returns tuples; this helper makes the rest of the code read by column name.
def rows(connection, sql: str, params: list[Any] | None = None) -> list[dict[str, Any]]:
    result = connection.execute(sql, params or [])
    names = [column[0] for column in result.description]
    return [dict(zip(names, row)) for row in result.fetchall()]


def one(connection, sql: str, params: list[Any] | None = None) -> dict[str, Any] | None:
    result = rows(connection, sql, params)
    if result:
        return result[0]
    return None


# Discover the actual marts columns before building queries.
def inspect_schema(connection) -> dict[str, list[str]]:
    schema_rows = rows(connection, "select table_name, column_name from information_schema.columns where table_schema = 'marts' order by table_name, ordinal_position")
    schema: dict[str, list[str]] = {}
    for row in schema_rows:
        schema.setdefault(row["table_name"], []).append(row["column_name"])
    return schema


def print_schema(schema: dict[str, list[str]]) -> None:
    print("Discovered marts tables:")
    for table, columns in sorted(schema.items()):
        print(f"- marts.{table}: {len(columns)} columns")
    print()


def require_tables(schema: dict[str, list[str]]) -> None:
    required = ["dim_accounts", "fct_opportunities", "fct_calls", "fct_funnel", "fct_product_usage"]
    missing = [table for table in required if table not in schema]
    if missing:
        raise SystemExit(f"Missing expected marts tables: {', '.join(missing)}")


# Try candidate substrings in order. Exact matches win, then substring matches.
def find_column(schema: dict[str, list[str]], table: str, candidates: list[str], required: bool = True) -> str | None:
    columns = schema.get(table, [])
    exact = {column.lower(): column for column in columns}
    for candidate in candidates:
        key = candidate.lower()
        if key in exact:
            return exact[key]
        for column in columns:
            if key in column.lower():
                return column
    if required:
        raise SystemExit(f"Missing expected column on {table}: one of {', '.join(candidates)}")
    return None


# Resolve the few columns used later, keeping table names documented and fixed.
def resolve_columns(schema: dict[str, list[str]]) -> dict[str, dict[str, str | None]]:
    specs = {
        "accounts": ("dim_accounts", [
            ("account_id", ["account_id", "id"], True), ("account_name", ["account_name", "name", "company"], True),
            ("segment", ["segment"], False), ("industry", ["industry"], False), ("arr", ["arr", "annual_recurring_revenue"], False),
        ]),
        "opportunities": ("fct_opportunities", [
            ("account_id", ["account_id"], False), ("account_name", ["account_name", "company", "account"], False),
            ("id", ["opp_id", "opportunity_id", "deal_id"], False), ("name", ["opp_name", "opportunity_name", "deal_name", "name"], False),
            ("stage", ["stage"], False), ("amount", ["amount"], False), ("is_closed", ["is_closed", "closed"], False),
            ("is_won", ["is_won", "won"], False), ("next_step", ["next_step", "next_steps"], False),
            ("buying", ["buying_signal_mentions", "buying"], False), ("pricing", ["pricing_mentions", "pricing"], False), ("risk", ["risk_mentions", "risk"], False),
        ]),
        "calls": ("fct_calls", [
            ("account_id", ["account_id"], False), ("account_name", ["account_name", "company", "account"], False),
            ("id", ["call_id", "meeting_id"], False), ("date", ["call_date", "meeting_date", "date"], False), ("type", ["call_type", "meeting_type", "type"], False),
            ("buying", ["buying_signal_mentions", "buying"], False), ("pricing", ["pricing_mentions", "pricing"], False),
            ("risk", ["risk_mentions", "risk"], False), ("next_steps", ["next_steps_mentioned", "next_step"], False),
        ]),
        "funnel": ("fct_funnel", [
            ("account_id", ["account_id"], False), ("converted_account_id", ["converted_account_id"], False), ("company", ["company", "account_name", "account"], False),
            ("first_name", ["first_name"], False), ("last_name", ["last_name"], False), ("email", ["email"], False),
            ("lead_id", ["lead_id", "prospect_id"], False), ("lead_score", ["lead_score", "score"], False), ("campaign", ["first_campaign_name", "campaign"], False),
        ]),
        "usage": ("fct_product_usage", [
            ("account_id", ["account_id"], False), ("account_name", ["account_name", "company", "account"], False), ("month", ["usage_month", "month"], False),
            ("active_users", ["active_users", "monthly_active_users"], False), ("events", ["total_events", "events"], False),
            ("features", ["unique_features_used", "features"], False), ("tier", ["engagement_tier", "tier"], False),
        ]),
    }
    resolved: dict[str, dict[str, str | None]] = {}
    for role, (table, fields) in specs.items():
        resolved[role] = {name: find_column(schema, table, candidates, required) for name, candidates, required in fields}
    return resolved


def get(row: dict[str, Any] | None, column: str | None) -> Any:
    if row is None or column is None:
        return None
    return row.get(column)


def account_name(account: dict[str, Any], columns) -> str:
    return str(get(account, columns["accounts"]["account_name"]) or "this account")


def prospect_name(prospect: dict[str, Any] | None, columns, fallback: str | None) -> str | None:
    if prospect is None:
        return fallback
    first = get(prospect, columns["funnel"]["first_name"])
    last = get(prospect, columns["funnel"]["last_name"])
    name = " ".join(str(part) for part in [first, last] if part)
    return name or get(prospect, columns["funnel"]["email"]) or fallback


# Find an account directly, or find a funnel prospect and map it back to an account.
def find_account_and_prospect(connection, columns, account_input: str | None, prospect_input: str | None):
    account_id = columns["accounts"]["account_id"]
    account_name_col = columns["accounts"]["account_name"]
    if account_input:
        sql = f"select * from {TABLES['accounts']} where lower({account_name_col}) = lower(?) or lower({account_name_col}) like lower(?) order by case when lower({account_name_col}) = lower(?) then 0 else 1 end limit 1"
        return one(connection, sql, [account_input, f"%{account_input}%", account_input]), None
    if not prospect_input:
        return None, None

    filters: list[str] = []
    params: list[Any] = []
    search = f"%{prospect_input}%"
    if columns["funnel"]["first_name"] and columns["funnel"]["last_name"]:
        filters.append(f"lower(coalesce({columns['funnel']['first_name']}, '') || ' ' || coalesce({columns['funnel']['last_name']}, '')) like lower(?)")
        params.append(search)
    if columns["funnel"]["email"]:
        filters.append(f"lower(coalesce({columns['funnel']['email']}, '')) like lower(?)")
        params.append(search)
    if not filters:
        return None, None

    order_sql = f"order by {columns['funnel']['lead_score']} desc nulls last" if columns["funnel"]["lead_score"] else ""
    prospect = one(connection, f"select * from {TABLES['funnel']} where {' or '.join(filters)} {order_sql} limit 1", params)
    if prospect is None:
        return None, None

    converted_id = get(prospect, columns["funnel"]["converted_account_id"])
    if converted_id is not None:
        account = one(connection, f"select * from {TABLES['accounts']} where {account_id} = ? limit 1", [converted_id])
        if account:
            return account, prospect

    company = get(prospect, columns["funnel"]["company"])
    if company:
        account = one(connection, f"select * from {TABLES['accounts']} where lower({account_name_col}) = lower(?) limit 1", [company])
        return account or {account_id: None, account_name_col: company}, prospect
    return None, prospect


def account_filter(table_columns, account, columns):
    account_id = get(account, columns["accounts"]["account_id"])
    if table_columns["account_id"] and account_id is not None:
        return f"{table_columns['account_id']} = ?", [account_id]
    if table_columns["account_name"]:
        return f"lower({table_columns['account_name']}) = lower(?)", [account_name(account, columns)]
    return None, []


def order_by(pairs: list[tuple[str | None, str]]) -> str:
    parts = [f"{column} {direction}" for column, direction in pairs if column]
    if not parts:
        return ""
    return f"order by {', '.join(parts)}"


# Pull small result sets from opportunities, calls, usage, and funnel.
def gather_context(connection, columns, account, prospect_input: str | None):
    context = {"opportunities": [], "calls": [], "usage": [], "funnel": []}
    query_plan = [
        ("opportunities", 5, [(columns["opportunities"]["is_closed"], "asc"), (columns["opportunities"]["amount"], "desc nulls last")]),
        ("calls", 4, [(columns["calls"]["date"], "desc nulls last")]),
        ("usage", 2, [(columns["usage"]["month"], "desc nulls last")]),
    ]
    for role, limit, ordering in query_plan:
        where_sql, params = account_filter(columns[role], account, columns)
        if where_sql:
            context[role] = rows(connection, f"select * from {TABLES[role]} where {where_sql} {order_by(ordering)} limit {limit}", params)

    funnel_filters: list[str] = []
    funnel_params: list[Any] = []
    account_id = get(account, columns["accounts"]["account_id"])
    if columns["funnel"]["account_id"] and account_id is not None:
        funnel_filters.append(f"{columns['funnel']['account_id']} = ?")
        funnel_params.append(account_id)
    if columns["funnel"]["converted_account_id"] and account_id is not None:
        funnel_filters.append(f"{columns['funnel']['converted_account_id']} = ?")
        funnel_params.append(account_id)
    if columns["funnel"]["company"]:
        funnel_filters.append(f"lower({columns['funnel']['company']}) = lower(?)")
        funnel_params.append(account_name(account, columns))
    if prospect_input and columns["funnel"]["email"]:
        funnel_filters.append(f"lower(coalesce({columns['funnel']['email']}, '')) like lower(?)")
        funnel_params.append(f"%{prospect_input}%")
    if funnel_filters:
        order_sql = order_by([(columns["funnel"]["lead_score"], "desc nulls last")])
        context["funnel"] = rows(connection, f"select * from {TABLES['funnel']} where {' or '.join(funnel_filters)} {order_sql} limit 4", funnel_params)
    return context


# Decide the email framing with simple deterministic rules.
def detect_relationship_mode(context, columns) -> str:
    for opportunity in context["opportunities"]:
        if not get(opportunity, columns["opportunities"]["is_closed"]):
            return "deal_progression"
    for opportunity in context["opportunities"]:
        if get(opportunity, columns["opportunities"]["is_closed"]) and get(opportunity, columns["opportunities"]["is_won"]):
            return "expansion"
    latest_usage = context["usage"][0] if context["usage"] else None
    if latest_usage and (get(latest_usage, columns["usage"]["active_users"]) or 0) >= 3:
        return "expansion"
    return "cold_outreach"


def add_fact(evidence: list[dict[str, Any]], source: str, row: Any, fact: str) -> None:
    evidence.append({"source": source, "row": fmt(row), "fact": fact})


# Turn rows into a fixed-order evidence list that the email can safely use.
def build_evidence(account, prospect, context, columns) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    name = account_name(account, columns)
    add_fact(evidence, TABLES["accounts"], get(account, columns["accounts"]["account_id"]) or name, f"{name} is a {fmt(get(account, columns['accounts']['segment']))} account in {fmt(get(account, columns['accounts']['industry']))} with {money(get(account, columns['accounts']['arr']))} ARR.")

    if prospect:
        person = prospect_name(prospect, columns, None) or "A prospect"
        add_fact(evidence, TABLES["funnel"], get(prospect, columns["funnel"]["lead_id"]) or get(prospect, columns["funnel"]["email"]) or person, f"{person} engaged through {fmt(get(prospect, columns['funnel']['campaign']))} with lead score {fmt(get(prospect, columns['funnel']['lead_score']))}.")

    for opportunity in context["opportunities"]:
        if get(opportunity, columns["opportunities"]["is_closed"]):
            continue
        fact = f"Open opportunity '{fmt(get(opportunity, columns['opportunities']['name']))}' is in {fmt(get(opportunity, columns['opportunities']['stage']))} for {money(get(opportunity, columns['opportunities']['amount']))}; next step is {fmt(get(opportunity, columns['opportunities']['next_step']))}."
        add_fact(evidence, TABLES["opportunities"], get(opportunity, columns["opportunities"]["id"]), fact)
        break

    if context["usage"]:
        usage = context["usage"][0]
        fact = f"Latest product usage shows {fmt(get(usage, columns['usage']['active_users']), '0')} active users, {fmt(get(usage, columns['usage']['events']), '0')} events, {fmt(get(usage, columns['usage']['features']), '0')} features used, and engagement tier {fmt(get(usage, columns['usage']['tier']))}."
        add_fact(evidence, TABLES["usage"], f"{fmt(get(usage, columns['usage']['account_id']))}:{fmt(get(usage, columns['usage']['month']))}", fact)

    for call in context["calls"]:
        if not any(get(call, columns["calls"][key]) for key in ["buying", "pricing", "risk", "next_steps"]):
            continue
        fact = f"On {fmt(get(call, columns['calls']['date']))}, a {fmt(get(call, columns['calls']['type']))} call had {fmt(get(call, columns['calls']['buying']), '0')} buying-signal mentions, {fmt(get(call, columns['calls']['pricing']), '0')} pricing mentions, {fmt(get(call, columns['calls']['risk']), '0')} risk mentions, and next steps mentioned: {fmt(get(call, columns['calls']['next_steps']))}."
        add_fact(evidence, TABLES["calls"], get(call, columns["calls"]["id"]), fact)
        break
    return evidence[:5]


# Draft a local email from evidence only; no API call is needed.
def draft_email(name: str, person: str | None, relationship_mode: str, evidence: list[dict[str, Any]]) -> str:
    greeting = f"Hi {person.split()[0]}," if person and "@" not in person else "Hi there,"
    facts = [item["fact"] for item in evidence]
    first_fact = facts[0] if facts else "I found recent activity worth discussing."
    second_fact = facts[1] if len(facts) > 1 else first_fact
    if relationship_mode == "deal_progression":
        subject = f"Next step on {name}"
        body = f"I saw active deal context for {name}. {second_fact}\n\nWould it be useful to compare notes on the open questions and align on the next practical step?"
    elif relationship_mode == "expansion":
        subject = f"Building on momentum at {name}"
        body = f"I noticed there may be momentum to build on at {name}. {second_fact}\n\nWould you be open to a short conversation about where adoption could go next?"
    else:
        subject = f"Quick idea for {name}"
        body = f"I noticed recent engagement from {name}. {first_fact}\n\nWould it be worth a brief conversation to see whether there is anything timely behind that interest?"
    return f"Subject: {subject}\n\n{greeting}\n\n{body}\n\nBest,\nYour Name"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Draft GTM outreach from DuckDB marts context.")
    parser.add_argument("account", nargs="?", help="Optional positional account name")
    parser.add_argument("--account", dest="account_flag", help="Account name")
    parser.add_argument("--prospect", help="Prospect full name or email")
    parser.add_argument("--db", default=DB_PATH, help="Path to DuckDB database")
    parser.add_argument("--show-schema", action="store_true", help="Print discovered marts tables")
    return parser.parse_args()


# Keep main linear: parse, connect, inspect, fetch context, build evidence, draft.
def main() -> None:
    args = parse_args()
    account_input = args.account_flag or args.account
    if not account_input and not args.prospect:
        raise SystemExit("Provide an account name or --prospect.")
    if not Path(args.db).exists():
        raise SystemExit(f"DuckDB database not found: {args.db}")

    connection = duckdb.connect(args.db, read_only=True)
    schema = inspect_schema(connection)
    require_tables(schema)
    if args.show_schema:
        print_schema(schema)

    columns = resolve_columns(schema)
    account, prospect = find_account_and_prospect(connection, columns, account_input, args.prospect)
    if not account:
        raise SystemExit("No matching account or prospect found.")

    context = gather_context(connection, columns, account, args.prospect)
    relationship_mode = detect_relationship_mode(context, columns)
    evidence = build_evidence(account, prospect, context, columns)
    email = draft_email(account_name(account, columns), prospect_name(prospect, columns, args.prospect), relationship_mode, evidence)

    print(f"Relationship mode: {relationship_mode}\n")
    print(email)
    print("\nEvidence used:")
    for index, item in enumerate(evidence, start=1):
        print(f"{index}. [{item['source']} row={item['row']}] {item['fact']}")


if __name__ == "__main__":
    main()
