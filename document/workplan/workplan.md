# Work Plan

## Introduction

### Mangroves as coastal protection
Sea level rise poses a threat to all coastal communities, including many of the world's largest population centers. The risk is even more existential for low-lying tropical commmunities, who have done little to contribute to the current climate crisis, but are disproportionatelly affected by the sea level rise. Low-lying nations often do not have any available high ground to move cities to, and sometimes don't have access to the resources to fully mitigate these risks through hard infrastrcture. For these reasons, mangroves forests are an important resource for these communities, providing coastal protection that can adapt to sea level rise by trapping sediment and expanding outward if conditions permit.


Current study of the effects of mangroves on wave attenuation are limited by the difficulty of gather data about these ecosystems.  Shallow water bathymetry and mangrove height are difficult to survey manually. Mangrove forests are extremely dense and field work is difficuly. Therefore, finding an automated way of extracting this anywhere in the world from and publicly available data is a massive improvement when modeling sites that don't have existing survey data.

### ICESat-2
The ICESat-2 mission is a satellite carrying ATLAS, a photon-counting, green-light LiDAR sensor instrument. The satellite instruments points at reference ground tracks along the earth's surface with a repeat time of 91 days.  The instrument emits laser pulses of photons along 3 different tracks relative to the reference ground tracks. Of the approximately $10^14$ of photons emitted per pulse, up to ~10 make it back to the sensor and are detected. [@neumannt.a.ATLASICESat2L2A2019]

![RBTref](../figures/ATLAS_beam_layout_from_user_guide.png)

![beams](../figures/3d_beam_view_from_atl03ATBD.png) []



### Satellite Derived bathymetry
#### Multispectral imagery
There are many techniques to approximate depth by the spectral signatures of optical satellite data. The two classical ones are the band-ratio model and the linear 

#### LiDAR bathymetry

Green light lasers can penetrate the water up to a certain depth based on the local water clarity. In very clear water depth detection of up to 40m has been achieved from spaceborne lasers [@parrishValidationICESat2ATLAS2019]. The laser path has to be corrected for refraction induced by the water before the bathymetry can be reliably estimated. 


## Motivation

### Impact of the nearshore data
One of the most important aspects of a 1D wave model is the nearshore bathymetry, since the exact shape and depth of the profile has a profound impact on the wave transformation. The current state of 1D modeling of mangrove ecosystems either relies on in-situ survey data, or on a assumed profile shape. Currently, there exists a world-wide bathymetric dataset (GEBCO), but the resolution of 1km, and the rounding of depths to the nearest meter make this data insufficient for accurate modeling of the nearshore zone. 

### Limitations of conventional nearshore survey
The nearshore zone is a very difficult environment to perform bathymetric surveying. [@parrishValidationICESat2ATLAS2019]. Exisiting methods of bathymetric survey, like a multi-beam echo sounder (MBES) are typically attached to ships which cannot navigate in water shallower than 4-5m, and are limited by operational restrictions when working in shallow water, like the precense of navigational hazards or sensitive ecosytems. Airborne LIDAR surveying is required for a high resolution model of the bathymetry. However, these surveys are extremely expensive to perform and require extensive post-processing effort to create a usable surface model.

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
