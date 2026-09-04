# P609, E584, and Rubin Project

## Working concept

This project combines three related fields:

1. **Scientific computation:** reproduce and extend a published globular-cluster classification experiment using PCA, reconstruction autoencoders, and UMAP.
2. **Scientific visualization:** construct an interactive ParaView representation of the Fornax source population, its learned photometric manifold, uncertainty, and temporal behavior.
3. **Radiation effects and electronics reliability:** determine how radiation-associated and detector-reliability artifacts propagate from CCD measurements into photometry, learned representations, and classification decisions.

The protected scientific core is intentionally narrower than the complete visualization project. This allows the core experiment to produce a defensible paper even if the class project grows in other directions.

## Central scientific questions

### Paper core

> Does neighborhood-preserving dimensionality reduction reveal stable, discriminative globular-cluster structure in multiband photometry that PCA and reconstruction autoencoders fail to retain?

### Reliability extension

> How do radiation-associated and detector-reliability artifacts propagate from CCD pixels into photometry, UMAP geometry, and globular-cluster classification?

### Visualization question

> How can physical detector space, astronomical sky coordinates, photometric feature space, learned latent space, uncertainty, and time be shown together without implying structure that the analysis has not established?

## Nested project scopes

| Scope | Required result |
|---|---|
| Paper core | Reproduce the published PCA and autoencoder benchmark and test whether UMAP improves globular-cluster classification under identical conditions |
| Reliability extension | Measure how configured radiation-informed detector faults alter measured photometry, manifold position, and classification |
| E584 visualization | Show the propagation from detector space through photometry into latent space using ParaView |

The paper core proceeds regardless of group membership. The reliability and visualization layers may strengthen it, but they must not redefine or delay it.

## Repository and collaboration boundary

The individual P609 research remains in the private `glob_umap` repository.
If an E584 group forms, collaborative ParaView work will reside in a separate
repository on `github.iu.edu`.

The interface between the projects will be a versioned, documented export
rather than shared internal code or database access. The P609 project produces
ParaView-ready datasets and manifests. The E584 project consumes those exports
and owns collaborative visualization code, state files, and presentation
materials. This boundary permits independent progress and protects the paper
core from group-driven scope changes.

## Existing data foundation

The verified source bundle contains:

- FDS (ugri): 239,158 objects and 51 columns;
- DES DR2 (grizY): 395,813 objects and 27 selected columns;
- FDS master globular-cluster catalogue: 3,263 objects;
- Chaturvedi spectroscopic catalogue: 851 objects;
- authoritative schemas, provenance, query geometry, and checksums.

These data support immediate construction of the static Fornax photometric manifold. Rubin observations may later add genuine temporal and detector-level information.

## The evolving Fornax manifold

The proposed ParaView dataset represents each astronomical source as a persistent object with attributes such as:

- canonical object identifier;
- right ascension and declination;
- detector, amplifier, and pixel coordinates when available;
- observation identifier and time;
- (ugrizY) photometry and uncertainties;
- globular-cluster, star, or galaxy label evidence;
- morphology measurements;
- PCA and UMAP coordinates;
- classifier score or probability;
- neighborhood membership and stability;
- detector artifact flags;
- fault-model parameters;
- raw, corrected, and perturbed measurements.

This supports several coordinated views:

1. the Fornax field in sky coordinates;
2. the same sources in a three-dimensional learned manifold;
3. a nearest-neighbor graph showing local topology;
4. uncertainty clouds or trajectories around individual objects;
5. detector-position maps of transient and persistent artifacts;
6. temporal trajectories as repeated Rubin observations become available;
7. classification boundaries and objects that cross them.

The most distinctive visualization follows the same object through:

[
	ext{detector position}
ightarrow
	ext{pixel artifact}
ightarrow
	ext{photometric change}
ightarrow
	ext{latent displacement}
ightarrow
	ext{classification outcome}.
]

ParaView exports may include:

