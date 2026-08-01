# Project Policy

## Fair method comparison

PCA and UMAP must receive precisely the same:

- object population;
- feature vectors;
- scaling;
- missing-data treatment;
- labels;
- train/test separation.

We should fit preprocessing and embeddings only on the appropriate training population. Otherwise information can leak across evaluation boundaries.

Because UMAP is stochastic, a single attractive embedding proves little. Each UMAP configuration should run across a YAML-defined seed ensemble. We then measure whether neighborhoods, separations, and downstream performance persist.

Evaluation should include more than visual appeal:

- neighborhood preservation;
- trustworthiness and continuity;
- recovery of known globular clusters;
- contaminant rejection;
- stability across seeds;
- stability across UMAP parameters;
- sensitivity to photometric uncertainty;
- performance as progressively harder contaminants are introduced;
- comparison with PCA using identical downstream classifiers.

## Graphing policy

I would implement one shared plotting layer and one YAML style definition. Individual analyses supply data and semantic labels; they do not choose fonts, palettes, line widths, or export details independently.

Our defaults should include:

- restrained Tufte-style presentation;
- minimal spines and grid lines;
- direct labels where practical;
- meaningful axis labels with units;
- sentence-case descriptive titles;
- metadata in captions and manifests, not titles;
- colorblind-safe palettes;
- uncertainty shown when it affects interpretation;
- vector output for line work and rasterization for very dense scatter;
- identical axis ranges for genuine visual comparisons.

Zero-based axes should be a policy applied when scientifically meaningful, not an absolute rule. PCA coordinates are naturally centered around zero. UMAP coordinates have arbitrary origin and scale, so forcing zero into the plot conveys nothing. Astronomical magnitude conventions and tightly bounded color ranges also require judgment.

## Filename policy

Filenames should describe function, not contain experimental metadata:

```text
ingest/fds.py
ingest/des.py
match/sky.py
feature/color.py
embed/pca.py
embed/umap.py
eval/neighborhood.py
plot/embed.py
```

Likewise:

```text
config/exp/pca.yaml
config/exp/umap.yaml
config/exp/boundary.yaml
```

Generated outputs can live beneath a short run identifier:

```text
artifacts/run_0042/
```

The accompanying manifest records parameters, input checksums, timestamps, versions, and row counts. The filename does not need to become a miniature database.

Finally, every filtering stage should produce a count ledger: records read, rejected, matched, ambiguous, missing bands, retained, labeled, and assigned to each sample. That ledger will help us reconstruct the paper’s unexplained count transitions—and ensure that we never create unexplained transitions of our own.
