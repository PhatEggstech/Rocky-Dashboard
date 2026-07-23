# Rocky Lens Datalake Pipeline

Bronze → Silver → Gold lakehouse pipeline for HMK (Rocky) analytics.

## Architecture

```
POS PostgreSQL (255 tables) → extract.py → bronze.* (warehouse PG)
                                         → MinIO (Parquet archive)
bronze.* → silver SQL transforms → silver.* (aggregated marts)
silver.* → gold SQL transforms   → gold.* (API-ready, mirrors SQLite)
```

## Directory Structure

```
datalake/
├── ddl/          # Schema DDL (run in order: 001, 002, ...)
├── sql/
│   ├── bronze/   # POS → bronze extraction SQL
│   ├── silver/   # bronze → silver aggregation SQL
│   └── gold/     # silver → gold passthrough SQL
├── lib/
│   ├── extract.py    # POS extraction logic
│   ├── loader.py     # MinIO Parquet archive
│   └── transform.py  # Execute silver/gold SQL
└── scripts/
    └── run_pipeline.py  # CLI entrypoint
```

## Quick Start

```bash
# Set environment variables
export WAREHOUSE_PG_DSN="postgresql://user:password@localhost:5433/hmk_warehouse"
export POS_PG_DSN="postgresql://..."

# Initialize warehouse schemas
python -m datalake.scripts.run_pipeline init

# Run full pipeline
python -m datalake.scripts.run_pipeline full

# Run only silver/gold
python -m datalake.scripts.run_pipeline silver
python -m datalake.scripts.run_pipeline gold
```

## Docker

```bash
docker compose up warehouse-pg minio -d
```

Warehouse PG: `localhost:5433` (user: hmk, pass: hmk_warehouse, db: hmk_warehouse)
MinIO: `localhost:9000` (console: `localhost:9001`, user: minioadmin)

## Naming Conventions

- Bronze SQL: `b_<table>.sql`
- Silver SQL: `s_00_dim_*.sql` (dims first), `s_daily_*.sql`, `s_monthly_*.sql`
- Gold SQL: `g_00_*.sql` (passthrough), `g_*.sql`
- All columns: snake_case
- Idempotency: `INSERT ... ON CONFLICT DO UPDATE`
