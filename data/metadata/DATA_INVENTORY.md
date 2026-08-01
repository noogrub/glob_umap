# Fornax LSST-like source data inventory

## Adopted field

- Center: right ascension `54.6205 deg`, declination `-35.4498 deg` (J2000)
- Radius: `1.0 deg`
- This center reproduces the paper's stated DES count of `395,813` objects exactly.
- The paper does not state the center numerically, so this value is an inference from the reported count and should be confirmed with the authors.

## FDS source catalog

- Catalog: `J/A+A/639/A136/fds`
- Source: VizieR / CDS, Cantiello et al. (2020)
- Local file: `data/raw/fds/fds_ngc1399_1deg.csv`
- Rows: `239,158`
- Columns: `51`
- Duplicate `ID` values: `0`

Columns:

`recno`, `ID`, `RAJ2000`, `DEJ2000`, `umag`, `e_umag`, `gmag`, `e_gmag`,
`rmag`, `e_rmag`, `imag`, `e_imag`, `CS`, `CIn`, `FR`, `FWHM`, `Aw`, `Bw`,
`Elo`, `Flags`, `Sharp`, `CSu`, `CIun`, `Sharpu`, `umagex8`, `e_umagex8`,
`umagauto`, `e_umagauto`, `CSg`, `CIgn`, `Sharpg`, `gmagex8`, `e_gmagex8`,
`gmagauto`, `e_gmagauto`, `CSr`, `CIrn`, `Sharpr`, `rmagex8`, `e_rmagex8`,
`rmagauto`, `e_rmagauto`, `CSi`, `CIin`, `Sharpi`, `imagex8`, `e_imagex8`,
`imagauto`, `e_imagauto`, `E(B-V)`, `Field`

Primary analysis fields:

- `ID`: FDS source identifier and label-join key.
- `RAJ2000`, `DEJ2000`: J2000 sky position in degrees.
- `umag`, `e_umag`: FDS PSF-corrected u magnitude and uncertainty used by the paper.
- `gmag`, `rmag`, `imag` and errors: FDS PSF photometry retained for survey-seam diagnostics.
- `CS`, `CIn`, `FR`, `FWHM`, `Elo`, `Sharp`: morphology diagnostics.
- `E(B-V)`: Schlafly-Finkbeiner reddening estimate.

Authoritative descriptions and fixed-width formats are in
`data/metadata/fds_J_AA_639_A136_ReadMe.txt`.

## DES DR2 source catalog

- Catalogs: `des_dr2.main` joined to `des_dr2.mag` on `coadd_object_id`
- Source: NOIRLab Astro Data Lab
- Local exact-cone file: `data/raw/des/des_dr2_ngc1399_1deg.csv`
- Rows: `395,813`
- Columns: `27`
- Duplicate `coadd_object_id` values: `0`

Columns:

`coadd_object_id`, `ra`, `dec`, `alphawin_j2000`, `deltawin_j2000`,
`extended_class_coadd`, `extended_class_wavg`, `ebv_sfd98`, `mag_auto_i`,
`mag_auto_i_dered`, `spread_model_i`, `spreaderr_model_i`, `class_star_i`,
`flux_radius_i`, `fwhm_image_i`, `flags_i`, `imaflags_iso_i`,
`mag_aper_5_g`, `magerr_aper_5_g`, `mag_aper_5_r`, `magerr_aper_5_r`,
`mag_aper_5_i`, `magerr_aper_5_i`, `mag_aper_5_z`, `magerr_aper_5_z`,
`mag_aper_5_y`, `magerr_aper_5_y`

Primary analysis fields:

- `coadd_object_id`: DES source identifier.
- `ra`, `dec`: indexed J2000 position used for the source-region query.
- `alphawin_j2000`, `deltawin_j2000`: full-precision J2000 position.
- `extended_class_coadd`: `0` high-confidence star, `1` candidate star,
  `2` mostly galaxy, `3` high-confidence galaxy, `-9` unavailable.
- `mag_auto_i`: magnitude used in the paper's star/galaxy label cuts.
- `mag_aper_5_{g,r,i,z,y}` and corresponding errors: 11.11-pixel diameter
  circular-aperture photometry used in the final LSST-like vector.
- `spread_model_i`, `class_star_i`, `flux_radius_i`, `fwhm_image_i`: morphology
  variables retained for boundary-expansion experiments.

DES uses `99` as a missing/sentinel magnitude in these exports. Sentinel counts
in the exact cone are:

- g: `10,147`
- r: `2,266`
- i: `2,048`
- z: `5,731`
- y: `62,153`

The complete table-level schemas downloaded from `TAP_SCHEMA.columns` are in:

- `data/metadata/des_dr2_main_columns.csv`
- `data/metadata/des_dr2_mag_columns.csv`

## Globular-cluster label catalogs

### Cantiello et al. (2020) master catalog

- Local file: `data/raw/fds/mastergc.dat`
- Rows: `3,263`
- Spectroscopic flag `Yes`: `1,342`
- Photometric flag `Yes` and spectroscopic flag not `Yes`: `1,921`
- Columns: `ID`, `RAdeg`, `DEdeg`, `umag`, `e_umag`, `gmag`, `e_gmag`,
  `rmag`, `e_rmag`, `imag`, `e_imag`, `CS`, `CIn`, `FR`, `FWHM`, `Elo`,
  `Sharp`, `E(B-V)`, `Field`, `FCC`, `pGC`, `rh2`, `Phot`, `Spect`.

This resolves the apparent `2,104` photometric flags: `183` objects have both
photometric and spectroscopic confirmation, leaving exactly `1,921`
photometric-only objects as stated in the paper.

### Chaturvedi et al. (2022) spectroscopic catalog

- Catalog: `J/A+A/657/A93/catalog.dat`
- Local file: `data/raw/chaturvedi/catalog.dat`
- Rows: `851`
- Rows with spectral signal-to-noise ratio at least 3: `825`
- Columns: `PointName`, `FVSS-GC`, `RAdeg`, `DEdeg`, `RV`, `e_RV`, `S/N`,
  `Class`, `FDS`, `RAFdeg`, `DEFdeg`, `gmag`, `e_gmag`, `rmag`, `e_rmag`,
  `imag`, `e_imag`, `umag`, `e_umag`.

The paper's intermediate counts `296`, `292`, and `268` cannot be recovered
from simple ID membership and the stated signal-to-noise cut alone. Reproducing
them requires the authors' exact deduplication, FDS-labeling, and DES-matching
sequence.

## Intermediate files

- `data/raw/des/des_dr2_ngc1399_box.csv` is the lossless bounding-box export
  used before the local exact spherical cut.
- `data/metadata/fds_sync_export_incomplete.csv` is retained as evidence that
  VizieR's synchronous endpoint silently truncated a large query. It must not
  be used for analysis.
- The four `fds_ngc1399_{a,b,c,d}.csv` files are verified asynchronous TAP
  partitions whose header-normalized union is the final FDS cone file.
