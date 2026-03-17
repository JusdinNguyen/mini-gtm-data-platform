# Mini Data Platform — GTM Edition

This repo is a synthetic data platform containing mock GTM data — CRM records, sales call intelligence, marketing automation, and product analytics — along with Airflow DAGs, dbt models, Evidence dashboards, and a DuckDB data warehouse.

## Assignment

Build an agent that, given an account or prospect, pulls together relevant internal context — deal history, product usage, call intelligence, marketing engagement — and drafts a personalized outreach email. Try to discover the schema dynamically rather than hardcoding table and column names. No requirements around languages, model providers, or methods — we want to see how you think about these problems.

To submit, send us a link to your fork with a README outlining your approach and where you'd continue building if you had more time. This should take no more than a few hours.

We're looking forward to seeing your work!

## Quick Setup

Run the setup script to initialize everything:

```bash
./setup.sh
```

This will:
1. Generate synthetic GTM data (accounts, opportunities, stage history, contacts, contact roles, leads, calls, trackers, campaigns, activities, product users/events)
2. Initialize Airflow and load data into DuckDB
3. Run dbt transformations (staging → marts)

Then view the dashboards:

```bash
cd evidence
npm install       # First time only
npm run sources   # Build data sources
npm run dev       # Start dev server
# Open http://localhost:3000
```

---

## Manual Setup (Advanced)

<details>
<summary>Click to expand manual setup steps</summary>

### 1. Install dependencies

```bash
uv sync
```

### 2. Generate synthetic data

```bash
uv run python scripts/generate_all.py
```

### 3. Initialize Airflow

First, update `airflow/airflow.cfg` to use an absolute path for the database:

```bash
cd airflow
# Update sql_alchemy_conn in airflow.cfg to:
# sql_alchemy_conn = sqlite:////absolute/path/to/your/mini-data-platform-gtm/airflow/airflow.db

export AIRFLOW_HOME=$(pwd)
uv run airflow db migrate
```

### 4. Run ingestion DAGs

```bash
# From airflow/ directory
export AIRFLOW_HOME=$(pwd)
uv run python dags/ingest_accounts.py
uv run python dags/ingest_opportunities.py
uv run python dags/ingest_stage_history.py
uv run python dags/ingest_contacts.py
uv run python dags/ingest_contact_roles.py
uv run python dags/ingest_leads.py
uv run python dags/ingest_calls.py
uv run python dags/ingest_call_trackers.py
uv run python dags/ingest_campaigns.py
uv run python dags/ingest_lead_activities.py
uv run python dags/ingest_product_users.py
uv run python dags/ingest_product_events.py
```

### 5. Run dbt transformations

```bash
# From airflow/ directory
export AIRFLOW_HOME=$(pwd)
uv run python dags/run_dbt.py

# Or run dbt directly
cd ../dbt_project
uv run dbt build --profiles-dir .
```

</details>

## Project Structure

```
mini-data-platform-gtm/
├── sources/
│   └── postgres/             # All raw source data (CSV files)
├── airflow/
│   ├── dags/                 # Airflow DAGs for ingestion and transformation
│   │   ├── ingest_*.py       # Load data from sources → raw schema
│   │   ├── run_dbt.py        # Run dbt staging → marts pipeline
│   │   └── build_evidence.py # Build Evidence dashboards
│   └── utils/                # Shared utilities (warehouse.py)
├── warehouse/                # DuckDB database (data.duckdb)
├── dbt_project/              # dbt transformations
│   └── models/
│       ├── staging/          # Clean raw data (12 models)
│       └── marts/            # Analytics-ready tables (6 models)
├── evidence/                 # Evidence BI dashboards
│   ├── pages/                # Dashboard pages (pipeline, deals, funnel, forecast, adoption)
│   └── sources/              # SQL queries and DuckDB connection
└── scripts/                  # Data generation scripts
```

## Data Pipeline

### Raw Layer (`raw` schema)

- Loaded by Airflow ingestion DAGs
- 12 tables: accounts, opportunities, stage_history, contacts, contact_roles, leads, calls, call_trackers, campaigns, lead_activities, product_users, product_events

### Staging Layer (`staging` schema)

- Created by dbt
- 12 views with data cleaning (fix negatives, cap impossible values, filter nulls, remove future timestamps, deduplicate)

### Marts Layer (`marts` schema)

- Created by dbt
- 6 denormalized tables:
  - `dim_accounts` — Accounts enriched with pipeline stats, contact counts, segment classification
  - `dim_reps` — Sales rep dimension with win rate, pipeline, call activity metrics
  - `fct_opportunities` — Opportunities joined with account, call stats, call intelligence, multi-threading, lead attribution
  - `fct_calls` — Sales calls with opportunity/account context and tracker topic summaries
  - `fct_funnel` — Lead-to-close funnel with marketing attribution and engagement metrics
  - `fct_product_usage` — Account-level monthly product usage with feature adoption and engagement tiers

## Data Volumes

- **Raw**: ~130K total rows across 12 tables
- **Staging**: Same as raw (views with cleaning)
- **Marts**: ~1K dimension rows + ~40K fact rows
- **Database Size**: ~10-15 MB (DuckDB)

## Evidence Dashboards

The project includes interactive dashboards built with Evidence:

### Available Dashboards

1. **Pipeline Overview** (`/`) — Total pipeline, stage distribution, segment/region breakdown, monthly trends
2. **Deal Intelligence** (`/deals`) — Win/loss analysis, loss reasons, competitive intel from call trackers, call insights
3. **Full Funnel** (`/funnel`) — Lead-to-close conversion rates, channel ROI, marketing attribution, engagement analysis
4. **Forecast** (`/forecast`) — Forecast categories, weighted pipeline, rep commit analysis, quarterly trends
5. **Product Usage** (`/adoption`) — Product usage analytics, feature adoption, engagement tiers, usage vs revenue

### Running Evidence

```bash
cd evidence
npm install       # First time only
npm run sources   # Build data sources
npm run dev       # Start dev server
```

Then open http://localhost:3000 to view dashboards.

**Note**: Evidence connects to the DuckDB warehouse at `../warehouse/data.duckdb` and queries the `marts` and `staging` schemas through pass-through SQL files in `evidence/sources/warehouse/`.

### Building Evidence (Static Site)

```bash
# Using Airflow DAG
cd airflow
uv run python dags/build_evidence.py

# Or build directly
cd evidence
npm run build
```
