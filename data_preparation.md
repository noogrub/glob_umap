# Data Preparation

This document is the reproducible decision record for constructing the first
Fornax machine-learning populations. It preserves the evidence, diagnostic
queries, observed results, assumptions, and resulting policies. It does not
claim an exact reconstruction of Schweder-Souza et al. where the publication
does not specify an implementation detail.

## Scientific target

The immediate experiment asks whether a neighborhood-preserving
representation improves the purity-completeness tradeoff for globular-cluster
selection. PCA, UMAP, and later representations must therefore receive the
same objects, photometry, labels, preprocessing, and data splits.

Schweder-Souza et al. report the following preparation sequence:

1. select a circular one-degree field around NGC 1399;
2. crossmatch FDS and DES within 1 arcsecond;
3. use FDS PSF `u` and DES `grizY` `MAG_APER_5` photometry;
4. remove sources missing any of the six magnitudes;
5. remove sources with an error greater than 0.5 mag in any band;
6. identify known GCs;
7. label high-confidence DES galaxies and stars while excluding known GCs.

The paper reports this count sequence:

| Stage | Reported rows |
|---|---:|
| DES sources in the one-degree field | 395,813 |
| Complete six-band photometry | 190,281 |
| Errors no greater than 0.5 mag | 105,318 |
| Globular clusters in final sample | 1,440 |
| Galaxies in final sample | 49,579 |
| Stars in final sample | 3,726 |
| Final labeled sample | 54,745 |

The paper gives the radius but not the exact coordinate columns, crossmatch
direction, software, tie handling, or treatment of multiple candidates. It
also states that magnitudes were corrected for reddening without listing the
coefficients used for every selected magnitude column.

## Verified source contract

The downloaded field reproduces the paper's DES starting count when centered
at `(54.6205, -35.4498)` degrees. That center is consequently part of this
dataset's provenance; it is not inferred again during sample preparation.

The raw catalogues were verified against their files before being locked:

| Relation | Rows | Source rows | SHA-256 verified |
|---|---:|---:|---|
| `raw.fds` | 239,158 | 239,158 | yes |
| `raw.des` | 395,813 | 395,813 | yes |
| `raw.gc_master` | 3,263 | 3,263 | yes |
| `raw.spec` | 851 | 851 | yes |

Every immutable raw record is identified by the checksummed catalogue release
and `(source_file, source_row)`. Catalogue identifiers remain scientific data,
not assumed primary keys. Run `glob-umap preflight` and
`sql/91_audit_raw.sql` to recheck this contract.

## Why FDS is the reference catalogue

The paper's six-band vector requires the FDS `u` measurement. FDS also
contains the source identifiers used by the master GC catalogue and the
Chaturvedi cross-identifications. Each FDS record therefore seeds one
`core.object`; DES records are candidate measurements of those objects.

This does not assert that FDS coordinates are universally superior. It makes
the origin of each object explicit and supplies a deterministic direction for
this crossmatch.

## Candidate generation

`glob-umap match --config config/matches/fds_des.yaml` retained every DES-FDS
candidate within 1 arcsecond. It made no automatic DES selection.

Observed result:

| Quantity | Count |
|---|---:|
| FDS records | 239,158 |
| DES records | 395,813 |
| Candidate pairs | 213,094 |
| DES records with candidates | 212,907 |
| DES records with one candidate | 212,720 |
| DES records with multiple candidates | 187 |
| DES records without candidates | 182,906 |
| FDS records with targets | 212,802 |
| FDS records with multiple targets | 292 |

Candidate separations ranged from 0.000223 to 0.999876 arcsec, with a median
of 0.208186 arcsec.

The basic database audit was:

