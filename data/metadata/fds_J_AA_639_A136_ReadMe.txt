J/A+A/639/A136      The Fornax Deep Survey with the VST. IX.  (Cantiello+, 2020)
================================================================================
The Fornax Deep Survey with the VST. IX. The catalog of sources in the FDS area,
with an example study for globular clusters and background galaxies.
    Cantiello M., Venhola A., Grado A., Paolillo M., D'Abrusco R., Raimondo G.,
    Quintini M., Hilker M., Mieske S., Tortora C., Spavone M., Capaccioli M.,
    Iodice E., Peletier R., Barroso J.F., Limatola L., Napolitano N.,
    Schipani P., van de Ven G., Gentile F., Covone G.
    <Astron. Astrophys. 639, A136 (2020)>
    =2020A&A...639A.136C        (SIMBAD/NED BibCode)
================================================================================
ADC_Keywords: Clusters, galaxy ; Galaxies, photometry ; Photometry, SDSS ;
              Morphology ; Clusters, globular
Keywords: galaxies: elliptical and lenticular, cD -
          galaxies: star clusters: general -
          galaxies: individual: NGC 1316, NGC 1399 -
          galaxies: clusters: individual: Fornax - galaxies: evolution -
          galaxies: stellar content

Abstract:
    A possible pathway for understanding the events and the
    mechanisms involved in galaxy formation and evolution is an in-depth
    comprehension of the galactic and inter-galactic fossil sub-structures
    with long dynamical times-scales: stars in the field and in stellar
    clusters.

    This paper continues the series of the Fornax Deep Survey (FDS).
    Following the previous studies dedicated to extended Fornax cluster
    members, in this paper we present the catalogs of compact stellar
    systems in the Fornax cluster as well as extended background sources
    and point-like sources.

    We derive ugri photometry of ~1.7 million sources over the ~21 square
    degree area of FDS centered on the bright central galaxy NGC1399. For
    a wider area, of ~27 square degrees extending in the direction of
    NGC1316, we provide gri photometry for ~3.1 million sources. To
    improve the morphological characterization of sources we generate
    multi-band image stacks by coadding the best seeing gri-band single
    exposures with a cut at FWHM<=0.9". We use the multi-band stacks as
    master detection frames, with a FWHM improved by ~15% and a FWHM
    variability from field to field reduced by a factor of ~2.5 compared
    to the pass-band with best FWHM, namely the r-band. The identification
    of compact sources, in particular of globular clusters (GC), is
    obtained from a combination of photometric (e.g. colors, magnitudes)
    and morphometric (e.g. concentration index, elongation, effective
    radius) selection criteria, by also taking as reference the properties
    of sources with well-defined classification from spectroscopic or
    high-resolution imaging data.

    Using the FDS catalogs, we present a preliminary analysis of globular
    cluster (GC) distributions in the Fornax area. The study confirms and
    extends further previous results which were limited to a smaller
    survey area. We observe the inter-galactic population of GCs, a
    population of mainly blue GCs centered on NGC1399, extends over
    ~0.9Mpc, with an ellipticity ~0.65 and a small tilt in the direction
    of NGC1336. Several sub-structures extend over ~0.5Mpc along various
    directions. Two of these structures do not cross any bright galaxy;
    one of them appears to be connected to NGC1404, a bright galaxy close
    to the cluster core and particularly poor of GCs. Using the gri
    catalogs we analyze the GC distribution over the extended FDS area,
    and do not find any obvious GC sub-structure bridging the two
    brightest cluster galaxies, NGC1316 and NGC1399. Although NGC1316 is
    more than twice brighter of NGC1399 in optical bands, using gri data,
    we estimate a factor of ~3-4 richer GC population around NGC1399
    compared to NGC1316, out to galactocentric distances of ~40' or
    ~230kpc

Description:
    We derive ugri photometry of ~1.7 million sources over the ~21 square
    degree area of the Fornax Deep Survey (FDS) centered on the bright
    galaxy NGC1399 (fds.dat). For a wider area, of ~27 square degrees
    extending in the direction of NGC1316, we provide gri photometry for
    ~3.1 million sources (fdsex.dat). The identification of compact
    sources, globular clusters (GC) and ultra compact dwarf galaxies
    (UCD), is obtained from a combination of photometric and morphometric
    selection criteria taking as reference the properties of confirmed GCs
    and UCDs in the literature. The master tables of GC and UCD are also
    provided.

File Summary:
--------------------------------------------------------------------------------
 FileName     Lrecl  Records   Explanations
