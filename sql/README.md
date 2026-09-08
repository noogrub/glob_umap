# PostgreSQL setup

These scripts create the catalogue-level database structure described in
`database_design.md`.

## Requirements

- PostgreSQL role `gc` with login permission
- database name `gc_ml`
- password stored outside the repository, preferably in `.pgpass`
- `PGDATABASE`, `PGUSER`, `PGHOST`, and `PGPORT` set in the environment

Create the login role interactively if it does not already exist:

```bash
createuser --login --pwprompt gc
```

The command may require a PostgreSQL administrator login appropriate to the
local installation.

## Create the database

Run the database script while connected to an administrative database:

```bash
psql --dbname=postgres --file=sql/00_database.sql
```

The script verifies that role `gc` exists, then creates `gc_ml` when needed.
It does not store or change the role password.

## Create the tables

Connect as `gc` to `gc_ml` and apply the schema:

```bash
psql --file=sql/apply.sql
```

`apply.sql` creates the `raw`, `core`, and `ml` schemas in one transaction and
then verifies that every expected table exists.

## Lock the raw catalogues

After successful ingestion and audit, run the lock script as the PostgreSQL
administrator. The shell opens the file before `sudo`, so the `postgres` OS
account does not need access to the project directory:

```bash
sudo -u postgres psql --dbname=gc_ml < sql/50_lock_raw.sql
```

The script creates the `NOLOGIN` role `gc_raw_owner`, transfers ownership of
the `raw` schema and tables to it, and grants `gc` only `USAGE` and `SELECT`.
Normal project sessions can then read raw data but cannot insert, update,
delete, truncate, or alter it. A PostgreSQL administrator can deliberately
reverse the ownership and grants if the raw layer must be rebuilt.

## Audit the source contract

First verify the source files themselves:

```bash
glob-umap preflight --config config/datasets/fornax.yaml
```

Then verify the database rows, catalogue registrations, contiguous source-row
keys, owners, and privileges:

```bash
psql --file=sql/91_audit_raw.sql
```

Every `source_contract_ok`, `gc_can_select`, and `gc_write_locked` value should
be true. `gc_can_create` and every `gc_raw_owner` capability should be false.

## File order

| File | Purpose |
|---|---|
| `00_database.sql` | Create `gc_ml` with owner `gc` |
| `10_schemas.sql` | Create and protect the three schemas |
| `20_raw.sql` | Create source-faithful catalogue staging tables |
| `30_core.sql` | Create normalized astronomical tables |
| `40_ml.sql` | Create samples, runs, embeddings, metrics, and artifacts |
| `50_lock_raw.sql` | Transfer raw ownership and grant `gc` read-only access |
| `90_verify.sql` | Verify the expected tables and list them |
| `91_audit_raw.sql` | Audit raw source lineage, ownership, and permissions |
| `apply.sql` | Apply the schema files in order |

The files are safe to re-run for initial creation. `IF NOT EXISTS` does not
upgrade an older table definition. Later schema changes require explicit,
ordered migration files.