```sql
WITH des_candidates AS (
    SELECT m.object_id,
           m.record_id,
           m.angular_sep_arcsec,
           m.candidate_count,
           m.candidate_rank
    FROM core.match AS m
    JOIN core.match_run AS mr USING (match_run_id)
    JOIN core.record AS r USING (record_id)
    JOIN core.catalog AS c USING (catalog_id)
    WHERE mr.name = 'fds_des_1arcsec'
      AND c.code = 'des_dr2_fornax'
)
SELECT count(*) AS candidate_pairs,
       count(DISTINCT record_id) AS des_with_candidates,
       count(DISTINCT object_id) AS fds_with_targets,
       min(angular_sep_arcsec) AS minimum_arcsec,
       percentile_cont(0.5) WITHIN GROUP (
           ORDER BY angular_sep_arcsec
       ) AS median_arcsec,
       max(angular_sep_arcsec) AS maximum_arcsec
FROM des_candidates;
```

## Ambiguity investigation

Ambiguity exists in both directions. A DES record can fall within 1 arcsecond
of two FDS objects, and an FDS object can have two DES records within the
radius. Neither case may be silently discarded.

### DES-to-FDS ambiguity

For the 187 DES records with two FDS candidates, the separation gap between
the first and second candidates ranged from 0.002286 to 0.852439 arcsec; the
median gap was 0.306513 arcsec.

```sql
WITH ranked AS (
    SELECT m.record_id,
           m.candidate_count,
           m.candidate_rank,
           m.angular_sep_arcsec
    FROM core.match AS m
    JOIN core.match_run AS mr USING (match_run_id)
    JOIN core.record AS r USING (record_id)
    JOIN core.catalog AS c USING (catalog_id)
    WHERE mr.name = 'fds_des_1arcsec'
      AND c.code = 'des_dr2_fornax'
), margins AS (
    SELECT record_id,
           max(candidate_count) AS candidates,
           max(angular_sep_arcsec) FILTER (
               WHERE candidate_rank = 2
           ) - max(angular_sep_arcsec) FILTER (
               WHERE candidate_rank = 1
           ) AS margin_arcsec
    FROM ranked
    GROUP BY record_id
    HAVING max(candidate_count) > 1
)
SELECT count(*) AS ambiguous_des,
       max(candidates) AS maximum_candidates,
       min(margin_arcsec) AS minimum_margin,
       percentile_cont(0.5) WITHIN GROUP (
           ORDER BY margin_arcsec
       ) AS median_margin,
       max(margin_arcsec) AS maximum_margin
FROM margins;
```

### FDS-to-DES ambiguity

For the 292 FDS objects with two DES candidates, the separation gap ranged
from 0.000510 to 0.889538 arcsec; the median gap was 0.295288 arcsec.

```sql
WITH ranked AS (
    SELECT m.object_id,
           m.angular_sep_arcsec,
           row_number() OVER (
               PARTITION BY m.object_id
               ORDER BY m.angular_sep_arcsec, m.record_id
           ) AS reference_rank,
           count(*) OVER (
               PARTITION BY m.object_id
           ) AS candidates
    FROM core.match AS m
    JOIN core.match_run AS mr USING (match_run_id)
    JOIN core.record AS r USING (record_id)
    JOIN core.catalog AS c USING (catalog_id)
    WHERE mr.name = 'fds_des_1arcsec'
      AND c.code = 'des_dr2_fornax'
), margins AS (
    SELECT object_id,
           max(candidates) AS candidates,
           max(angular_sep_arcsec) FILTER (
               WHERE reference_rank = 2
           ) - max(angular_sep_arcsec) FILTER (
               WHERE reference_rank = 1
           ) AS margin_arcsec
    FROM ranked
    GROUP BY object_id
    HAVING max(candidates) > 1
)
SELECT count(*) AS ambiguous_fds,
       max(candidates) AS maximum_candidates,
       min(margin_arcsec) AS minimum_margin,
       percentile_cont(0.5) WITHIN GROUP (
           ORDER BY margin_arcsec
       ) AS median_margin,
       max(margin_arcsec) AS maximum_margin
FROM margins;
```

## Match-policy comparison

Selecting the nearest DES record for each FDS object produces 212,802 pairs,
but only 212,621 distinct DES records. Thus 181 DES measurements would be
assigned to two FDS objects. Requiring reciprocal nearest neighbors retains
212,621 unambiguous one-to-one pairs.

