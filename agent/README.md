# GTM Outreach Agent

A lightweight GTM outreach agent built on top of the Mini GTM Data Platform.

The agent takes an account or prospect input, pulls together relevant internal GTM context from the local DuckDB warehouse, chooses an explainable outreach angle, and drafts a personalized B2B sales email.

The main question the agent tries to answer is:

> Why should a seller reach out to this account right now?

## Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/JusdinNguyen/mini-gtm-data-platform.git
cd mini-gtm-data-platform
```

### 2. Install dependencies

This project uses `uv`.

```bash
uv add duckdb openai
```

The minimum required dependencies are also listed in `requirements.txt`:

```txt
duckdb
openai
```

Alternatively, install with pip:

```bash
pip install -r requirements.txt
```

### 3. Make sure the DuckDB warehouse exists

The agent expects the DuckDB database to exist at:

```text
warehouse/data.duckdb
```

If the database has not been generated yet, run the original project setup:

```bash
./setup.sh
```

### 4. Run the agent without an OpenAI API key

The agent works without an API key by using a deterministic fallback template.

```bash
unset OPENAI_API_KEY
uv run python -m agent.main "Pacific Analytics"
```

You should see:

```text
No OPENAI_API_KEY found, using template draft.
```

### 5. Run the agent with OpenAI

To use the LLM email drafter, set your OpenAI API key and model:

```bash
export OPENAI_API_KEY="your-api-key-here"
export OPENAI_MODEL="gpt-4.1"
```

Then run:

```bash
uv run python -m agent.main "Pacific Analytics"
```

You should see:

```text
Using LLM draft.
Using OpenAI model: gpt-4.1
```

### 6. Try different input types

Exact account name:

```bash
uv run python -m agent.main "Pacific Analytics"
```

Partial account name:

```bash
uv run python -m agent.main "Pacific"
```

Prospect email:

```bash
uv run python -m agent.main "sarah.lopez4473@scaleupsystems.com"
```

If a partial name matches multiple accounts, the resolver prints the possible matches and asks the user to be more specific instead of guessing.

## Assignment

The assignment was to build an agent that, given an account or prospect, pulls together relevant internal context such as deal history, product usage, call intelligence, and marketing engagement, then drafts a personalized outreach email.

The assignment also asked to try to discover the schema dynamically rather than hardcoding all table and column names.

## My Approach

My approach has four main steps:

1. Resolve the user input into an account.
2. Gather internal GTM context from the DuckDB warehouse.
3. Choose an explainable outreach angle using rules.
4. Draft a personalized outreach email using either an LLM or a fallback template.

I intentionally kept the retrieval and outreach decision logic outside of the LLM. Python handles account resolution, database queries, evidence selection, and outreach angle selection. The LLM is only used for drafting the final email from already-selected evidence.

This makes the agent more predictable, easier to debug, and easier to explain.

## How the Agent Works

The agent follows this flow:

```text
Input account name, partial account name, or prospect email
→ Resolve the input into an account
→ Retrieve account, opportunity, call, product usage, and funnel context
→ Interpret deal status, usage level, lead warmth, and call signals
→ Choose the strongest outreach angle
→ Build evidence facts from the database
→ Draft a personalized email
→ Print the email plus the evidence used
```

The possible outreach angles are:

```text
open opportunity follow-up
expansion
re-engagement
adoption support
warm prospect outreach
general account outreach
```

## Project Structure

```text
agent/
├── __init__.py
├── main.py
├── resolver.py
├── database.py
├── schema.py
├── context.py
├── rules.py
├── drafter.py
└── models.py
```

## File Responsibilities

### `main.py`

Entry point for the CLI.

It reads the user input, connects to DuckDB, inspects the schema, resolves the input into an account, gathers context, applies rules, drafts the email, and prints the output.

### `resolver.py`

Resolves user input into an account.

It currently supports:

```text
exact account names
partial account names
prospect emails from fct_funnel
```

If a partial input is ambiguous, the resolver prints possible account matches and asks the user to be more specific instead of randomly picking one.

### `database.py`

Contains reusable DuckDB helper functions.

It handles opening a read-only database connection and fetching one or many rows from SQL queries.

### `schema.py`

Handles light schema discovery.

It inspects `information_schema.columns` to learn which tables and columns exist in the `marts` schema, then provides helpers to find likely tables and columns.

### `context.py`

Retrieves the internal GTM context for a resolved account.

It gathers data from:

```text
dim_accounts
fct_opportunities
fct_calls
fct_funnel
fct_product_usage
```

### `rules.py`

Chooses the outreach angle.

It uses a simple priority order to decide whether the email should focus on an open opportunity, expansion, re-engagement, adoption support, warm prospect outreach, or general outreach.

It also builds evidence facts explaining why the decision was made.

### `drafter.py`

Drafts the email.

If `OPENAI_API_KEY` is set, the agent uses OpenAI to draft a more natural email. If no API key is available, it uses a deterministic fallback template.

### `models.py`

Defines shared data structures used by the agent, including:

```text
EvidenceFact
EmailDraft
AgentResult
```

## Schema Discovery

The agent uses light dynamic schema discovery.

Instead of hardcoding every exact table and column name, `schema.py` inspects DuckDB metadata with `information_schema.columns`.

For example, the agent can look for a table related to accounts and then find a likely account name column from options such as:

```text
name
account_name
company
company_name
```

The current version still assumes the cleaned GTM data lives in the `marts` schema, which is reasonable because the repo’s dbt models produce analytics-ready marts tables.

Given more time, I would make the resolver more dynamic by searching more candidate columns and scoring possible matches.

## Data Sources

### `dim_accounts`

Used to understand who the company is.

Useful fields include:

```text
account_id
name
industry
arr
segment
region
owner_id
```

This table acts as the anchor for the rest of the account context. The `account_id` connects the account to opportunities, calls, product usage, and funnel activity.

ARR is used as supporting context, but it does not decide the outreach angle by itself.

### `fct_opportunities`

Used to understand active or past sales deals.

Useful fields include:

```text
opp_name
stage
amount
is_closed
is_won
next_step
forecast_category
opportunity_type
pricing_mentions
risk_mentions
buying_signal_mentions
```

This table is the strongest signal for active sales motion.

If an account has an open opportunity, the agent prioritizes a deal follow-up email.

### `fct_calls`

Used to understand recent sales conversations.

Useful fields include:

```text
call_date
call_type
disposition
next_steps_mentioned
pricing_mentions
risk_mentions
security_mentions
buying_signal_mentions
objection_mentions
technical_mentions
```

Call data can help adjust tone and personalization.

For example, pricing mentions may suggest a value-focused message, while risk or objection mentions may suggest a more careful and supportive message.

### `fct_product_usage`

Used to understand product engagement.

Useful fields include:

```text
usage_month
active_users
total_events
unique_features_used
usage_trend_pct
engagement_tier
```

Product usage helps the agent identify expansion, adoption support, or re-engagement opportunities.

High usage can suggest expansion potential. Low or declining usage can suggest that the account may need support.

### `fct_funnel`

Used to understand lead, prospect, and campaign activity.

Useful fields include:

```text
lead_score
lead_source
lead_status
company
is_converted
campaigns_touched
first_campaign_name
first_campaign_channel
reached_mql
reached_sql
reached_opportunity
```

Funnel data helps identify warm prospects and campaign context.

A high lead score can trigger warm prospect outreach if there is no stronger opportunity or product usage signal.

## Outreach Decision Logic

The agent intentionally uses a simple priority order.

It does not try to use every column from every table. Instead, it looks for the strongest reason to contact the account right now.

### Priority Order

```text
open opportunity → follow-up
high usage → expansion
declining usage → re-engagement
low usage → adoption support
high lead score → warm prospect outreach
fallback → general outreach
```

### 1. Open Opportunity Follow-Up

If the account has an active sales opportunity, the agent prioritizes a deal follow-up email.

This is the highest-priority signal because there is already an active sales motion.

Example:

```text
Pacific Analytics - New Business
Stage: Qualification
Next step: Reference call
```

### 2. Expansion

If there is no open opportunity, but the latest product usage shows high engagement, the agent chooses an expansion angle.

High usage can suggest that the account may be ready for a larger plan, upgrade, or broader rollout.

### 3. Re-Engagement

If product usage is declining, the agent chooses a re-engagement angle.

Declining usage can mean the account may need help, attention, or a reason to re-engage with the product.

### 4. Adoption Support

If product usage is low, the agent chooses an adoption support angle.

Low usage can suggest that the account may need onboarding help, enablement, or guidance on getting more value from the product.

### 5. Warm Prospect Outreach

If there is no strong opportunity or product usage signal, but a related lead has a high lead score, the agent chooses a warm prospect outreach angle.

For this first version, a lead score of 75 or higher is treated as a warm lead.

In a production version, this threshold could be tuned using historical conversion data.

### 6. General Account Outreach

If none of the above signals are present, the agent falls back to a general account outreach angle.

## Evidence Selection

The agent chooses only a few strong evidence points.

Evidence should come from the database, not guesses.

Good evidence examples include:

```text
open opportunity stage and next step
recent call mentions of pricing, risk, or buying signals
product usage tier or usage trend
lead score or campaign source
account industry, segment, or ARR
```

The email should not mention every available data point. The best email should feel specific but not overloaded.

## LLM and Template Modes

The agent can run in two modes.

### LLM Mode

If `OPENAI_API_KEY` is set, the agent uses OpenAI to draft the email.

```bash
export OPENAI_API_KEY="your-api-key-here"
export OPENAI_MODEL="gpt-4.1"
uv run python -m agent.main "Pacific Analytics"
```

Expected terminal output:

```text
Using LLM draft.
Using OpenAI model: gpt-4.1
```

### Template Mode

If `OPENAI_API_KEY` is not set, the agent uses a deterministic fallback template.

```bash
unset OPENAI_API_KEY
uv run python -m agent.main "Pacific Analytics"
```

Expected terminal output:

```text
No OPENAI_API_KEY found, using template draft.
```

This makes the project easy to demo even without API access.

## Example Output

Command:

```bash
uv run python -m agent.main "Pacific Analytics"
```

Example output:

```text
Using LLM draft.
Using OpenAI model: gpt-4.1
Account: Pacific Analytics
Outreach angle: open opportunity follow-up

