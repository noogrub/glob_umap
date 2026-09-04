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
