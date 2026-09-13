# Core Computation Plan

The core computation will work like this:

- Load the frozen development features.
- Convert them to a controlled numerical representation.
- Split the development data into five folds.
- Within each fold:
- fit the standardizer;
- fit identity, PCA, or UMAP;
- fit the classifier;
- predict the held-out fold.
- Compare the out-of-fold predictions.
- deterministically select a method and decision threshold.
- Freeze that selection before accessing the final test set.
- Later, measure uncertainty and UMAP stability without retuning.

## Here is what each new setting controls.

| Setting | Why it exists | How the code uses it |
|---|---|---|
| `Numerical dtype` | Floating-point precision affects scaling, SVD, distances, and probability calculations | Database values become NumPy arrays of the declared type; every numerical boundary verifies that type |
| `Finite-value policy` | NaN and infinity can arise from bad inputs, division by zero, overflow, or failed transformations | Validation runs after loading, scaling, embedding, and prediction; our initial policy will be reject/halt immediately
| `SVD driver` | PCA requires a singular-value decomposition | Our fit_pca() function calls scipy.linalg.svd() using the configured LAPACK driver |
| `Rank tolerance` | Very small singular values may be numerical noise rather than meaningful dimensions | pca_diagnostics() compares singular values with the configured tolerance to determine numerical rank |
| `Selection tie rule` | Two candidates can have equal or nearly equal evaluation scores | select_candidate() uses a stated tolerance and deterministic secondary rule |
| `Monte Carlo model` | Reported photometric errors must be translated into simulated measurements | draw_magnitudes() samples six magnitudes under the configured distribution and assumptions |
| `Monte Carlo seeds` | Random uncertainty simulations must be reproducible | Each realization receives a declared seed |
| `Stability neighborhoods` | UMAP coordinates cannot be compared directly across seeds | We compare the sets of each object’s nearest neighbors at configured values of $k$ |
| `Result paths` | Selection must be preserved before final testing | Tuning, selection, evaluation, and robustness outputs go to explicitly named artifacts |
| `Progress interval` | UMAP and repeated calculations may run for a long time | Long loops report status after the configured number of seconds |

Two distinctions are important.

The finite-value policy is not an imputation policy. Missing catalogue measurements were already handled during sample construction. Here, reject means that a numerical calculation must stop if it unexpectedly produces NaN or infinity. We do not quietly drop an object from the frozen sample.

We will not write an SVD algorithm. We will write the procedure around a maintained implementation: `scipy.linalg.svd(...)`
Our code remains responsible for centering the training matrix, invoking SVD correctly, retaining components, transforming new data without refitting, calculating rank and explained variance, and enforcing fold boundaries. That is the scientifically relevant numerical work.

For numerical rank, a principled starting rule is:

$$ \text{tolerance} = \max(n,p)\,\epsilon\,\sigma_{\max}, $$

where $n \times p$ is the matrix shape, $\epsilon$ is machine precision for the configured dtype, and $\sigma_{\max}$ is the largest singular value. The YAML should state that policy and any multiplier, rather than contain an arbitrary absolute cutoff.

