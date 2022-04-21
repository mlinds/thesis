# Work Plan

## Introduction

## Lidar bathymetric survey

<!-- citations 21, 22, and 23 from forfinski et al explain the background  -->

<!-- notes from forfinski et al -->
- 1064 and 1550nm lasers are preferred for topograhic lidar
- 532nm laser better for bathymetric lidar
- photon-counting lidar allow low power consumption, so they are more practical from a satellite
- in waveform-resolving lidar, each point return is a pulse containing thousands of photons

### Mangroves as coastal protection
Sea level rise poses a threat to all coastal communities, including many of the world's largest population centers. The risk is even more existential for low-lying tropical commmunities, who have done little to contribute to the current climate crisis, but are disproportionatelly affected by the sea level rise. Low-lying nations often do not have any available high ground to move cities to, and sometimes don't have access to the resources to fully mitigate these risks through hard infrastrcture. For these reasons, mangroves forests are an important resource for these communities, providing coastal protection that can adapt to sea level rise by trapping sediment and expanding outward if conditions permit.

Current study of the effects of mangroves on wave attenuation are limited by the difficulty of gather data about these ecosystems.  Shallow water bathymetry and mangrove height are difficult to survey manually. Mangrove forests are extremely dense and field work is difficult. Therefore, finding an automated way of extracting this anywhere in the world from and publicly available data is a massive improvement when modeling sites that don't have existing survey data.

### ICESat-2
The ICESat-2 mission is inteded to gather high resolution topograhic data on a global scale. The satellite carries the Advanced Topographic Laser Altimeter System (ATLAS). ATLAS is a highly sensitive photon-counting, green-light LiDAR. The satellite instrument points at reference ground tracks (RGT) along the earth's surface with a repeat time of 91 days. Along the refence track, there are 3 beams, one pointing directly at the reference track, and two that are offset by approximately 3km on either side. 

![RBTref](../figures/ATLAS_beam_layout_from_user_guide.png)


Each of the 3 beams emits both a strong and weak beam, with the strong beam being approximately 4x more powerful [@Neumann]. Of the approximately $10^14$ of photons emitted per pulse, up to approximately 10 make it back to the sensor and are detected. [@neumannt.a.ATLASICESat2L2A2019]. The exact number of emmitted photons that subsequently detected at the sensor depends on the local atmospheric conditions and the reflectivity of the surface. [@Neumann]

![beams](../figures/3d_beam_view_from_atl03ATBD.png)[@Neumann]

To locate the position of each photon in 3D space, the time of flight of the photon is calculated with a precision of 800 ps [@Neumann2019d]. The location of the center of mass of the instrument is found using Global Positioning System (GPS) systems on board the satellite. By combining the measured time of flight and satellite position, the exact geolocation of the photon can be estimated with high accuracy [@Neumann2019d]. 
The photon gelocation data is distributed by NASA as the ATL03 data product[]

#### Weak Vs. Strong Beams
The beams are divided into weak and strong signals to enhance the radiometric dynamic range. The strong beams are expected to provide better signal-noise ratios over low-reflectively surfaces. [@Neumann2019d] Therefore, these beams are expected to provide the best data for radiometric bathymetry measurements. 

#### Vertical control 
The ATL03 data product reports the photon heights relative to the WGS84 reference ellipsoid. These ellipsoidal heights are calculated with corrections for:
- The solid earth tides
- Ocean loading
- Ocean Pole tide
- Wet and dry atmospheric delays

The height provided in ATL03 is calculated by the following equation:

$$H_{GC} =  H_{P} - H_{OPT} - H_{OL} - H_{SEPT} - H_{SET} - H_{TCA}$$

Where:
- $H_{GC}$ is the geophysically corrected photon height above the WGS84 ellipsoid
- $H_{P}$ is the raw photon height above the WGS84 ellipsoid
- $H_{OPT}$ is the height of the Ocean Pole tide
- $H_{OL}$ is the height of the ocean load tide
- $H_{SEPT}$ is the height of the solid earth pole tide
- $H_{SET}$ is the solid earth tide
- $H_{TCA}$ is the height of the total column atmospheric delay