--------------------------------------------------------------------------------
ReadMe           80        .   This file
fds.dat         524  1682503   Sources position, ugri photometry and morphometry
                                for ~1.7 million sources in ~21 sq. degree area
                                of FDS
fdsex.dat       424  3112605   Sources position, gri photometry and morphometry
                                for ~3.1 million sources in ~27 sq. degree area
                                 of FDSex
mastergc.dat    167     3263  *Reference GCs catalog
masteruc.dat    158       68  *Reference UCDs catalog
--------------------------------------------------------------------------------
Note on mastergc.dat: with positions, ugri photometry, morphometry of the
  collection of GC with well-defined classification from spectroscopic or
  high-resolution imaging data.
Note on masteruc.dat: with positions, ugri photometry, morphometry of the
  collection of UCDs with well-defined classification from spectroscopic data.
--------------------------------------------------------------------------------

See also:
 J/A+A/608/A142 : FDS with VST. III. LSB galaxies (Venhola+, 2017)
 J/A+A/620/A165 : FDS with VST. IV. dwarf galaxies (Venhola+, 2018)
 J/A+A/623/A1   : FDS with VST. V. Isophote fit (Iodice+, 2019)

Byte-by-byte Description of file: fds.dat
--------------------------------------------------------------------------------
   Bytes Format Units   Label    Explanations
--------------------------------------------------------------------------------
   1- 23  A23   ---     ID       Source identification based on the IAU
                                  naming rules, FDSJHHMMSS.ss+DDMMSS.ss
  25- 33  F9.6  deg     RAdeg    Right ascension (J2000.0)
  35- 44  F10.6 deg     DEdeg    Declination (J2000.0)
  46- 51  F6.3  mag     umag     u-band PSF corrected magnitude
  53- 57  F5.3  mag   e_umag     Error on u-band PSF corrected magnitude
  59- 64  F6.3  mag     gmag     g-band PSF corrected magnitude
  66- 70  F5.3  mag   e_gmag     Error on g-band PSF corrected magnitude
  72- 77  F6.3  mag     rmag     r-band PSF corrected magnitude
  79- 83  F5.3  mag   e_rmag     Error on r-band PSF corrected magnitude
  85- 90  F6.3  mag     imag     i-band PSF corrected magnitude
  92- 96  F5.3  mag   e_imag     Error on i-band PSF corrected magnitude
  98-102  F5.3  ---     CS       SExtractor CLASS_STAR from the
                                  multi-band 'a'-stacks
 104-109  F6.3  ---     CIn      Normalized concentration index from 'a'-stacks
 111-116  E6.2  arcsec  FR       SExtractor Flux radius from the
                                  multi-band 'a'-stacks
 118-123  F6.2  arcsec  FWHM     Source FWHM from the multi-band 'a'-stacks
 125-131  E7.5  deg     Aw       SExtractor Profile RMS along major axis
                                  from 'a'-stacks
 133-139  E7.5  deg     Bw       SExtractor Profile RMS along minor axis
                                  from 'a'-stacks
 141-145  F5.2  ---     Elo      Elongation, major-to-minor axis ratio
                                  from 'a'-stacks
 147-148  I2    ---     Flags    Flags, based on SExtractor flags coding rules
 150-156  F7.3  ---     Sharp    DAOphot sharpness parameter
                                  from the 'a'-stacks
 158-171 E14.10 ---     CSu      ?=-99 [0/1] u-band SExtractor CLASS_STAR
 173-177  F5.3  ---     CIun     ?=-99 u-band normalized concentration index
 179-185  F7.3  ---     Sharpu   ?=-99 u-band DAOphot sharpness parameter
 187-200 E14.10 mag     umagex8  ?=-99 u-band aperture magnitude within 8 pixels
 202-215 E14.10 mag   e_umagex8  ?=-99 Error on u-band aperture magnitude within
                                  8 pixels
 217-230 E14.10 mag     umagauto ?=-99 SExtractor automated u-band aperture
                                  magnitude MAG_AUTO and
 232-245 E14.10 mag   e_umagauto ?=-99 Error on automated u-band aperture
                                  magnitude MAG_AUTO
 247-260 E14.10 ---     CSg      [0/1]?=-99 g-band SExtractor CLASS_STAR
 262-267  F6.3  ---     CIgn     g-band Normalized concentration index
 269-275  F7.3  ---     Sharpg   g-band DAOphot sharpness parameter
 277-290 E14.10 mag     gmagex8  ?=-99 g-band Aperture magnitude within 8 pixels
 292-305 E14.10 mag   e_gmagex8  ?=-99 Error on g-band Aperture magnitude within
                                  8 pixels
 307-320 E14.10 mag     gmagauto ?=-99 SExtractor g-band automated aperture
                                  magnitude MAG_AUTO
 322-335 E14.10 mag   e_gmagauto ?=-99 Error on g-band automated aperture
                                  magnitude MAG_AUTO
 337-350 E14.10 ---     CSr      [0/1]?=-99 r-band SExtractor CLASS_STAR
 352-357  F6.3  ---     CIrn     r-band Normalized concentration index
 359-365  F7.3  ---     Sharpr   r-band DAOphot sharpness parameter
 367-380 E14.10 mag     rmagex8  ?=-99 r-band Aperture magnitude within 8 pixels
 382-395 E14.10 mag   e_rmagex8  ?=-99 Error on r-band Aperture magnitude within
                                  8 pixels
 397-410 E14.10 mag     rmagauto ?=-99 SExtractor automated r-band aperture
                                  magnitude MAG_AUTO
 412-425 E14.10 mag   e_rmagauto ?=-99 Error on automated aperture r-band
                                  magnitude MAG_AUTO
 427-440 E14.10 ---     CSi      [0/1]?=-99 i-band SExtractor CLASS_STAR
 442-447  F6.3  ---     CIin     i-band Normalized concentration index
 449-455  F7.3  ---     Sharpi   i-band DAOphot sharpness parameter
 457-470 E14.10 mag     imagex8  ?=-99 Aperture i-band magnitude within 8 pixels
 472-485 E14.10 mag   e_imagex8  ?=-99 Error on Aperture i-band magnitude within
                                  8 pixels
 487-500 E14.10 mag     imagauto ?=-99 SExtractor automated aperture i-band
                                  magnitude MAG_AUTO
 502-515 E14.10 mag   e_imagauto ?=-99 Error on automated aperture i-band
                                  magnitude MAG_AUTO
 517-521  F5.3  mag     E(B-V)   Reddening from Schlafly & Finkbeiner
                                  (2011ApJ...737..103S)
 523-524  I2    ---     Field    [1/31] FDS field pointing ID
