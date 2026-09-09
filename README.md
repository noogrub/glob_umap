# glob_umap

Use UMAP to analyze LSST-like color data for identifying globular clusters in
Vera C. Rubin Observatory data.

## Keel boot

This README is the authoritative project boot source for
`noogrub/glob_umap`.

Before designing, writing, modifying, or reviewing the project, read these
files in full:

1. [P609_E584_Rubin_project.md](P609_E584_Rubin_project.md)
2. [database_design.md](database_design.md)
3. [policy.md](policy.md)
4. [data_preparation.md](data_preparation.md)

These files define the project scope, collaboration boundary, database
architecture, evaluation policy, graphing standard, and naming requirements.

For database creation or schema work, also read
[sql/README.md](sql/README.md).

## Current boundary

The private `glob_umap` repository is the source of truth for John's
individual P609 research and prospective paper. A future E584 group repository
on `github.iu.edu` will consume versioned ParaView exports without owning the
P609 database or analysis core.

## Catalogue ingestion

Install the package in a project virtual environment:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test]'
```

Verify every raw file against its configured checksum, header or fixed-width
layout, and row count without changing PostgreSQL:

```bash
glob-umap preflight --config config/datasets/fornax.yaml
```

Only after preflight succeeds, load all four catalogues in one transaction:

```bash
glob-umap ingest --config config/datasets/fornax.yaml
```

The loader reads PostgreSQL connection settings from the standard `PG*`
environment variables. It refuses to load into a nonempty raw table, preserves
numeric sentinel values, maps only YAML-configured catalogue null markers to
SQL `NULL`, registers each source in `core.catalog`, and writes the configured
provenance manifest after a successful commit. During loading it reports
progress at the YAML-configured
interval, currently every 10 seconds, as well as at the start and completion of
each catalogue.

The manifest includes the resolved ingestion configuration, hashes of every
YAML configuration file, hashes and row counts for every source catalogue, the
Git commit, and relevant software versions.

Run the unit tests with:

```bash
python -m unittest discover -s tests -v
```

Audit the loaded raw tables without modifying them:

```bash
glob-umap audit --config config/audits/raw.yaml
```

The audit verifies source counts, stable-key uniqueness, coordinate bounds,
per-column null counts, and numeric ranges. Its configuration and output paths
are defined in YAML.

After a successful initial audit, lock the raw catalogue layer as the
PostgreSQL administrator and verify its source contract and permissions:

```bash
sudo -u postgres psql --dbname=gc_ml < sql/50_lock_raw.sql
psql --file=sql/91_audit_raw.sql
```

The `gc` project login then retains read access but cannot modify the raw
schema or its catalogue tables.

## Normalize catalogue records

Apply the object-origin migration once to an existing database:

```bash
psql --file=sql/31_object_origin.sql
```

Then create one normalized `core.record` row for every immutable raw row:

```bash
glob-umap records --config config/core/records.yaml
```

The YAML file defines each source table, coordinate columns, and composite
source key. The command refuses to overwrite existing core records and writes
`data/interim/record_manifest.json`.

## Generate FDS-DES match candidates

Generate every DES-to-FDS candidate within the paper's 1 arcsecond radius:

```bash
glob-umap match --config config/matches/fds_des.yaml
```

FDS records seed the canonical objects. Their zero-separation identity links
are selected, but every DES candidate remains unselected until ambiguity has
been inspected. The command records candidate ranks, separations, multiplicity,
the resolved YAML configuration, and summary counts in
`data/interim/fds_des_match.json`.

## Audit the sample funnels

Count every selection stage under the conservative reciprocal-nearest policy:

```bash
glob-umap funnel --config config/samples/clean.yaml
```

Repeat the same measurements using the nearest DES source for every FDS
record, our paper-like sensitivity policy:

```bash
glob-umap funnel --config config/samples/paper.yaml
```

These commands are read-only. They report matched, complete, error-qualified,
and labeled populations, compare available stages with the paper's counts,
and write provenance manifests beneath `data/interim/`. The evidence and
decision trail are maintained in `data_preparation.md`.
