# Preliminary Research Proposal

## Nonlinear representations for globular-cluster identification

**John Burgoon**  
**P609 Computational Physics**  
**September 2026**

## Project question

Can a neighborhood-preserving nonlinear representation improve the
identification of globular clusters in six-band photometry relative to
principal component analysis (PCA)?

The immediate goal is a controlled reproduction and extension of
Schweder-Souza et al. (2026). That study classified globular clusters,
galaxies, and stars in a one-degree field around NGC 1399 using LSST-like
`ugrizY` photometry. It reported a minimum globular-cluster contamination rate
of approximately 30% and concluded that PCA retained essentially all useful
color information tested by its models.

This project will test a narrower interpretation of that conclusion. PCA
preserves directions of maximum variance, but the scientifically useful
structure may instead be local and nonlinear. Uniform Manifold Approximation
and Projection (UMAP) is designed to preserve neighborhood structure and is
therefore a suitable comparison. A predictive JEPA-style representation may
be examined later, but it will not displace the PCA-versus-UMAP core.

## Physical basis

The six photometric bands measure different portions of each source's spectral
energy distribution. Relationships among the bands carry information about
stellar population, age, metallicity, dust, and redshift. Globular clusters
can nevertheless resemble compact galaxies or foreground stars in integrated
light. The problem is therefore both a numerical representation problem and a
measurement problem with genuine physical degeneracies.

The experiment will primarily use five independent adjacent colors,
`u-g`, `g-r`, `r-i`, `i-z`, and `z-Y`. The paper's 15 pairwise colors will be
retained as a reproduction condition, although six magnitudes contain only
five independent color degrees of freedom.

## Data and completed preparation

The required public catalogues have been downloaded, checksummed, documented,
and loaded into a normalized PostgreSQL database:

| Catalogue | Records |
|---|---:|
| Fornax Deep Survey photometry | 239,158 |
| Dark Energy Survey DR2 photometry | 395,813 |
| FDS master globular-cluster catalogue | 3,263 |
| Chaturvedi spectroscopic catalogue | 851 |

The raw database layer is immutable and can be audited against the source
files. Every crossmatch candidate within one arcsecond has been retained so
that ambiguous matches remain visible rather than being silently discarded.

Our conservative reciprocal-nearest crossmatch produces:

| Selection stage | Records |
|---|---:|
| DES sources in the field | 395,813 |
| Reciprocal FDS-DES matches | 212,621 |
| Complete `ugrizY` photometry | 191,123 |
| Error no greater than 0.5 mag in every band | 106,008 |
| Globular clusters | 1,402 |
| Galaxies | 49,667 |
| Stars | 3,730 |
| Final labeled sample | 54,799 |

The published final sample contains 54,745 objects. Our independently defined
sample differs by 54 objects, approximately 0.1%, despite several unpublished
crossmatching and preprocessing details. A second analysis using the nearest
DES match for each FDS source will measure how sensitive the results are to the
crossmatching policy.

## Computational experiment

The work will proceed in four stages.

1. **Reproduce the baseline.** Reconstruct the paper's color, PCA,
   autoencoder, random-forest, and multilayer-perceptron comparisons as closely
   as the published methods permit.
2. **Compare representations fairly.** Evaluate PCA and unsupervised UMAP in
   two, four, and five dimensions using identical objects, features, scaling,
   splits, and downstream classifiers. Supervised UMAP will be reported
   separately because it uses label information during representation
   learning.
3. **Measure uncertainty and stability.** Repeat train/test splits and UMAP
   seeds, perturb photometry according to reported uncertainties, and test
   sensitivity to UMAP parameters, redundant colors, the `u` band, and
   crossmatch policy.
4. **Examine difficult cases.** Study globular-cluster versus galaxy errors
   separately from the full three-class problem and inspect whether failures
   correlate with magnitude, morphology, crowding, survey boundaries, or
   likely source blending.

All learned transformations will be fitted only on training data and refitted
inside cross-validation. The final test set will remain untouched until the
model and hyperparameter choices are fixed. Configuration, input checksums,
software versions, random seeds, database state, and population counts will be
recorded for every experiment.

## Evaluation

The principal result will not be chosen from a visually attractive embedding
or a single default classification threshold. Representations will be
compared using:

- precision-recall curves and area under those curves;
- precision at fixed globular-cluster recall;
- recall at fixed globular-cluster precision;
- F1 score with uncertainty intervals;
- paired bootstrap differences between methods;
- neighborhood preservation and stability across UMAP seeds.

Results will be reported for both the three-class problem—globular cluster,
galaxy, and star—and the scientifically difficult globular-cluster-versus-
galaxy problem.

