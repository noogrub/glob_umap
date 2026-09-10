# Database Design

For PostgreSQL, `gc_ml` and user `gc` are good. I suggest standard PostgreSQL environment variables:

```bash
export PGDATABASE=gc_ml
export PGUSER=gc
export PGHOST=localhost
export PGPORT=5432
```

Keep the password only in `.pgpass`, never `.bashrc`, and set:

```bash
chmod 600 ~/.pgpass
```

## Database structure

I would use three schemas:

- `raw`: source-faithful imports, preserved without reinterpretation
- `core`: normalized astronomical objects, measurements, matches, and labels
- `ml`: samples, experiment runs, embeddings, metrics, and artifacts

The essential distinction is between a catalogue record and an astronomical object. One physical source may appear in FDS, DES, and spectroscopic catalogues. We must preserve each original record and represent our assertion that records correspond to the same object separately.

A preliminary normalized model would include:

| Schema | Table | Purpose |
|---|---|---|
| `raw` | `fds`, `des`, `spec` | Source-faithful imported records |
| `core` | `catalog` | Catalogue and release provenance |
| `core` | `object` | Canonical astronomical object |
| `core` | `record` | Original catalogue record |
| `core` | `match` | Record-to-object correspondence |
| `core` | `phot` | Band measurements and uncertainties |
| `core` | `shape` | Morphology and concentration measurements |
| `core` | `label` | Classification evidence and provenance |
| `ml` | `sample` | Defined experimental population |
| `ml` | `member` | Objects included in a sample |
| `ml` | `run` | One resolved experiment execution |
| `ml` | `embed` | PCA or UMAP coordinates |
| `ml` | `metric` | Evaluation results |
| `ml` | `artifact` | Figures, manifests, and exported results |

The `label` table should hold evidence, not pretend to contain unquestionable ground truth. A spectroscopic classification, photometric selection, literature classification, and our own inferred classification are different evidence types with different strengths.

For the Cantiello master catalogue, `p_gc` and half-light radius are
ACSFCS-derived measurements. The verified source release contains neither
value for its 1,159 spectroscopic-only objects, while both are present for all
2,104 objects with photometric identification. The normalized layer must
preserve this structural absence as SQL `NULL`, without imputation.
Photometric and spectroscopic identification remain separate
provenance-bearing rows in `core.label`.

## Normalization versus analysis speed

Normalized tables should be authoritative. ML code should consume deliberately denormalized database views or materialized views.

For example, a materialized view might provide one row per object with:

```text
u_g, g_r, r_i, i_z, z_y, uncertainties, morphology, label
```

This gives us:

- clean relational storage;
- fast NumPy/pandas extraction;
- a documented mapping from source measurements to model vectors;
- no repeated hand-written joins inside analysis code.

## Crossmatching

Crossmatching must be a first-class stage rather than an incidental join. Each match should retain:

- angular separation;
- matching method;
- search radius;
- candidate count;
- ambiguity status;
- catalogue coordinates used;
- matching run identifier.

We should never silently discard one-to-many or ambiguous matches. Those cases may become especially interesting near the classification boundary.

## Implemented catalogue-level schema

The initial schema is implemented in `sql/`.

### Raw catalogue tables

| Table | Source |
|---|---|
| `raw.fds` | FDS one-degree source catalogue |
| `raw.des` | DES DR2 one-degree source catalogue |
| `raw.gc_master` | Cantiello et al. master globular-cluster catalogue |
| `raw.spec` | Chaturvedi et al. spectroscopic catalogue |

Raw tables retain source values without scientific filtering. The ingestion
layer maps original column names to SQL-safe names and records the source file
and source row. Catalogue-specific textual null markers such as `---` are
mapped to SQL `NULL` according to YAML; numeric sentinel values remain
unchanged.

### Core tables

