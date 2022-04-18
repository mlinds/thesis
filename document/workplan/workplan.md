# Work Plan

## Introduction

### Mangroves as coastal protection
Sea level rise poses a threat to all coastal communities, including many of the world's largest population centers. The risk is even more existential for low-lying tropical commmunities, who have done little to contribute to the current climate crisis, but are disproportionatelly affected by the sea level rise. Low-lying nations often do not have any available high ground to move cities to, and sometimes don't have access to the resources to fully mitigate these risks through hard infrastrcture. For these reasons, mangroves forests are an important resource for these communities, providing coastal protection that can adapt to sea level rise by trapping sediment and expanding outward if conditions permit.

Current study of the effects of mangroves on wave attenuation are limited by the difficulty of gather data about these ecosystems.  Shallow water bathymetry and mangrove height are difficult to survey manually. Mangrove forests are extremely dense and field work is difficuly. Therefore, finding an automated way of extracting this anywhere in the world from and publicly available data is a massive improvement when modeling sites that don't have existing survey data.

### ICESat-2
The ICESat-2 mission is inteded to gather high resolution topograhic data on a global scale. The satellite carries the Advanced Topographic Laser Altimeter System (ATLAS). ATLAS is a highly sensitive photon-counting, green-light LiDAR. The satellite instrument points at reference ground tracks along the earth's surface with a repeat time of 91 days. Along the refence track, there are 3 beams, one pointing directly at the reference track, and two that are offset by approximately 3km on either side. 

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


## Motivation

### Impact of the nearshore data
One of the most important aspects of a 1D wave model is the nearshore bathymetry, since the exact shape and depth of the profile has a profound impact on the wave transformation. The current state of 1D modeling of mangrove ecosystems either relies on in-situ survey data, or on a assumed profile shape. Currently, there exists a world-wide bathymetric dataset (GEBCO), but the resolution of 1km, and the rounding of depths to the nearest meter make this data insufficient for accurate modeling of the nearshore zone. 

### Limitations of conventional nearshore survey
The nearshore zone is a very difficult environment to perform bathymetric surveying. [@parrishValidationICESat2ATLAS2019]. Exisiting methods of bathymetric survey, like a multi-beam echo sounder (MBES) are typically attached to ships which cannot navigate in water shallower than 4-5m, and are limited by operational restrictions when working in shallow water, like the precense of navigational hazards or sensitive ecosytems. Airborne LiDAR surveying can be used for a high resolution model of the bathymetry. However, these surveys are extremely expensive to perform and require extensive post-processing effort to create a usable surface model.

### Knowledge gaps

- How does canopy height and other physical characteristics of the mangrove forest affect the coastal protection offered by mangroves
- How can nearshore bathymetry be assesed at a global scale in data poor regions?

### Research Question

- How can spaceborne LiDAR data be used to improve existing nearshore bathymetry and canopy height data along mangrove-lined coasts?

To answer this question, the following subquestions will be pursued:

- How can ICESat-2 transects with reliable data be identified algorithmically? 
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
