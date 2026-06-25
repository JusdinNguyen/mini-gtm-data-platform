# GTM Outreach Agent

This folder contains the GTM outreach agent built for the Mini Data Platform take-home assignment.

The agent takes an account or prospect input, pulls together relevant internal GTM context from the local DuckDB warehouse, chooses an explainable outreach angle, and drafts a personalized B2B sales email.

The main question the agent tries to answer is:

> Why should a seller reach out to this account right now?

## How to Run

From the project root:

```bash

uv run python -m agent.main "Pacific Analytics"

```

Run with a prospect email:

```bash

uv run python -m agent.main "sarah.lopez4473@scaleupsystems.com"

```

Run with a partial account name:

```bash

uv run python -m agent.main "Pacific"

```

If the partial input matches multiple accounts, the resolver prints the possible matches and asks the user to be more specific instead of guessing.

## Agent Flow

```text

Input account name, partial account name, or prospect email

→ resolver.py resolves the input into an account

→ context.py pulls internal GTM context

→ rules.py chooses the outreach angle

→ drafter.py drafts the email

→ main.py prints the evidence and final email

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

├── models.py

├── requirements.txt

└── README.md

```

## File Responsibilities

### `main.py`

The CLI entry point.

It reads the user input, connects to DuckDB, inspects the schema, resolves the input into an account, gathers context, applies outreach rules, drafts the email, and prints the result.

### `resolver.py`

Resolves user input into an account.

It currently supports:

- Exact account names

- Partial account names

- Prospect emails from `fct_funnel`

For email input, it searches the funnel table, finds the `converted_account_id`, and maps that back to the account table.

For partial account names, it returns the account only if there is one clear match. If there are multiple matches, it asks the user to be more specific.

### `database.py`

Contains reusable DuckDB helper functions.

It opens the local DuckDB database in read-only mode and provides helper functions for fetching one row or many rows.

### `schema.py`

Handles light schema discovery.

It inspects `information_schema.columns` to learn which tables and columns exist in the `marts` schema.

This helps the agent find tables and columns without hardcoding every exact name.

For example, the agent can look for a table containing `"account"` and a column matching one of:

```text

name

account_name

company

company_name

```

### `context.py`

Retrieves business context for the resolved account.

It gathers data from:

- `dim_accounts`

- `fct_opportunities`

- `fct_calls`

- `fct_funnel`

- `fct_product_usage`

This file only retrieves data. It does not decide the outreach strategy and does not write the email.

### `rules.py`

Chooses the outreach angle.

The rules are intentionally simple and explainable. The goal is to identify the strongest reason to contact the account right now.

Priority order:

```text

open opportunity follow-up

expansion

re-engagement

adoption support

warm prospect outreach

general account outreach

```

### `drafter.py`

Drafts the email.

If `OPENAI_API_KEY` is available, it uses OpenAI to draft a more natural email.

If no API key is available, it uses a deterministic fallback template.

### `models.py`

Defines shared data structures, including:

- `EvidenceFact`

- `EmailDraft`

- `AgentResult`

## Schema Discovery

The assignment asked to try to discover the schema dynamically rather than hardcoding table and column names.

This agent uses light dynamic schema discovery by querying DuckDB metadata:

```sql

SELECT table_name, column_name

FROM information_schema.columns

WHERE table_schema = 'marts'

ORDER BY table_name, ordinal_position

```

The agent then uses helper functions to find likely tables and columns.

For example:

```text

find_table(schema, "account")

find_column(schema, accounts_table, ["name", "account_name", "company"])

```

This means the agent does not need to hardcode every exact column name, although it still assumes the cleaned GTM data lives in the `marts` schema.

That assumption is reasonable for this project because the dbt models create analytics-ready marts tables.

## Data Sources Used

### `dim_accounts`

Used for account-level details such as:

- Account name

- Industry

- Segment

- Region

- ARR

- Account ID

### `fct_opportunities`

Used for sales deal context such as:

- Opportunity name

- Stage

- Amount

- Close status

- Next step

- Forecast category

- Buying signals

- Pricing mentions

- Risk mentions

If an account has an open opportunity, the agent prioritizes a deal follow-up email.

### `fct_calls`

Used for sales call intelligence such as:

- Call date

- Call type

- Disposition

- Next steps mentioned

- Pricing mentions

- Risk mentions

- Security mentions

- Buying signals

- Objections

- Technical mentions

### `fct_product_usage`

Used for product engagement context such as:

- Usage month

- Active users

- Total events

- Unique features used

- Usage trend

- Engagement tier

Product usage helps the agent identify expansion, re-engagement, or adoption support opportunities.

### `fct_funnel`

Used for marketing and prospect engagement such as:

- Lead score

- Lead source

- Lead status