--------------------------------------------------------------------------------

Byte-by-byte Description of file: fdsex.dat
--------------------------------------------------------------------------------
   Bytes Format Units   Label    Explanations
--------------------------------------------------------------------------------
   1- 23  A23   ---     ID       Source identification based on the IAU
                                  naming rules, FDSJHHMMSS.ss+DDMMSS.ss
  25- 33  F9.6  deg     RAdeg    Right ascension (J2000.0)
  35- 44  F10.6 deg     DEdeg    Declination (J2000.0)
  46- 51  F6.3  mag     gmag     g-band PSF corrected magnitude
  53- 57  F5.3  mag   e_gmag     Error on g-band PSF corrected magnitude
  59- 64  F6.3  mag     rmag     r-band PSF corrected magnitude
  66- 70  F5.3  mag   e_rmag     Error on r-band PSF corrected magnitude
  72- 77  F6.3  mag     imag     i-band PSF corrected magnitude
  79- 83  F5.3  mag   e_imag     Error on i-band PSF corrected magnitude
  85- 89  F5.3  ---     CS       SExtractor CLASS_STAR from the
                                  multi-band 'a'-stacks
  91- 98  F8.3  ---     CIn      Normalized concentration index from 'a'-stacks
 100-105  E6.2  arcsec  FR       SExtractor Flux radius from the
                                  multi-band 'a'-stacks
 107-112  E6.2  arcsec  FWHM     Source FWHM from the multi-band 'a'-stacks
 114-120  E7.3  deg     Aw       SExtractor Profile RMS along major axis
                                  from 'a'-stacks
 122-128  E7.3  deg     Bw       SExtractor Profile RMS along minor axis
                                  from 'a'-stacks
 130-134  F5.2  ---     Elo      Elongation, major-to-minor axis ratio
                                  from 'a'-stacks
 136-137  I2    ---     Flags    Flags, based on SExtractor flags coding rules
 139-145  F7.3  ---     Sharp    DAOphot sharpness parameter from
                                  the 'a'-stacks
 147-160 E14.10 ---     CSg      ?=-99 g-band SExtractor CLASS_STAR
 162-167  F6.3  ---     CIgn     g-band Normalized concentration index
 169-175  F7.3  ---     Sharpg   g-band DAOphot sharpness parameter
 177-190 E14.10 mag     gmagex8  ?=-99 g-band Aperture magnitude within 8 pixels
 192-205 E14.10 mag   e_gmagex8  ?=-99 Error on g-band Aperture magnitude within
                                  8 pixels
 207-220 E14.10 mag     gmagauto ?=-99 g-band SExtractor automated aperture
                                  magnitude MAG_AUTO
 222-235 E14.10 mag   e_gmagauto ?=-99 g-band Error on automated aperture
                                  magnitude MAG_AUTO
 237-250 E14.10 ---     CSr      ?=-99 r-band SExtractor CLASS_STAR
 252-257  F6.3  ---     CIgr     r-band Normalized concentration index
 259-265  F7.3  ---     Sharpr   r-band DAOphot sharpness parameter
 267-280 E14.10 mag     rmagex8  ?=-99 r-band Aperture magnitude within 8 pixels
 282-295 E14.10 mag   e_rmagex8  ?=-99 Error on r-band Aperture magnitude within
                                  8 pixels
 297-310 E14.10 mag     rmagauto ?=-99 r-band SExtractor automated aperture
                                  magnitude MAG_AUTO
 312-325 E14.10 mag   e_rmagauto ?=-99 r-band Error on automated aperture
                                  magnitude MAG_AUTO
 327-340 E14.10 ---     CSi      ?=-99 i-band SExtractor CLASS_STAR
 342-347  F6.3  ---     CIin     i-band Normalized concentration index
 349-355  F7.3  ---     Sharpi   i-band DAOphot sharpness parameter
 357-370 E14.10 mag     imagex8  ?=-99 i-band Aperture magnitude within 8 pixels
 372-385 E14.10 mag   e_imagex8  ?=-99 Error on i-band Aperture magnitude within
                                  8 pixels
 387-400 E14.10 mag     imagauto ?=-99 i-band SExtractor automated aperture
                                  magnitude MAG_AUTO
 402-415 E14.10 mag   e_imagauto ?=-99 i-band Error on automated aperture
                                  magnitude MAG_AUTO
 417-421  F5.3  mag     E(B-V)   Reddening from Schlafly & Finkbeiner
                                  (2011ApJ...737..103S)
 423-424  I2    ---     Field    [1/31] FDS field pointing ID