```sql
WITH ranked AS (
    SELECT m.object_id,
           m.record_id AS des_record_id,
           m.candidate_rank AS target_rank,
           row_number() OVER (
               PARTITION BY m.object_id
               ORDER BY m.angular_sep_arcsec, m.record_id
           ) AS reference_rank
    FROM core.match AS m
    JOIN core.match_run AS mr USING (match_run_id)
    JOIN core.record AS r USING (record_id)
    JOIN core.catalog AS c USING (catalog_id)
    WHERE mr.name = 'fds_des_1arcsec'
      AND c.code = 'des_dr2_fornax'
), nearest AS (
    SELECT * FROM ranked WHERE reference_rank = 1
)
SELECT count(*) AS fds_nearest_matches,
       count(DISTINCT des_record_id) AS distinct_des_records,
       count(*) - count(DISTINCT des_record_id) AS duplicate_des_assignments,
       count(*) FILTER (WHERE target_rank = 1) AS reciprocal_nearest
FROM nearest;
```

This establishes two deliberate policies:

| Configuration | Policy | Purpose |
|---|---|---|
| `config/samples/clean.yaml` | reciprocal nearest | Conservative primary population; one DES measurement cannot represent two FDS objects |
| `config/samples/paper.yaml` | nearest DES per FDS | Paper-like sensitivity population; does not claim to reproduce unpublished ambiguity handling |

## Coordinate-column check

DES supplies both catalog positions (`ra`, `dec`) and windowed positions
(`ra_window`, `dec_window`). The normalized match uses the windowed positions.
We checked whether that choice could explain the count discrepancy.

```sql
WITH offsets AS (
    SELECT degrees(acos(least(1.0, greatest(-1.0,
        sin(radians(dec)) * sin(radians(dec_window))
        + cos(radians(dec)) * cos(radians(dec_window))
        * cos(radians(ra - ra_window))
    )))) * 3600.0 AS separation_arcsec
    FROM raw.des
)
SELECT percentile_cont(0.5) WITHIN GROUP (
           ORDER BY separation_arcsec
       ) AS median_arcsec,
       percentile_cont(0.95) WITHIN GROUP (
           ORDER BY separation_arcsec
       ) AS p95_arcsec,
       max(separation_arcsec) AS maximum_arcsec,
       count(*) FILTER (
           WHERE separation_arcsec > 0.1
       ) AS above_0_1_arcsec,
       count(*) FILTER (
           WHERE separation_arcsec > 0.5
       ) AS above_0_5_arcsec
FROM offsets;
```

Observed median, 95th percentile, and maximum separations were 0.001295,
0.001976, and 0.002327 arcsec. No record differed by more than 0.1 arcsec.
Coordinate-column choice therefore cannot explain a discrepancy of roughly
one thousand complete sources.

## Photometric funnel comparison

Both match policies use:

- FDS PSF `u_mag` and `u_mag_err`;
- DES `MAG_APER_5` `grizY` magnitudes and errors;
- all six magnitudes present, treating the documented DES value `99` as
  missing rather than as a physical magnitude;
- all six errors present and no greater than 0.5 mag.

The initial diagnostic query produced:

| Policy | Matched | Complete `ugrizY` | Errors at most 0.5 mag |
|---|---:|---:|---:|
| Nearest DES per FDS | 212,802 | 191,297 | 106,121 |
| Reciprocal nearest | 212,621 | 191,123 | 106,008 |
| Paper | not reported | 190,281 | 105,318 |

The corresponding SQL pattern was:

