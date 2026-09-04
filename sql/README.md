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

## File order

| File | Purpose |
|---|---|
| `00_database.sql` | Create `gc_ml` with owner `gc` |
| `10_schemas.sql` | Create and protect the three schemas |
| `20_raw.sql` | Create source-faithful catalogue staging tables |
| `30_core.sql` | Create normalized astronomical tables |
| `40_ml.sql` | Create samples, runs, embeddings, metrics, and artifacts |
| `90_verify.sql` | Verify the expected tables and list them |
| `apply.sql` | Apply the schema files in order |

The files are safe to re-run for initial creation. `IF NOT EXISTS` does not
upgrade an older table definition. Later schema changes require explicit,
ordered migration files.