--------------------------------------------------------------------------------

Byte-by-byte Description of file: mastergc.dat
--------------------------------------------------------------------------------
   Bytes Format Units   Label     Explanations
--------------------------------------------------------------------------------
   1- 23  A23   ---     ID        Source identification based on the IAU
                                   naming rules, FDSJHHMMSS.ss+DDMMSS.ss
  25- 33  F9.6  deg     RAdeg     Right ascension (J2000.0)
  35- 44  F10.6 deg     DEdeg     Declination (J2000.0)
  46- 51  F6.3  mag     umag      u-band PSF corrected magnitude
  53- 57  F5.3  mag   e_umag      error on u-band PSF corrected magnitude
  59- 64  F6.3  mag     gmag      g-band PSF corrected magnitude
  66- 70  F5.3  mag   e_gmag      error on g-band PSF corrected magnitude
  72- 77  F6.3  mag     rmag      r-band PSF corrected magnitude
  79- 83  F5.3  mag   e_rmag      error on r-band PSF corrected magnitude
  85- 90  F6.3  mag     imag      i-band PSF corrected magnitude
  92- 96  F5.3  mag   e_imag      error on i-band PSF corrected magnitude
  98-102  F5.3  ---     CS        SExtractor CLASS_STAR from the multi-band
                                   'a'-stacks
 104-109  F6.3  ---     CIn       Normalized concentration index from 'a'-stacks
 111-117  F7.2  arcsec  FR        SExtractor Flux radius from the
                                   multi-band 'a'-stacks
 119-123  F5.2  arcsec  FWHM      Source FWHM from the multi-band 'a'-stacks
 125-128  F4.2  ---     Elo       Elongation, major-to-minor axis ratio -
                                   from 'a'-stacks
 130-135  F6.3  ---     Sharp     DAOphot sharpness parameter
                                   from the 'a'-stacks
 137-141  F5.3  mag     E(B-V)    Reddening from Schlafly & Finkbeiner
                                   (2011ApJ...737..103S)
 143-144  I2    ---     Field     FDS field pointing ID
 146-148  I3    ---     FCC       [47/335]? Fornax cluster catalog ID of the
                                   host galaxy
 150-153  F4.2  ---     pGC       [0/1]? pGC likelihood from Jordan et al.
                                   (2015ApJS..221...13J, Cat. J/ApJS/221/13)
 155-159  F5.3  arcsec  rh2       ? Mean g and z GC half light radius
 161-163  A3    ---     Phot      [Yes/No ] GC identified from ACSFCS
                                   imaging data
 165-167  A3    ---     Spect     [Yes/No ] GC identified through
                                   spectroscopic data