```sql
WITH candidates AS (
    SELECT m.object_id,
           m.record_id AS des_record_id,
           m.candidate_rank AS target_rank,
           row_number() OVER (
               PARTITION BY m.object_id
               ORDER BY m.angular_sep_arcsec, m.record_id
           ) AS reference_rank
    FROM core.match AS m
    JOIN core.match_run AS mr USING (match_run_id)
    JOIN core.record AS r USING (record_id)
    JOIN core.catalog AS c USING (catalog_id)
    WHERE mr.name = 'fds_des_1arcsec'
      AND c.code = 'des_dr2_fornax'
), policies AS (
    SELECT 'fds_nearest' AS policy, *
    FROM candidates
    WHERE reference_rank = 1
    UNION ALL
    SELECT 'reciprocal' AS policy, *
    FROM candidates
    WHERE reference_rank = 1 AND target_rank = 1
), joined AS (
    SELECT p.policy,
           f.u_mag,
           f.u_mag_err,
           d.g_mag_ap5, d.g_mag_ap5_err,
           d.r_mag_ap5, d.r_mag_ap5_err,
           d.i_mag_ap5, d.i_mag_ap5_err,
           d.z_mag_ap5, d.z_mag_ap5_err,
           d.y_mag_ap5, d.y_mag_ap5_err
    FROM policies AS p
    JOIN core.object AS o USING (object_id)
    JOIN core.record AS fr ON fr.record_id = o.origin_record_id
    JOIN raw.fds AS f ON f.ingest_id = fr.raw_ingest_id
    JOIN core.record AS dr ON dr.record_id = p.des_record_id
    JOIN raw.des AS d ON d.ingest_id = dr.raw_ingest_id
), complete AS (
    SELECT *,
           u_mag IS NOT NULL
           AND g_mag_ap5 IS NOT NULL AND g_mag_ap5 <> 99
           AND r_mag_ap5 IS NOT NULL AND r_mag_ap5 <> 99
           AND i_mag_ap5 IS NOT NULL AND i_mag_ap5 <> 99
           AND z_mag_ap5 IS NOT NULL AND z_mag_ap5 <> 99
           AND y_mag_ap5 IS NOT NULL AND y_mag_ap5 <> 99 AS has_ugrizy
    FROM joined
)
SELECT policy,
       count(*) AS matched,
       count(*) FILTER (WHERE has_ugrizy) AS complete_ugrizy,
       count(*) FILTER (
           WHERE has_ugrizy
             AND u_mag_err <= 0.5
             AND g_mag_ap5_err <= 0.5
             AND r_mag_ap5_err <= 0.5
             AND i_mag_ap5_err <= 0.5
             AND z_mag_ap5_err <= 0.5
             AND y_mag_ap5_err <= 0.5
       ) AS errors_at_most_0_5
FROM complete
GROUP BY policy
ORDER BY policy;
```

Neither reasonable policy reproduces the paper exactly. We will report that
difference rather than tune an undocumented choice until a count agrees.

The completed configured funnels produced:

| Stage | Reciprocal nearest | Nearest DES per FDS | Policy difference | Paper |
|---|---:|---:|---:|---:|
| Matched | 212,621 | 212,802 | +181 | not reported |
| Complete `ugrizY` | 191,123 | 191,297 | +174 | 190,281 |
| Errors at most 0.5 mag | 106,008 | 106,121 | +113 | 105,318 |
| Globular clusters | 1,402 | 1,402 | 0 | 1,440 |
| Galaxies | 49,667 | 49,722 | +55 | 49,579 |
| Stars | 3,730 | 3,730 | 0 | 3,726 |
| Final labeled sample | 54,799 | 54,854 | +55 | 54,745 |

The ambiguity policy changes only 55 final galaxy assignments. It changes no
globular-cluster or star assignments. The reciprocal-nearest population is
both one-to-one and closer to the published final count, but closeness to the
published count is supporting evidence rather than the reason for choosing
the conservative policy.

### Numeric-sentinel correction

The raw DES export uses `99` as a missing-magnitude sentinel, as recorded in
`data/metadata/DATA_INVENTORY.md`. The raw schema preserves that source value
deliberately instead of converting it during ingestion.