## Expected result and significance

The working hypothesis is that neighborhood-preserving representations may
retain discriminative local structure that PCA does not. A valid positive
result would require a repeatable improvement at matched precision or recall,
not merely visible separation in two dimensions.

A negative result would also be useful. If PCA, UMAP, and the reproduced
autoencoder remain equivalent under controlled evaluation, the experiment
would provide stronger evidence that the available photometry has reached an
information limit and that morphology, near-infrared observations, or other
measurements are required.

## Proposed deliverables

- a reproducible, configuration-driven data and analysis pipeline;
- a documented reproduction of the published PCA baseline;
- a controlled PCA-versus-UMAP evaluation;
- uncertainty, stability, and ablation studies;
- clear scientific figures and a ParaView-compatible dataset;
- a final research paper and class presentation.

Optional visualization and detector-reliability extensions will remain
modular.

## Publication objective

The intended outcome is a manuscript suitable for submission to a
peer-reviewed astronomy journal. The provisional target is *The Astronomical
Journal*, with the final venue determined by whether the principal contribution
is an astronomical result, an analysis methodology, or both.

The paper will be framed as an astronomy study supported by rigorous
computational physics. Its scientific claim will concern globular-cluster
selection and the information carried by Rubin-like multiband photometry. The
numerical analysis will establish how reliably that claim can be made.

## Appendix A: Relevance to this class

The computational core of this project is the numerical stability and
uncertainty propagation of linear and nonlinear representations of physical
measurements. It directly supports the P609 learning outcomes of evaluating
numerical algorithms, choosing methods under computational constraints,
presenting results effectively, building reusable research functions, and
practicing sound software design.

Four distinct sources of uncertainty will be measured rather than conflated:

- **Measurement uncertainty:** reported photometric errors propagated through
  colors, embeddings, and classifications using Monte Carlo perturbations.
- **Sampling uncertainty:** variation across train/test partitions and
  bootstrap samples.
- **Algorithmic uncertainty:** variation across UMAP seeds, approximate-neighbor
  searches, and hyperparameters.
- **Numerical error:** effects caused by finite-precision representation and
  numerical implementation.

The relationship between the project and the P609 syllabus is:

| P609 topic or outcome | Project application |
|---|---|
| Representing numbers and sources of error | `float32` versus `float64`, roundoff, conditioning, and separation of measurement, sampling, algorithmic, and numerical uncertainty |
| Linear algebra | PCA covariance matrix, eigendecomposition, rank deficiency, and correlated colors |
| Nonlinear equations and algorithms | UMAP's nonlinear embedding and optimization |
| Monte Carlo techniques | Photometric perturbations, repeated embeddings, and bootstrap confidence intervals |
| Algorithm selection | PCA versus UMAP versus autoencoder under accuracy, stability, runtime, and memory constraints |
| Effective presentation | Precision-recall curves, uncertainty plots, embedding diagnostics, and concise scientific figures |
| Reusable research functions | General modules for perturbation, conditioning, evaluation, provenance, and visualization |

Specific numerical investigations will include:

- computing sub-arcsecond angular separations without avoidable precision loss;
- measuring the rank and conditioning of 15 pairwise colors derived from only
  six magnitudes;
- examining the stability of PCA eigenvalues and eigenvectors;
- comparing `float32` and `float64` representations;
- preserving correlated errors when one magnitude contributes to multiple
  colors;
- measuring whether nonlinear embeddings amplify observational noise;
- testing nearest-neighbor stability under small perturbations; and
- separating repeatable manifold structure from stochastic UMAP variation.

The project does not artificially introduce differential equations,
quadrature, or other course topics that are not required by the scientific
problem. Its central computational question is:

> How reliably do linear and nonlinear dimensionality-reduction algorithms
> preserve physically meaningful class information when their inputs contain
> measurement uncertainty, algebraic redundancy, finite-precision effects,
> and sampling variation?

## References

1. Schweder-Souza, N., Chies-Santos, A. L., de Souza, R. S., et al. (2026).
   “The contribution of the color space in LSST-like photometry for the
   selection of extragalactic globular cluster candidates.” *The
   Astrophysical Journal*, **1005**(1), 96.
   [doi:10.3847/1538-4357/ae7321](https://doi.org/10.3847/1538-4357/ae7321).
2. McInnes, L., Healy, J., and Melville, J. (2018). “UMAP: Uniform Manifold
   Approximation and Projection for Dimension Reduction.”
   [arXiv:1802.03426](https://arxiv.org/abs/1802.03426).