| Table | Purpose |
|---|---|
| `core.catalog` | Source, release, file, checksum, and import provenance |
| `core.object` | Canonical astronomical identity and adopted position |
| `core.record` | One source-catalogue record |
| `core.match_run` | Resolved configuration for a crossmatch operation |
| `core.match` | Ranked record-to-object match candidates and selection |
| `core.phot` | Normalized per-band magnitude measurements |
| `core.shape` | Normalized morphology measurements |
| `core.label` | Classification evidence with provenance and confidence |

`core.match` preserves every candidate considered by a matching run. A partial
unique index permits at most one selected object for each source record while
retaining ambiguous alternatives.

`core.label` preserves distinct evidence rather than collapsing it into one
ground-truth assertion. A partial unique index on object, source record,
evidence type, and provenance prevents accidental duplicate normalization
while allowing one source record to contribute separate photometric and
spectroscopic evidence.

An object's `origin_record_id` identifies the catalogue record from which its
initial identity and adopted position were created. For the first Fornax
crossmatch, each FDS source seeds one canonical object. This origin is explicit
provenance rather than an assertion that FDS coordinates are permanently
preferred over every later measurement.

The initial FDS-DES match reproduces the paper's 1 arcsecond search radius with
a unit-sphere k-d tree. It stores every DES candidate, its exact spherical
separation, candidate count, and deterministic rank. No DES candidate is
selected during candidate generation. Unmatched, unique-candidate, and
multiple-candidate cases are counted before a resolution policy is chosen.

### Machine-learning tables

| Table | Purpose |
|---|---|
| `ml.sample` | Versioned population definition |
| `ml.member` | Object membership, split, target, and explicit weight |
| `ml.run` | Resolved experiment configuration and Git provenance |
| `ml.embed` | Normalized embedding coordinates of arbitrary dimension |
| `ml.metric` | Evaluation values, thresholds, intervals, and scope |
| `ml.stage_count` | Required row-count ledger for every filtering stage |
| `ml.artifact` | Generated figure, manifest, and export provenance |

`ml.member.split` stores one frozen outer partition for each materialized
sample. The first clean sample uses a stratified 80 percent development and 20
percent test partition. Its stable seeded assignment is based on the origin
catalogue code and source row rather than database identity values. The exact
configuration, allocation rule, class counts, and assignment digest are stored
under `ml.sample.definition.split` and in the corresponding manifest.

The value `train` denotes the complete development population. Cross-validation
folds are derived within that population for each experiment and are not
written into `ml.member`. The `test` population remains fixed across all fair
method comparisons.

The Rubin temporal and detector-reliability extension is deliberately absent
from this first migration. It will extend the schema after the real Rubin data
products and their fields have been inspected.

## Schema application

`sql/00_database.sql` creates database `gc_ml` for existing login role `gc`.
`sql/apply.sql` creates all catalogue-level schemas and tables in one
transaction, then verifies the result. Exact commands and prerequisites are in
`sql/README.md`.

`sql/31_object_origin.sql` adds explicit source-record provenance to canonical
objects. Existing databases created before this migration must apply it once
before running the crossmatch.


## Raw catalogue immutability

After ingestion and audit, the `raw` schema and its four catalogue tables are
owned by the `NOLOGIN` role `gc_raw_owner`. The project login `gc` has
`USAGE` on the schema and `SELECT` on the tables, but no write or schema
creation privileges. Normal analysis therefore cannot insert, update, delete,
truncate, or alter raw catalogue data.

The source identity of a raw record is `(source_file, source_row)` within the
registered, checksummed catalogue release. Published catalogue identifiers
remain data attributes used later for matching; they are not assumed to be
unique record keys.

Apply the post-ingestion lock with `sql/50_lock_raw.sql`. Verify the database
source contract, row-key continuity, ownership, and privileges with
`sql/91_audit_raw.sql`. The file checksum is independently verified by the
`glob-umap preflight` command. Administrator-only recovery instructions are
maintained in `sql/README.md`.