- VTK PolyData (`.vtp`) point clouds;
- graph geometry for nearest-neighbor relationships;
- PVD (`.pvd`) collections for temporal sequences;
- volumetric density fields for overlap regions;
- image, variance, and mask-derived attributes where accessible.

## Rubin and radiation effects

The Vera C. Rubin Observatory is ground-based at Cerro Pachón and has no orbital focal-plane components. Its CCDs therefore do not experience the same radiation environment as spaceborne instruments. However, Rubin exposures and processing include reliability phenomena relevant to this project:

- transient cosmic-ray tracks;
- known bad or suspect pixels;
- hot pixels and columns;
- dark-response changes;
- charge-transfer and readout artifacts;
- residual defects that survive calibration or interpolation.

A cosmic-ray track is a transient radiation effect. A bad pixel is not, by itself, evidence of radiation damage. Manufacturing variation, temperature, aging, and electronics can produce similar symptoms. We must not assign a radiation cause without supporting evidence.

Rubin's processing pipeline explicitly repairs cosmic-ray hits, masks known bad pixels, and maintains image, variance, and mask planes:

- [Rubin Observatory facilities](https://rubinobservatory.org/about/organization)
- [Rubin CCD processing](https://pipelines.lsst.io/v/v24_1_1/modules/lsst.pipe.tasks/tasks/lsst.pipe.tasks.processCcd.ProcessCcdTask.html)
- [Instrument signature removal](https://pipelines.lsst.io/py-api/lsst.ip.isr.IsrTask.html)

## Radiation-informed fault experiment

The reliability extension should use controlled, YAML-defined fault models rather than presume that every observed defect was radiation-induced.

Candidate faults include:

- particle tracks with configurable geometry and deposited charge;
- isolated transient pixel excursions;
- persistent hot pixels or columns;
- charge loss;
- charge-transfer-like trailing;
- amplifier-correlated offsets;
- increasing defect density or severity.

The experimental sequence is:

1. select representative source images or photometric observations;
2. apply a configured fault realization;
3. repeat the relevant calibration and photometric measurement;
4. transform the changed feature vector through the fixed representation;
5. record latent displacement and classification change;
6. repeat across fault parameters, seeds, source classes, and measurement uncertainty;
7. identify the fault regimes where scientific inference becomes unreliable.

The first pilot may perturb catalogue photometry. A stronger experiment will inject faults at image or cutout level and then remeasure the photometry.

## Representation constraint

UMAP coordinates are not intrinsically aligned across independent fits. Re-fitting UMAP for each epoch could create apparent motion through arbitrary rotation, reflection, or nonlinear distortion.

Temporal work should therefore use either:

- a reference UMAP fitted once, with later observations transformed into that fixed space; or
- an explicitly justified alignment procedure whose residual uncertainty is measured.

A visually attractive embedding is not itself scientific evidence. PCA, UMAP, and autoencoder representations must receive identical populations, features, scaling, missing-data treatment, labels, and train/test partitions.

## Immediate sprint: September 4–14

The goal for September 14 is a concrete demonstration capable of attracting the two E584 students interested in astrophysics.

Target outputs:

- PostgreSQL schema and verified catalogue ingestion;
- reproducible population counts and crossmatches;
- canonical five-color feature table;
- PCA baseline;
- preliminary two- and three-dimensional UMAP embeddings across several seeds;
- initial precision-recall comparison;
- first ParaView-compatible VTP point cloud;
- concise one-page project description;
- Fornax population and selection-funnel figure;
- PCA-versus-UMAP figure;
- three-dimensional UMAP view colored by class evidence or probability.

A small radiation pilot is desirable but secondary. It may perturb selected photometric vectors with one simple configured fault model and show their movement through the fixed latent space.

The recruiting summary is:

> We already have nearly 635,000 Fornax-region source records, verified labels, and a reproducible computational design. We are building an interactive visualization that follows astronomical objects from CCD measurement uncertainty through a learned color manifold to classification success or failure.

## Semester milestones

| Date | Course milestone | Internal scientific gate |
|---|---|---|
| **September 14** | Potential ideas and datasets | Real data, preliminary embeddings, early quantitative result, and ParaView dataset |
| **September 28** | Project groups formed | Published benchmark substantially reproduced and group roles defined |
| **October 19** | Group plan presented | Design frozen, uncertainty and radiation experiments specified, and visualization prototype operating |
| **November 2** | Internal deadline | All principal computational experiments complete |
| **November 16** | Progress report | Results analyzed, principal figures chosen, and conclusions stable |
| **December 1** | Internal deadline | Paper-quality draft and final visualization complete |
| **December 7** | Group presentations begin | Project ready to present |
| **December 14** | Final presentation date | Contingency date rather than working deadline |

November 2 is the effective computational deadline. The remaining time is reserved for interpretation, justified checks, writing, visualization refinement, and presentation preparation.

## Completion levels

### Minimum successful project

- verified and reproducible dataset construction;
- faithful PCA benchmark;
- fair PCA-versus-UMAP evaluation;
- repeated UMAP seeds;
- full precision-recall analysis;
- defensible positive or negative conclusion.

### Strong final project

- published autoencoder benchmark reproduced;
- uncertainty perturbation study;
- neighborhood and embedding stability measurements;
- survey and band ablations;
- interactive ParaView representation.

### Paper trajectory

- image-level radiation-informed fault injection;
- repeated Rubin observations;
- physical detector coordinates and mask information;
- temporal latent trajectories;
- realistic boundary populations;
- external validation;
- astrophysical and electronics-reliability interpretation.

A negative UMAP result remains useful if the experiment establishes the information limit more rigorously than previous work.

## Scope protection

The following controls protect the scientific core from group-driven scope expansion:

- one fixed paper question;
- explicit success and stopping criteria;
- a versioned dataset contract;
- separate astronomy, reliability, and visualization modules;
- a decision log;
- a backlog for attractive but nonessential ideas;
- configuration-driven experiments;
- immutable raw data and recorded checksums;
- count ledgers at every filtering stage;
- resolved run configurations and random seeds;
- contribution records suitable for later authorship decisions.

The class project may expand. The paper core may not be silently displaced by that expansion.

## Potential contributor roles

Possible intellectual contributions include:

- **John Burgoon:** project architecture, dataset integration, computational experiments, UMAP analysis, and cross-domain synthesis;
- **Dr. Boettcher:** numerical design, computational-physics guidance, and uncertainty analysis;
- **Dr. Wernert:** scientific-visualization design, ParaView methodology, and visual validation;
- **Dr. Loveless:** radiation-informed fault models and electronics-reliability interpretation;
- **E584 collaborators:** substantive visualization design, implementation, evaluation, and astrophysical exploration;
- **astronomy collaborator, if one joins:** astronomical population construction, label interpretation, and astrophysical conclusions.

Authorship is not assigned in advance. It should reflect substantial, identifiable contributions to the final research.

## Immediate decision rule

Development should proceed in this order:

1. establish the trustworthy astronomical dataset;
2. reproduce the published computational baseline;
3. obtain the first controlled UMAP result;
4. export a useful ParaView dataset;
5. add the smallest defensible reliability experiment;
6. expand only when earlier stages are stable.

This order ensures that the project remains publishable even if Rubin access, image-level calibration products, or group collaboration arrive later than hoped.

## References

1. Schweder-Souza, N., Chies-Santos, A. L., de Souza, R. S., et al. (2026). “The contribution of the color space in LSST-like photometry for the selection of extragalactic globular cluster candidates.” *The Astrophysical Journal*, **1005**(1), 96. [https://doi.org/10.3847/1538-4357/ae7321](https://doi.org/10.3847/1538-4357/ae7321). [arXiv:2512.17644v2](https://arxiv.org/abs/2512.17644v2).
