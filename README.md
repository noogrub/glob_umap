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
5. [core_architecture.md](core_architecture.md)

These files define the project scope, collaboration boundary, database
architecture, evaluation policy, graphing standard, and naming requirements.

## Repository authority

John has designated `noogrub/glob_umap` as the shared working repository for
this project. Codex is authorized to create, modify, commit, and push ordinary
project work here without requesting renewed permission for each push.
Destructive operations, history rewrites, secrets, and actions outside this
repository still require their normal safeguards.

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

## Materialize the clean sample

After reviewing both funnel reports, create the conservative population:

```bash
glob-umap sample --config config/materialize/clean.yaml
```

The operation creates one `ml.sample` definition and its `ml.member` rows in a
single transaction. It refuses to overwrite an existing named sample, verifies
the materialized count against a freshly evaluated funnel, leaves all data
splits explicitly `unassigned`, and writes
`data/interim/clean_sample.json`.

## Normalize label evidence

Apply the evidence-identity migration to an existing database:

```bash
psql --file=sql/32_label_evidence.sql
```

Then normalize the distinct photometric, spectroscopic, and DES morphology
evidence without changing sample membership or assigning data splits:

```bash
glob-umap labels --config config/core/labels.yaml
```

The command retains separate evidence rows when an object has more than one
source, preserves source probabilities only where supplied, refuses to write
into a nonempty `core.label` table, and verifies that every materialized sample
member has supporting evidence for its assigned target class. It writes
`data/interim/label_manifest.json` after the database transaction commits.

## Freeze the development/test split

After label evidence has been normalized, assign the configured stratified
holdout once:

```bash
glob-umap split --config config/splits/clean.yaml
```

The command requires every member to remain `unassigned` and to have label
evidence supporting its target class. Within each class, it orders stable
catalogue identities by a seeded hash and assigns the nearest integer to the
configured 20 percent test population. The remaining members form the
development population stored as `train`; later cross-validation folds are
temporary experiment-level partitions of that development population.

The exact class counts, resolved configuration, algorithm, and SHA-256 digest
of all assignments are stored in both the sample definition and
`data/interim/clean_split.json`. A second invocation fails rather than replacing
the frozen split.

## Bind exact catalogue records

Apply the member-record migration once to an existing database:

```bash
psql --file=sql/41_member_record.sql
```

Then bind every sample member to the exact FDS reference record and DES target
record selected during sample preparation:

```bash
glob-umap bind --config config/bindings/clean.yaml
```

The command inherits catalogue names and match policy from the materialization
definition, requires an empty binding set for the sample, and verifies one
reference and one target record per member. It stores the binding definition
and checksum in `ml.sample.definition.records` and writes
`data/interim/clean_records.json`. Later feature extraction reads these fixed
records rather than reconstructing the crossmatch.

## Normalize photometry

Normalize the measurements selected for the clean sample:

```bash
glob-umap phot --config config/core/phot.yaml
```

The configuration records FDS PSF `u` and DES aperture-5 `grizY`
measurements for the exact bound catalogue rows. The first feature set uses
observed magnitudes: DES publishes its `grizY` extinction coefficients, but
the comparison paper does not state the FDS `u` coefficient it applied. The
normalizer supports a coefficient-driven dereddened variant, but requires
every coefficient to be stated explicitly in YAML. It never supplies one as
an implicit default.

Every normalized value retains its catalogue record, band, measurement type,
reported uncertainty, correction state, and aperture diameter where
applicable. The stage records a stable digest in the sample definition and
`data/interim/phot_manifest.json`.

## Build and audit model features

Apply the feature migration once to an existing database, then build the
configured feature set:

```bash
psql --file=sql/42_feature.sql
glob-umap features --config config/features/clean.yaml
```

The stage materializes six magnitudes and all 15 pairwise colors in normalized
long form. The five adjacent colors are a named nonredundant group; all 15
colors remain available as the paper-like redundancy sensitivity group.
Color uncertainties use the explicitly configured independent-error
quadrature approximation. The audit requires one finite value per feature and
sample member, verifies every algebraic color identity, and confirms numerical
rank five before committing. Its manifest is
`data/interim/feature_manifest.json`.

## Freeze the evaluation plan

After the feature audit succeeds, bind the database state to the predeclared
evaluation protocol:

```bash
glob-umap plan --config config/exp/core.yaml
```

The plan compares identity, PCA, and unsupervised UMAP on the same development
population, feature groups, fold-local scaling, and classifiers. The final
test set remains locked through representation and parameter selection. The
operating threshold is chosen from out-of-fold development predictions to
target 30 percent GC recall, then applied unchanged to the test set. The plan
also declares UMAP stability seeds and paired stratified bootstrap uncertainty.
The command is read-only and writes `data/interim/evaluation_plan.json` only
after verifying the sample, split, bindings, photometry, and feature digest.

## Frozen data-foundation milestone

The first publication-grade analysis input was frozen on September 12, 2026.
It contains 54,799 labeled objects: 1,402 globular clusters, 49,667 galaxies,
and 3,730 stars. The fixed outer partition contains 43,840 development objects
and 10,959 final-test objects. The final-test population has not been used for
representation or model selection.

Each member is bound to one exact FDS reference record and one exact DES target
record. The observed-photometry layer contains one FDS PSF `u` measurement and
five DES aperture-5 `grizY` measurements per member. The feature layer contains
six magnitudes and all 15 pairwise colors per member; its color matrix has the
expected numerical rank of five and zero maximum algebraic-identity residual at
the recorded precision.

The binding, split, photometry, and feature digests are recorded in the
committed manifests under `data/interim/`. This milestone freezes inputs and
evaluation policy, not model results.

## PostgreSQL integration test

Unit tests do not execute SQL against PostgreSQL. Before a release or database
stage change, run the dedicated integration test against the disposable
database named exactly `gc_ml_test`. The test refuses any other database name
and never targets `gc_ml`.

Create the database once as an administrator, add a matching `gc_ml_test` entry
to `.pgpass`, then run:

```bash
cd /tmp
sudo -u postgres createdb --owner=gc gc_ml_test

cd /home/jwb/Code/glob_umap
GC_ML_TEST_DATABASE=gc_ml_test \
  python -m unittest discover -s integration_tests -v
```

The test rebuilds only the `raw`, `core`, and `ml` schemas in `gc_ml_test`,
loads a six-object fixture, and executes the production configurations through
record binding, photometry normalization, feature construction, and evaluation
plan validation.

## Database snapshot

Until the RAID10 target is available, verified database snapshots reside on
the Elonius system drive beneath `/home/jwb/postgres-snapshots/gc_ml/`. The
snapshot directory itself is not committed. Create a custom-format database
archive, preserve the required PostgreSQL roles, list the archive contents, and
checksum every output:

```bash
umask 077
snapshot_dir="/home/jwb/postgres-snapshots/gc_ml/$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$snapshot_dir"

(cd /tmp && sudo -u postgres \
  pg_dump --format=custom --compress=9 --dbname=gc_ml) \
  > "$snapshot_dir/gc_ml.dump"

(cd /tmp && sudo -u postgres \
  pg_dumpall --globals-only --no-role-passwords) \
  > "$snapshot_dir/globals.sql"

pg_restore --list "$snapshot_dir/gc_ml.dump" \
  > "$snapshot_dir/gc_ml.list"

(
  cd "$snapshot_dir"
  sha256sum gc_ml.dump globals.sql gc_ml.list > SHA256SUMS
  sha256sum --check SHA256SUMS
)
```

Copy the complete timestamped directory to a separate physical drive while
the RAID10 device is offline.