The first executable funnel run on 2026-09-09 checked only SQL `NULL` and
therefore incorrectly reported all 212,621 reciprocal matches as having
complete photometry. The error threshold still reduced the population to the
correct 106,008 records because sentinel-bearing measurements could not pass
the 0.5-mag error rule. Before any sample was materialized, the sample YAML and
funnel query were corrected to interpret the configured DES sentinel as
missing. This event is retained here as part of the experimental audit trail.

## Label rules

Known-GC evidence has precedence over contaminant labels.

The FDS master catalogue contributes:

- spectroscopic objects where `spectroscopic_flag = 'Yes'`;
- photometric objects where `photometric_flag = 'Yes'` and `p_gc > 0.75`.

The Chaturvedi catalogue contributes FDS-linked objects with `S/N >= 3` and
accepted source classes `A` or `B`. `EXISTS` semantics prevent repeated
catalogue identifiers from multiplying objects.

The verified master-catalogue structure is:

| Photometric flag | Spectroscopic flag | Rows | Missing `p_gc` | Missing radius |
|---|---|---:|---:|---:|
| No | Yes | 1,159 | 1,159 | 1,159 |
| Yes | No | 1,921 | 0 | 0 |
| Yes | Yes | 183 | 0 | 0 |

The absent `p_gc` and half-light radius values for spectroscopic-only objects
are structural and remain `NULL`; they are not grounds for removing a
spectroscopically identified GC.

After GC assignment, the paper's contaminant rules are applied:

- galaxy: `extended_class_coadd = 3` and
  `19.0 <= i_mag_auto_dered <= 22.5`;
- star: `extended_class_coadd = 0` and
  `18.0 <= i_mag_auto_dered <= 20.0`;
- an object already carrying GC evidence cannot be relabeled as a contaminant.

We use the DES dereddened automatic `i` magnitude for these cuts because the
paper states that all magnitudes were reddening-corrected. This is a grounded
interpretation, not a confirmed implementation detail, and will receive a
raw-versus-dereddened sensitivity check.

## Executable count ledger

The two read-only commands implement the policies above:

```bash
glob-umap funnel --config config/samples/clean.yaml
glob-umap funnel --config config/samples/paper.yaml
```

Each command writes its resolved YAML, YAML checksum, Git commit, software
versions, observed stage counts, and differences from available published
counts to a JSON report in `data/interim/`.

These commands measure the population and do not alter the database.

After both funnels have been inspected, materialize the conservative
population with:

```bash
glob-umap sample --config config/materialize/clean.yaml
```

The command inserts one provenance-bearing `ml.sample` row and its 54,799
`ml.member` rows in a single transaction. Every member initially has the
YAML-configured `unassigned` split and weight `1.0`; train, validation, and test
assignment is a later design-frozen stage. The command refuses to replace a
sample with the same name, reruns the funnel as an integrity check, and rolls
back unless its inserted class total agrees exactly. It writes
`data/interim/clean_sample.json` after the database commit.

The materializer reuses the funnel's exact population query. It records only
sample membership and target class. Normalization of measurements and label
evidence into `core.phot` and `core.label` remains required before feature
extraction; downstream modeling will not read raw catalogue tables directly.

### Completed materialization

The clean population was materialized successfully on 2026-09-09 at
13:20:47 UTC using code commit `44e3b31`. PostgreSQL assigned `sample_id = 1`.
The materialization configuration SHA-256 was
`9ba5071c6f7135fdefadab19e489ee8d4d3ac5a3351dad3d037427c34c2ef507`;
the unchanged clean-sample selection configuration SHA-256 was
`e5dddd85201666d5eecddc9245b521beff5b90a13753bd7dd8fa22ebf96c45ad`.

An independent database query verified the stored population:

```sql
SELECT s.name, m.split, m.target_class, count(*) AS members
FROM ml.sample AS s
JOIN ml.member AS m USING (sample_id)
WHERE s.name = 'clean_reciprocal'
GROUP BY s.name, m.split, m.target_class
ORDER BY m.target_class;
```

| Sample | Split | Target class | Members |
|---|---|---|---:|
| `clean_reciprocal` | `unassigned` | galaxy | 49,667 |
| `clean_reciprocal` | `unassigned` | globular cluster | 1,402 |
| `clean_reciprocal` | `unassigned` | star | 3,730 |

