# Mini Data Platform — GTM Edition

This repo is a synthetic GTM data platform containing mock CRM records, sales call intelligence, marketing automation data, product analytics data, dbt models, Evidence dashboards, and a local DuckDB warehouse.

For this assignment, I added a GTM outreach agent under the `agent/` folder.

The agent takes an account or prospect input, pulls together relevant internal GTM context, chooses an explainable outreach angle, and drafts a personalized B2B sales email.

## Assignment

Build an agent that, given an account or prospect, pulls together relevant internal context, including:

- Deal history
- Product usage
- Call intelligence
- Marketing engagement

The agent should then draft a personalized outreach email.

The prompt also asked to try to discover the schema dynamically rather than hardcoding every table and column name.

## Added Agent

The outreach agent lives here:

```text
agent/
```

Main entry point:

```text
agent/main.py
```

Detailed agent documentation:

```text
agent/README.md
```

## Quick Start

### 1. Install dependencies

This project uses `uv`.

```bash
uv add duckdb openai
```

The minimum required dependencies are:

```txt
duckdb
openai
```

They are also listed in:

```text
requirements.txt
```

### 2. Make sure the DuckDB warehouse exists

The agent expects the local DuckDB database to exist at:

```text
warehouse/data.duckdb
```

### 3. Run without an OpenAI API key

The agent can run without an API key by using a deterministic fallback template.

```bash
unset OPENAI_API_KEY
uv run python -m agent.main "Pacific Analytics"
```

Expected message:

```text
No OPENAI_API_KEY found, using template draft.
```

### 4. Run with OpenAI

To use the LLM drafting path:

```bash
export OPENAI_API_KEY="your-api-key-here"
export OPENAI_MODEL="gpt-4.1"
uv run python -m agent.main "Pacific Analytics"
```

Expected message:

```text
Using LLM draft.
Using OpenAI model: gpt-4.1
```

## Demo Commands

Exact account lookup:

```bash
uv run python -m agent.main "Pacific Analytics"
```

Partial account lookup:

```bash
uv run python -m agent.main "Pacific"
```

Prospect email lookup:

```bash
uv run python -m agent.main "sarah.lopez4473@scaleupsystems.com"
```

Fake account test:

```bash
uv run python -m agent.main "notarealcompany123"
```

## Agent Summary

The agent follows this flow:

```text
User input
→ Resolve input into an account
→ Pull GTM context from DuckDB
→ Choose an outreach angle
→ Build evidence facts
→ Draft a personalized email
→ Print the result
```

The core agent files are:

```text
agent/main.py
agent/resolver.py
agent/database.py
agent/schema.py
agent/context.py
agent/rules.py
agent/drafter.py
agent/models.py
```

## Design Summary

I intentionally kept retrieval and outreach decision logic outside of the LLM.

Python handles:

- Account resolution
- Database queries
- Schema inspection
- Evidence selection
- Outreach angle selection

The LLM is only used for the final email drafting step.

This makes the agent easier to debug, easier to explain, and safer to run. If no API key is available, the agent still works using a fallback template.

## More Details

For the full explanation of the agent implementation, file responsibilities, schema discovery, outreach rules, limitations, and future work, see:

```text
agent/README.md
```