- Campaigns touched

- Conversion status

- Converted account ID

This allows the agent to support prospect email input and warm prospect outreach.

## Outreach Decision Logic

The agent uses a simple priority order.

### 1. Open Opportunity Follow-Up

If the account has an open opportunity, the agent chooses:

```text

open opportunity follow-up

```

This is the highest-priority signal because there is already an active sales motion.

### 2. Expansion

If there is no open opportunity but product engagement is high, the agent chooses:

```text

expansion

```

High usage can suggest the account may be ready for broader adoption or expansion.

### 3. Re-Engagement

If product usage is declining, the agent chooses:

```text

re-engagement

```

Declining usage can suggest the account may need attention or support.

### 4. Adoption Support

If product engagement is low, the agent chooses:

```text

adoption support

```

Low usage can suggest onboarding gaps, workflow blockers, or underused product value.

### 5. Warm Prospect Outreach

If there is no stronger deal or usage signal, but a related lead has a high lead score, the agent chooses:

```text

warm prospect outreach

```

The current warm lead threshold is:

```text

75

```

### 6. General Account Outreach

If none of the above signals are present, the agent falls back to:

```text

general account outreach

```

## Evidence-Based Drafting

The agent creates `EvidenceFact` objects to explain why an outreach angle was selected.

Example evidence:

```text

Pacific Analytics is a SMB account in Energy with $6543 ARR.

There is an open opportunity called Pacific Analytics - New Business in the Qualification stage. The next step is: Reference call.

```

The evidence is printed before the email so the reviewer can see what facts influenced the draft.

The email should not mention every internal detail. The evidence is used to ground the draft, but the email should stay concise and natural.

## LLM and Template Modes

### LLM Mode

If `OPENAI_API_KEY` is set, the agent uses OpenAI:

```bash

export OPENAI_API_KEY="your-api-key-here"

export OPENAI_MODEL="gpt-4.1"

uv run python -m agent.main "Pacific Analytics"

```

Expected output:

```text

Using LLM draft.

Using OpenAI model: gpt-4.1

```

### Template Mode

If `OPENAI_API_KEY` is not set, the agent uses a fallback template:

```bash

unset OPENAI_API_KEY

uv run python -m agent.main "Pacific Analytics"

```

Expected output:

```text

No OPENAI_API_KEY found, using template draft.

```

This makes the project runnable without API access.

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

Subject: Next Steps for Pacific Analytics

Hi there,

I saw that the Pacific Analytics - New Business opportunity is in Qualification, with a reference call listed as the next step.

I can help make sure that call is useful and aligned with what your team needs before moving forward.

Would Tuesday or Wednesday work to get that reference call scheduled?

Best,

Justin

```

## Design Choices

### Controlled LLM Usage

I intentionally kept retrieval and outreach decision logic outside of the LLM.

Python handles:

- Input resolution

- Database queries

- Schema inspection

- Evidence selection

- Outreach angle selection

The LLM is only used to turn selected evidence into a natural email.

This makes the system easier to debug and easier to explain.

### Explainable Rules

I used rules for the outreach strategy because the decision should be predictable.

For example, if there is an open opportunity, that should clearly take priority over product usage or marketing activity.

### Fallback Template

The agent works even without an OpenAI API key.

This makes the project easier to run locally and easier to grade.

### Flat Structure for the Take-Home

The current `agent/` package uses a flat file structure because the project is small and easier to review in a take-home assignment.

Given more time, I would reorganize it into responsibility-based modules:

```text

agent/

├── main.py

├── database.py

├── models.py

├── retrieval/

│   ├── schema.py

│   ├── resolver.py

│   └── context.py

├── strategy/

│   └── rules.py

└── drafting/

    └── drafter.py

```

I kept the current version flat to avoid unnecessary complexity during the take-home, but this would be one of the first refactors I would make before expanding the agent further.

## Limitations

- The resolver supports exact account names, partial account names, and prospect emails, but it is still a simple first version.

- The resolver does not yet support full person-name lookup, account IDs, lead IDs, or embedding-based fuzzy matching.

- The schema discovery is light and still assumes cleaned GTM data lives in the `marts` schema.

- The lead score threshold is a simple heuristic.

- The fallback template is less natural than the LLM draft.

- The current version prints the email instead of saving it to a CRM or Gmail draft.

## Future Work

Given more time, I would add:

- Stronger fuzzy matching for account and prospect resolution

- Person-name, account ID, and lead ID lookup

- Candidate scoring and disambiguation

- Embedding-based similarity search

- More advanced use of call intelligence for tone and personalization

- A retrieval pipeline over past successful outreach emails

- Configurable rule thresholds

- CRM or Gmail draft integration

- A human review workflow before sending

- A simple UI for searching accounts and reviewing evidence