Included in the data are the height of the tide-free geoid, the height difference between the tide-free and mean-tide geoid, and the height of the tide relative to the mean tide geoid as calculated by the GOT4.8 model. This GOT4.8 model tidal height is a based on a low resolution model, and therefore is less accurate in nearshore coastal areas and within embayments [@Neumann]. 

#### Signal Photon Identification

The ATL03 data product includes a calculated confidence that a given photon return is signal or noise, for each surface type. This is a rough estimate, but is reliable for detecting ocean surface photons. However, many photons classified as noise by this included algorithm appear to represent bathymetric returns. Therefore, to calculate the bathymetry, all photon returns, including those classified as noise by the ATL03 signal/noise algorithm are filtered to remove points that are too high or low to be considered bathymetric returns. Then, a seperate algorithm specifically calibrated to distinguish bathymetric signal from noise photons is applied to this data. 


### Satellite Derived bathymetry
#### Multispectral imagery
There are many techniques to approximate depth by the spectral signatures of optical satellite data. The two classical ones are the band-ratio model and the linear band model.

#### LiDAR bathymetry

Green light lasers can penetrate the water up to a certain depth based on the local water clarity. In very clear water depth detection of up to 40m has been achieved from spaceborne lasers [@parrishValidationICESat2ATLAS2019]. The laser path has to be corrected for refraction induced by the water before the bathymetry can be reliably estimated. 

## Background & Prior Research
The potential for bathymetric mapping using spaceborne laser observations has been known since before the advent of the IceSAT-2 mission. The predecessor mission carried a LiDAR instrument called the Geoscience Laser Altimeter System (GLAS). While GLAS was a green-light laser, it was intended for measuring atmospheric aerosols [ref 14 cited by@Forfinski2016]. However, because of the laser architecture, GLAS was not able to penetrate the water column [@Forfinski2016]. 

However, a prototype of ATLAS, called the Multiple Altimeter Beam Experimental Lidar (MABEL) instrument was tested with high-altitude aircraft missions, allowing a simulation of the data that would be transmitted by ATLAS. Early experiments with MABEL showed good agreement with high-quality airbone data [@Forfinski2016].

Since the IceSAT-2 satellite launched in 2018, there have been several studies that evaluate the data for bathymetric mapping purposes, and experiment with different techniques to distinguish signal from noise. One of the earlist and most cited is Parrish et al. (2019) [@Parrish2019]. The paper addresses refraction correction by manually segmenting bathymetric signal points, estimating the water surface based on photons returns classified as water surface, using the provided angle of incidence of the satellite. 

The Parrish paper includes correction for both horizontal and vertical effects of refraction. Most of the time, the instrument is pointed directly down at the RGT, so the laser beams are near the nadir. When directly on-nadir, the horizontal error induced by refraction is approximately 9cm [@Parrish2019], which for bathymetric purposes is negligible. 

However, by design ATLAS can point up to $5\degree$ off-nadir. The off-nadir pointing mode is used occassionaly to increase the density of tracks in the mid-latitudes. This allows better coverage of the vegetation canopy height, and incidentally, the mid-latitude coasts. When pointing off-nadir, the horizontal error is much more significant and must be corrected for accurate bathymetry. In all of these calculations, the water surface is assumed to be flat. 

Parrish et al. test their technique in 4 different regions: St. Thomas, Turks and Caicos, North West Australia, and the Great Bahama Bank.
<!-- summarize parrish results -->
In the Parrish paper, they suggest that the best use of lidar data for bathymetry is to combine it with optical/multispectral techniques. Because the lidar-derived data provides highly accurate point estimates along a certain track, and the multispectral approach allows the estimation for a 2D area, combining the two techniques provides a synergistic fusion of the strengths of both. The LiDAR-derived depths are used as training data for the multispectral models allowing an accurate 2d picture of the bathymetry.  