The verified total is 54,799 members. The complete run manifest is
`data/interim/clean_sample.json`, committed in `126c238`.

## Label-evidence normalization

Sample membership does not convert heterogeneous catalogue evidence into a
single unquestioned truth. Before any train/test assignment, the configured
`glob-umap labels` stage writes separate `core.label` rows for:

- ACSFCS photometric GC identification, retaining `p_gc` as confidence;
- Cantiello catalogue spectroscopic identification, without inventing a
  numeric confidence;
- Chaturvedi spectroscopic identification, retaining class and signal-to-noise
  ratio in `details`;
- DES high-confidence galaxy or star morphology, tied to the exact DES record
  selected by the reciprocal-nearest policy.

An object may retain multiple or conflicting evidence rows. The clean sample's
GC-precedence rule determines its modeling target; it does not erase the
underlying evidence. The normalization command refuses to overwrite existing
labels and verifies that every materialized member has at least one evidence
row supporting its assigned target class.

Apply the idempotent uniqueness migration and run the stage with:

```bash
psql --file=sql/32_label_evidence.sql
glob-umap labels --config config/core/labels.yaml
```

The resulting manifest is `data/interim/label_manifest.json`.

## Frozen development/test partition

The primary sample receives one outer holdout before feature construction or
model fitting. `config/splits/clean.yaml` declares the sample, source and
destination split names, test fraction, seed, failure policy, and manifest
path. Run:

```bash
glob-umap split --config config/splits/clean.yaml
```

The splitter works independently within each target class. It hashes the
origin catalogue code, immutable source row, and configured seed, ranks those
stable identities, and assigns the nearest integer to the test population.
This avoids dependence on query order, PostgreSQL identity values, or Python
random-number-library behavior. The other members form the development
population recorded as `train`.

The command requires every member to remain `unassigned` and verifies that
each target has supporting normalized evidence. It then records the exact
assignment counts and a SHA-256 digest over every stable identity, target, and
split. The same split definition is stored in `ml.sample.definition`; the full
manifest is `data/interim/clean_split.json`. The command cannot silently
replace an existing assignment.

Only the development population participates in model selection and temporary
cross-validation folds. The test population remains untouched until the
preprocessing, representation, classifier, hyperparameters, and decision
threshold are fixed.

## Decisions and remaining uncertainty

Confirmed decisions:

- primary sample: reciprocal-nearest FDS-DES pairs;
- sensitivity sample: nearest DES record for each FDS object;
- input measurements: FDS PSF `u` plus DES `grizY` `MAG_APER_5`;
- complete six-band photometry for the clean benchmark;
- maximum error of 0.5 mag in every band;
- evidence-based GC precedence;
- published high-confidence DES star and galaxy rules;
- no adjustment made merely to reproduce a published count.

Still to be confirmed with the authors or tested explicitly:

- the paper's precise FDS-DES crossmatch direction and ambiguity policy;
- the exact sky-coordinate columns used;
- whether the authors used the same documented DES numeric-sentinel handling;
- the complete reddening coefficients and timing;
- the Chaturvedi `296 -> 292 -> 268` reduction;
- availability of the prepared merged catalogue or paper-specific code.

If the authors supply those details, the paper-like configuration may be
revised as a new version. The conservative primary policy remains independently
defined and reproducible.

## References

1. Schweder-Souza, N., Chies-Santos, A. L., de Souza, R. S., et al. (2026).
   “The contribution of the color space in LSST-like photometry for the
   selection of extragalactic globular cluster candidates.” *The
   Astrophysical Journal*, **1005**(1), 96.
   [doi:10.3847/1538-4357/ae7321](https://doi.org/10.3847/1538-4357/ae7321).
2. Schweder-Souza, N. `GC-Selector`.
   [https://github.com/n-ssouza/GC-Selector](https://github.com/n-ssouza/GC-Selector).
