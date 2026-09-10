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

To unlock the raw layer deliberately, run these commands as the PostgreSQL
administrator:

```sql
BEGIN;
ALTER SCHEMA raw OWNER TO gc;
ALTER TABLE raw.fds OWNER TO gc;
ALTER TABLE raw.des OWNER TO gc;
ALTER TABLE raw.gc_master OWNER TO gc;
ALTER TABLE raw.spec OWNER TO gc;
COMMIT;
```

After rebuilding and auditing the raw layer, run `50_lock_raw.sql` again.

## Add canonical-object provenance

Existing databases require this migration before the first crossmatch:

```bash
psql --file=sql/31_object_origin.sql
```

It adds `core.object.origin_record_id`, its foreign key to `core.record`, and a
unique index. The migration is idempotent and does not alter the locked raw
catalogues.

## Protect normalized label evidence

Existing databases require this migration before label normalization:

```bash
psql --file=sql/32_label_evidence.sql
```

It prevents the same source record from contributing the same evidence to the
same object more than once. Distinct photometric and spectroscopic evidence
from one catalogue record remain separate rows.

## Bind sample members to source records

Existing databases require this migration before freezing the catalogue rows
used by each materialized sample:

```bash
psql --file=sql/41_member_record.sql
```

It adds `ml.member_record`, whose composite foreign key restricts bindings to
existing sample members. Each member may have one reference and one target
record. The migration does not populate the table; use the configured
`glob-umap bind` stage after applying it.

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
| `31_object_origin.sql` | Link each canonical object to its originating record |
| `32_label_evidence.sql` | Prevent duplicate source-evidence rows |
| `40_ml.sql` | Create samples, runs, embeddings, metrics, and artifacts |
| `41_member_record.sql` | Bind sample members to exact source records |
| `50_lock_raw.sql` | Transfer raw ownership and grant `gc` read-only access |
| `90_verify.sql` | Verify the expected tables and list them |
| `91_audit_raw.sql` | Audit raw source lineage, ownership, and permissions |
| `apply.sql` | Apply the schema files in order |

The files are safe to re-run for initial creation. `IF NOT EXISTS` does not
upgrade an older table definition. Later schema changes require explicit,
ordered migration files.