Further studies have implemented the combination of multispectral SDB that is calibrated using satellite data. This technique has shown promising results. 



### Summary of prior studies

| Author                  | Year | Dataset | refraction correction method             | S/N Classification method | Tide correction method | notes                   |
| ----------------------- | ---- | ------- | ---------------------------------------- | ------------------------- | ---------------------- | ----------------------- |
| Forfinski-Sarkozy et al | 2016 | MABEL   | First-order depth correction             | Manual                    | N/A                    | non-tidal               |
| Parrish et al.          | 2016 | ATLAS   | Parrish method                           | Manual                    | N/A                    | used ellipsoidal height |
| Liu et al               | 2021 | ATL03   |                                          |                           | TMD tidal model        | -                       |
| Ma et al.               | 2020 | ATL03   | Parrish + sloping sea surface correction | Adaptive DBSCAN           | OTPS2                  | -                       |
|                         |      |         |                                          |                           |                        | -                       |
|                         |      |         |                                          |                           |                        | -                       |


## Motivation


### Impact of the nearshore data
One of the most important aspects of a 1D wave model is the nearshore bathymetry, since the exact shape and depth of the profile has a profound impact on the wave transformation. The current state of 1D modeling of mangrove ecosystems either relies on in-situ survey data, or on a assumed profile shape. Currently, there exists a world-wide bathymetric dataset (GEBCO), but the resolution of 1km, and the rounding of depths to the nearest meter make this data insufficient for accurate modeling of the nearshore zone. 

### Limitations of conventional nearshore survey
The nearshore zone is a very difficult environment to perform bathymetric surveying. [@Parrish2019]. Exisiting methods of bathymetric survey, like a multi-beam echo sounder (MBES) are typically attached to ships which cannot navigate in water shallower than 4-5m, and are limited by operational restrictions when working in shallow water, like the precense of navigational hazards or sensitive ecosytems. Airborne LiDAR surveying can be used for a high resolution model of the bathymetry. However, these surveys are extremely expensive to perform and require extensive post-processing effort to create a usable surface model.

### Knowledge gaps

- How does canopy height and other physical characteristics of the mangrove forest affect the coastal protection offered by mangroves
- How can nearshore bathymetry be assesed at a global scale in data poor regions?

### Research Question

- How can spaceborne LiDAR data be used to improve existing nearshore bathymetry and canopy height data along mangrove-lined coasts?

To answer this question, the following subquestions will be pursued:

- How can ICESat-2 transects with reliable data be identified algorithmically? 
- I
- How can LiDAR returns reflecting the seafloor be separated from background noise? 
- How can gaps be filled in areas with missing lidar photons?
- Once signal photons have been identified, how can the seafloor elevation data be extracted? 
- Can information about the mangrove canopy height be extracted from the LiDAR data?

## Approach

To extract the nearshore bathymetry 
- Find areas for global analysis:
  - select from VO hotspots where mangrove area >10% and population >20
  - dissolve polygons to merge any touching polygons
  - buffer features if needed?
  - resulting features are the study areas

- Downloading and processing data:
  - Get GEBCO and icesat for each study area 
  - extract ICESAT ground tracks lines
  - throw out any lines that don't intersect the OSM Coastline
  - determine which transect direction is offshore (based on deepest GEBCO depth?)
  - Go from offshore side to the OSM coastline intersection and resample the GEBCO depth to desired horizontal resolution
  - calculate along-track distance in meters by reprojecting to local UTM, starting from offshore side of transect 
  
- Classify lidar photon returns for each quality transect
    - Interpolate GEBCO data along the transect (contour raster, build 30m TIN off the contours?)
    - Extract bathymetry using correction algorithm 
    - Extract canopy height from canopy height data
- assess seafloor bathymetry
  - Bayesian updating of interpolated GEBCO data
### Diagram

<!-- ![image](../figures/approach.png){width="\\textwidth"} -->

## Planning

The planned schedule is shown in the image below. 

<!-- ![Schedule](../figures/thesis-schedule.png) -->
