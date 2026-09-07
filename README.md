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
numeric sentinel values, maps only empty fields to SQL `NULL`, registers each
source in `core.catalog`, and writes the configured provenance manifest after a
successful commit. During loading it reports progress at the YAML-configured
interval, currently every 10 seconds, as well as at the start and completion of
each catalogue.

The manifest includes the resolved ingestion configuration, hashes of every
YAML configuration file, hashes and row counts for every source catalogue, the
Git commit, and relevant software versions.

Run the unit tests with:

```bash
python -m unittest discover -s tests -v
```
