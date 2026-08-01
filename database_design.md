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