Evidence:
- [marts.dim_accounts] Pacific Analytics is a SMB account in Energy with $6543 ARR.
- [marts.fct_opportunities] There is an open opportunity called Pacific Analytics - New Business in the Qualification stage worth $42338. The next step is: Reference call.

Subject: Next Steps for Pacific Analytics - New Business

Hi there,

I saw your Pacific Analytics - New Business opportunity is in the Qualification stage, and the next step is a reference call. Let’s get this scheduled so you have everything you need to move forward.

Please reply with a few times that work for you, or let me know if there’s anything specific you want to cover on the call.

Looking forward to hearing from you.

Best,
Justin
```

## Demo Examples

Exact account lookup:

```bash
uv run python -m agent.main "Pacific Analytics"
```

Ambiguous partial account lookup:

```bash
uv run python -m agent.main "Pacific"
```

This prints multiple possible matches and asks the user to be more specific.

Prospect email lookup:

```bash
uv run python -m agent.main "sarah.lopez4473@scaleupsystems.com"
```

This searches the funnel table by email, resolves the converted account, and then runs the normal outreach workflow.

## Design Choices

### Controlled LLM Usage

I intentionally kept retrieval and outreach decision logic outside of the LLM.

Python handles account resolution, database queries, evidence selection, and outreach angle selection. The LLM is only used for drafting the final email from already-selected evidence.

This makes the agent more predictable and easier to debug.

### Rules Before Drafting

The agent chooses an outreach angle before drafting the email.

This keeps the business decision separate from the writing step. For example, an open opportunity should clearly take priority over product usage or funnel activity.

### Evidence-Based Output

The agent prints the evidence used for the draft.

This makes the result more transparent because a reviewer can see which database facts influenced the email.

### LLM With Fallback Template

The LLM makes the email sound more natural, but the agent still works without an API key.

This makes the project easier to run locally, demo, and grade.

### Simple CLI

The first version runs as a command-line tool.

This keeps the project focused on the core agent workflow instead of spending time on UI or integrations.

## Limitations

- The resolver supports exact account names, partial account names, and prospect emails, but it is still a simple first version.
- The resolver does not yet support full person-name lookup, account IDs, lead IDs, or embedding-based fuzzy matching.
- The fallback template is less natural than the LLM draft.
- The LLM may occasionally word evidence too strongly, so the prompt includes guardrails against inventing facts.
- The lead score threshold is a simple heuristic.
- The current version prints the email instead of saving it to Gmail or a CRM.

## Next Steps

If I had more time, I would add:

- Stronger input resolution for person names, account IDs, lead IDs, and fuzzy company matching.
- Candidate scoring and disambiguation when multiple accounts match.
- Embedding-based similarity search for better partial matching.
- More advanced use of sales call intelligence for tone and personalization.
- A retrieval pipeline over past successful outreach emails so the drafting step can learn from examples.
- Stronger evaluation using historical opportunity outcomes.
- Configurable rule thresholds, such as the lead score cutoff.
- CRM or Gmail integration so drafted emails could be saved directly as drafts.
- A human review workflow so sellers can approve or edit emails before sending.
- A simple UI where users can search accounts, inspect evidence, and copy or approve the draft.
- More precise prompt controls to avoid mentioning internal-only fields such as ARR in customer-facing emails.