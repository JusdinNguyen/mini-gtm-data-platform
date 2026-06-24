# GTM Outreach Agent

A simple Python agent that drafts personalized B2B outreach emails from the Mini GTM Data Platform DuckDB warehouse.

Given an account or prospect, the agent gathers internal GTM context from accounts, opportunities, calls, funnel activity, and product usage. It then drafts a short outreach email and prints the evidence used so the output can be checked.

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

The repo already provides a DuckDB warehouse with raw, staging, and marts schemas. I used the `marts` layer as the source of truth because those tables are already cleaned, joined, and modeled for business analysis through dbt.

The agent uses these documented marts tables:

```text
marts.dim_accounts
marts.fct_opportunities
marts.fct_calls
marts.fct_funnel
marts.fct_product_usage
```

I intentionally hardcoded the table names because the repo README clearly documents these marts tables and their roles. Fully discovering table roles dynamically would add complexity without much payoff for a short take-home.

For columns, the agent does use schema discovery. It reads `information_schema.columns`, then resolves the important column names before building queries. This keeps the code more flexible than fully hardcoding every table and column name while still keeping the implementation readable.

The flow is:

```text
1. Connect to DuckDB
2. Inspect the marts schema
3. Resolve important column names
4. Find the account or prospect
5. Gather opportunities, calls, funnel activity, and product usage
6. Detect the relationship mode
7. Build a short evidence list
8. Draft the email from the evidence
9. Print the email and supporting evidence
```

## Relationship modes

The agent uses simple deterministic rules to decide the email angle.

`deal_progression`: used when the account has an open opportunity. The email focuses on moving the deal forward.

`expansion`: used when the account has closed-won history or meaningful product usage. The email focuses on building on existing momentum.

`cold_outreach`: used when there is no clear open deal or expansion signal. The email uses lighter funnel or marketing engagement context.

## Design choices

I kept the default email drafting deterministic and local. There is no OpenAI API key required to run the project.

I chose this because the most important part of the assignment is retrieving the right internal context and grounding the email in that context. The evidence list is printed under the email so the reviewer can verify where the claims came from.

An LLM drafting step could be added later using the same evidence list as the prompt input.

## Tradeoffs and next steps

With more time, I would continue building in these areas:

- Add optional LLM drafting with the evidence list as the prompt input
- Improve prospect-to-account matching for leads that do not map cleanly to `dim_accounts`
- Add semantic search over call transcripts or call summaries
- Rank evidence by recency, deal stage, product usage strength, and sales urgency
- Add factuality checks to make sure every email claim is supported by retrieved evidence
- Add a sales rep approval workflow before sending emails

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
