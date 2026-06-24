# GTM Outreach Agent

This is a Python agent that drafts personalized B2B outreach emails using the Mini GTM Data Platform DuckDB warehouse.

The goal of the agent is to take an account or prospect, pull together the most relevant GTM context, and turn that context into a short outreach email. It uses account data, opportunities, sales calls, funnel activity, and product usage. The agent also prints the evidence it used, so the email can be checked instead of treated like a black box.

## Quick start

First, fork the original assignment repo:

```text
https://github.com/astronomer/mini-gtm-data-platform
```

This submission was built in my fork:

```text
https://github.com/JusdinNguyen/mini-gtm-data-platform
```

Clone the fork and move into the repo:

```bash
git clone https://github.com/JusdinNguyen/mini-gtm-data-platform.git
cd mini-gtm-data-platform
```

Run the project setup if the DuckDB warehouse has not been created yet:

```bash
./setup.sh
```

This generates the synthetic GTM data, loads it into DuckDB, and runs the dbt transformations. After setup, the warehouse should exist at:

```text
warehouse/data.duckdb
```

Install the agent dependency if needed:

```bash
uv pip install -r agent/requirements.txt
```

Run the outreach agent with an account:

```bash
uv run python agent/gtm_agent.py --account "Velocity Solutions" --show-schema
```

Run the outreach agent with a prospect:

```bash
uv run python agent/gtm_agent.py --prospect "john.garcia135@techflowinc.com"
```

## Example output

```text
Relationship mode: deal_progression

Subject: Next step on Velocity Solutions

Hi there,

I saw active deal context for Velocity Solutions. Open opportunity 'Velocity Solutions - Platform Deal' is in Prospecting for $235,033; next step is Reference call.

Would it be useful to compare notes on the open questions and align on the next practical step?

Best,
Your Name

Evidence used:
1. [marts.dim_accounts row=1] Velocity Solutions is a Mid-Market account in Education with $130,412 ARR.
2. [marts.fct_opportunities row=2,671] Open opportunity 'Velocity Solutions - Platform Deal' is in Prospecting for $235,033; next step is Reference call.
3. [marts.fct_product_usage row=1:2025-01-01] Latest product usage shows 1 active users, 12 events, 6 features used, and engagement tier Occasional.
4. [marts.fct_calls row=4,563] On 2024-12-30, a QBR call had 0 buying-signal mentions, 1 pricing mentions, 3 risk mentions, and next steps mentioned: no.
```

## Approach

The repo already provides a DuckDB warehouse with raw, staging, and marts schemas. I used the `marts` layer as the source of truth because those tables are already cleaned and modeled for GTM analysis.

The agent uses these marts tables:

```text
marts.dim_accounts
marts.fct_opportunities
marts.fct_calls
marts.fct_funnel
marts.fct_product_usage
```

I kept the table names fixed because the repo README already documents these marts and what they are used for. For a short take-home, that felt like the right tradeoff. Fully discovering table roles dynamically would make the project more complex without making the agent much better.

For columns, the agent does use schema discovery. It reads from `information_schema.columns` and resolves the important column names before building queries. This keeps the code flexible while still being easy to follow.

The basic flow is:

```text
1. Connect to DuckDB
2. Inspect the marts schema
3. Resolve the columns the agent needs
4. Find the account or prospect
5. Pull context from opportunities, calls, funnel activity, and product usage
6. Choose the outreach angle
7. Build a short evidence list
8. Draft the email from that evidence
9. Print the email and the supporting evidence
```

## Relationship modes

The agent uses a few simple rules to decide the email angle.

`deal_progression`: used when the account has an open opportunity. The email focuses on moving the deal forward.

`expansion`: used when the account has closed-won history or meaningful product usage. The email focuses on building on existing momentum.

`cold_outreach`: used when there is no clear open deal or expansion signal. The email uses lighter funnel or marketing engagement context.

## Design choices

I kept the email drafting deterministic and local by default. There is no OpenAI API key required to run the project.

I made that choice because the main challenge is not just generating an email. The more important part is finding the right internal context and grounding the email in that context. The evidence list makes the output easier to review and helps prevent unsupported claims.

An LLM drafting step could be added later using the same evidence list as the prompt input.

## Tradeoffs and next steps

With more time, I would keep building in these areas:

- Add optional LLM drafting with the evidence list as the prompt input
- Improve prospect-to-account matching. Today, if a prospect has a company name but does not cleanly map to a full `dim_accounts` record, the agent can still draft from funnel evidence, but some account fields may appear as `unknown`.
- Add semantic search over call transcripts or call summaries
- Rank evidence by recency, deal stage, product usage strength, and sales urgency
- Add checks to make sure every email claim is supported by retrieved evidence
- Add a sales rep review step before any email is sent

## Tested examples

I tested the agent with:

```bash
uv run python agent/gtm_agent.py --account "Velocity Solutions" --show-schema
```

```bash
uv run python agent/gtm_agent.py --account "Fusion Solutions"
```

```bash
uv run python agent/gtm_agent.py --prospect "john.garcia135@techflowinc.com"
```

These tests confirmed that the agent works with both account and prospect input, retrieves GTM context from the warehouse, drafts an email, and prints the supporting evidence.