--------------------------------------------------------------------------------


Byte-by-byte Description of file: masteruc.dat
--------------------------------------------------------------------------------
   Bytes Format Units   Label     Explanations
--------------------------------------------------------------------------------
   1- 23  A23   ---     ID        Source identification based on the IAU
                                   naming rules, FDSJHHMMSS.ss+DDMMSS.ss
  25- 33  F9.6  deg     RAdeg     Right ascension (J2000.0)
  35- 44  F10.6 deg     DEdeg     Declination (J2000.0)
  46- 51  F6.3  mag     umag      u-band PSF corrected magnitude
  53- 57  F5.3  mag   e_umag      error on u-band PSF corrected magnitude
  59- 64  F6.3  mag     gmag      g-band PSF corrected magnitude
  66- 70  F5.3  mag   e_gmag      error on g-band PSF corrected magnitude
  72- 77  F6.3  mag     rmag      r-band PSF corrected magnitude
  79- 83  F5.3  mag   e_rmag      error on r-band PSF corrected magnitude
  85- 90  F6.3  mag     imag      i-band PSF corrected magnitude
  92- 96  F5.3  mag   e_imag      error on i-band PSF corrected magnitude
  98-102  F5.3  ---     CS        SExtractor CLASS_STAR from the
                                   multi-band 'a'-stacks
 104-108  F5.3  ---     CIn       Normalized concentration index from 'a'-stacks
 110-113  F4.2  arcsec  FR        SExtractor Flux radius from the
                                  multi-band 'a'-stacks
 115-118  F4.2  arcsec  FWHM      Source FWHM from the multi-band 'a'-stacks
 120-123  F4.2  ---     Elo       Elongation, major-to-minor axis ratio
                                   from 'a'-stacks
 125-130  F6.3  ---     Sharp     DAOphot sharpness parameter
                                   from the 'a'-stacks
 132-136  F5.3  mag     E(B-V)    Reddening from Schlafly & Finkbeiner
                                   (2011ApJ...737..103S)
 138-139  I2    ---     Field     [6/16] FDS field pointing ID
 141-147  F7.2  km/s    HV        Heliocentric velocity from the literature
 149-154  F6.2  km/s  e_HV        Error on heliocentric velocity
 156-158  A3    ---   r_HV        Reference for the heliocentric velocity (1)
--------------------------------------------------------------------------------
Note (1): References as follows:
   K99: Kissler-Patig et al. (1999AJ....117.1206K)
   M04: Mieske et al. (2004A&A...418..445M, Cat. J/A+A/418/445)
   F07: Firth et al. (2007MNRAS.382.1342F, Cat. J/MNRAS/382/1342)
   B07: Bergond et al. (2007A&A...464L..21B, Cat. J/A+A/464/L21)
   M08: Mieske et al. (2008A&A...487..921M)
   G09: Gregg et al. (2009AJ....137..498G, Cat. J/AJ/137/498)
   S10: Schuberth et al. (2010A&A...513A..52S, Cat. J/A+A/513/A52)
   P18: Pota et al. (2018MNRAS.481.1744P)
--------------------------------------------------------------------------------

Acknowledgements:
    Michele Cantiello, michele.cantiello(at)inaf.it

References:
    Iodice et al.,  Paper I    2016ApJ...820...42I
    Iodice et al.,  Paper II   2017ApJ...839...21I
    Venhola et al., Paper III  2017A&A...608A.142V, Cat. J/A+A/608/A142
    Venhola et al., Paper IV   2018A&A...620A.165V, Cat. J/A+A/620/A165
    Iodice et al.,  Paper V    2019A&A...623A...1I, Cat. J/A+A/623/A1
    Venhola et al., Paper VI   2019A&A...625A.143V
    Raj et al.,     Paper VII  2019A&A...628A...4R
    Spavone et al., Paper VIII 2019A&A...639A..14S

================================================================================
(End)                                        Patricia Vannier [CDS]  25-May-2020
