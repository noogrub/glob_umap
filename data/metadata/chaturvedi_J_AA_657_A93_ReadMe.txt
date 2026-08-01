J/A+A/657/A93       Fornax globular clusters                 (Chaturvedi+, 2022)
================================================================================
The Fornax Cluster VLT Spectroscopic Survey. III.
Kinematical characterisation of globular clusters in the Fornax galaxy cluster.
    Chaturvedi A., Hilker M., Cantiello M., Napolitano N.R., van de Ven G.,
    Spiniello C., Fahrion K., Paolillo M., Gatto M., Puzia T.
    <Astron. Astrophys. 657, A93 (2022)>
    =2022A&A...657A..93C        (SIMBAD/NED BibCode)
================================================================================
ADC_Keywords: Clusters, galaxy ; Clusters, globular ; Photometry, SDSS
Keywords: catalogs - galaxies: clusters: individual: Fornax -
          galaxies: star clusters: general - galaxies: kinematics and dynamics

Abstract:
    The Fornax cluster provides an unparalleled opportunity of
    investigating the formation and evolution of early-type galaxies in a
    dense environment in detail. We aim at kinematically characterising
    photometrically detected globular cluster (GC) candidates in the core
    of the cluster. We used VLT/VIMOS spectroscopic data from the FVSS
    survey in the Fornax cluster, covering one square degree around the
    central massive galaxy NGC 1399. We confirm a total of 777 GCs, almost
    doubling previously detected GCs, using the same dataset as was used
    before. Combined with previous literature radial velocity measurements
    of GCs in Fornax, we compile the most extensive spectroscopic GC
    sample of 2341 objects in this environment. We found that red GCs are
    mostly concentrated around major galaxies, while blue GCs are
    kinematically irregular and are widely spread throughout the core
    region of the cluster. The velocity dispersion profiles of blue and
    red GCs show a quite distinct behaviour. Blue GCs exhibit a sharp
    increase in the velocity dispersion profile from 250 to 400km/s within
    5 arcminutes (~29kpc~1r_eff_ of NGC 1399) from the central galaxy.
    The velocity dispersion profile of red GCs follows a constant value
    between 200-300km/s until 8 arcminutes (~46kpc~1.6r_eff_, and then
    rises to 350km/s at 10 arcminutes (~58kpc~2r_eff_). Beyond 10
    arcminutes and out to 40 arcminutes (~230kpc~8r_eff_), blue and red
    GCs show a constant velocity dispersion of 300+/-50km/s, indicating
    that both GC populations trace the cluster potential. We kinematically
    confirm and characterise the previously photometrically discovered
    overdensities of intra-cluster GCs. We found that these substructured
    intra-cluster regions in Fornax are dominated mostly by blue GCs.

Description:
    This file contains the catalogue of spectroscopically confirmed
    globular clusters. Column list:(1) GC named as in the VIMOS pointing
    id; (2) CGs named as in the FVSS ID (FVSSIIIGC:RA-DEC); (3) right
    ascension; (4) declination; (5) GC radial velocity; (6) radial
    velocity uncertainty; (7) spectral S/N; (8) GC object class; (9) FDS
    ID (10) right ascension (FDS); (11) declination (FDS); (12-13) g-band
    magnitude with error; (14-15) r-band magnitude and its error; (16-17)
    i-band magnitude and its error; (18-19) u-band magnitude and its
    error.

    Magnitude information for each GC in g,r, i, and u band were obtained
    from the matched FDS photometric catalogue presented by Cantiello et
    al. (2020A&A...639A.136C, Cat. J/A+A/639/A136).

File Summary:
--------------------------------------------------------------------------------
 FileName      Lrecl  Records   Explanations
--------------------------------------------------------------------------------
ReadMe            80        .   This file
catalog.dat      234      851   Catalogue of spectroscopically confirmed
                                 globular clusters
--------------------------------------------------------------------------------

See also:
   J/A+A/639/A136 : The Fornax Deep Survey with the VST. IX. (Cantiello+, 2020)

Byte-by-byte Description of file: catalog.dat
--------------------------------------------------------------------------------
   Bytes Format Units  Label      Explanations
--------------------------------------------------------------------------------
   1- 26  A26   ---    PointName  GC named as in the VIMOS pointing id
  28- 56  A29   ---    FVSS-GC    CGs named as in the FVSS ID (FVSSIIIGC:RA-DEC)
  58- 75 F18.15 deg    RAdeg      Right ascension (J2000)
  77- 95 F19.15 deg    DEdeg      Declination (J2000)
  97-103  F7.2  km/s   RV         GC radial velocity
 105-110  F6.2  km/s e_RV         GC radial velocity uncertainty
 112-130 F19.16 ---    S/N        Spectral signal to noise ratio
     132  A1    ---    Class      [ABC] GC object class
 134-156  A23   ---    FDS        FDS ID, FDSJHHMMSS.ss+DDMMSS.ss (1)
 158-167  F10.7 deg    RAFdeg     ?=- Right ascension  (FDS) (1)
 169-178  F10.6 deg    DEFdeg     ?=- Declination (FDS) (1)
 180-185  F6.3  mag    gmag       ?=- g band PSF corrected magnitude (1)
 187-192  F6.4  mag  e_gmag       ?=- rms uncertainty g-band magnitude (1)
 194-199  F6.3  mag    rmag       ?=- r band PSF corrected magnitude (1)
 201-206  F6.4  mag  e_rmag       ?=- rms uncertainty r-band magnitude (1)
 208-213  F6.3  mag    imag       ?=- i band PSF corrected magnitude (1)
 215-220  F6.4  mag  e_imag       ?=- rms uncertainty i-band magnitude (1)
 222-227  F6.3  mag    umag       ?=- u band PSF corrected magnitude (1)
 229-234  F6.4  mag  e_umag       ?=- rms uncertainty u-band magnitude (1)
--------------------------------------------------------------------------------
Note (1): from Cantiello et al. (2020A&A...639A.136C, Cat. J/A+A/639/A136).
--------------------------------------------------------------------------------

Acknowledgements:
    Avinash Chaturvedi, avinash.chaturvedi(at)eso.org

References:
    Pota et al.,      Paper I   2018MNRAS.481.1744P
    Spiniello et al., Paper II  2018MNRAS.477.1880S

================================================================================
(End)                                        Patricia Vannier [CDS]  27-Dec-2021
