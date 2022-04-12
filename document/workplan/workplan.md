# Work Plan

## Introduction


### Mangroves as a coastal buffer
Sea level rise poses a threat to all coastal communities, including many of the world's largest population centers. The risk is even more existential for low-lying tropical commmunities, who have done little to contribute to the current climate crisis, but are disproportionatelly affected by the sea level rise. Low-lying nations often do not have any available high ground to move cities to, and sometimes don't have access to the resources to fully mitigate these risks through hard infrastrcture. For these reasons, mangroves forests are an important resource for these communities, providing coastal protection that can adapt to sea level rise by trapping sediment and expanding outward if conditions permit.


Current study of the effects of mangroves on wave attenuation are limited by the difficulty of gather data about these ecosystems.  Shallow water bathymetry and mangrove height are difficult to survey manually. Mangrove forests are extremely dense and field work is difficuly. Therefore, finding an automated way of extracting this anywhere in the world from and publicly available data is a massive improvement when  modeling sites that don't have existing survey data.

### ICESat-2
The ICESat-2 mission is a satellite carrying ATLAS, a photon-counting, green-light LiDAR sensor instrument. The satellite follows ground tracks along the earth surface with a repeat time of 91 days. The instrument emits laser pulses of photons along 3 different tracks relative to the reference ground tracks. Along each track, there is one strong and one weak laser beam. Of the trillions of photons emitted, up to ~10 make it back to the sensor and are detected. (find citation)

![RBTref](../figures/ATLAS_beam_layout_from_user_guide.png)

![beams](../figures/3d_beam_view_from_atl03ATBD.png) []



### Satellite Derived bathymetry
#### Multispectral imagery
There are many techniques to approximate depth by the spectral signatures of optical satellite data. The two classical ones are the band-ratio model and the linear 

#### LiDAR bathymetry

Green light lasers can penetrate the water up to a certain depth based on the local water clarity. In very clear water depth detectetion of up to 40m has been achieved from spaceborne lasrs [@parrishValidationICESat2ATLAS2019]. The laser path has to be corrected for refraction induced by the water before the bathymetry can be reliably estimated. 


## Motivation

### Impact of the nearshore data
One of the most important aspects of a 1D wave model is the nearshore bathymetry, since the exact shape and depth of the profile has a profound impact on the wave transformation. The current state of 1D modeling of mangrove ecosystems either relies on in-situ survey data, or on a assumed profile shape. Currently, there exists a world-wide bathymetric dataset (GEBCO), but the resolution of 1km, and the rounding of depths to the nearest meter make this data insufficient for accurate modeling of the nearshore zone. 

### Issues with traditional methods
The nearshore zone is a very difficult environment to perform bathymetric surveying. [@parrishValidationICESat2ATLAS2019]. Exisiting methods of bathymetric survey, like a multi-beam echo sounder (MBES) are typically attached to ships which cannot navigate in water shallower than 4-5m, and there are many operational restrictions when working in shallow water, like the precense of navigational hazards or sensitive ecosytems. Airborne LIDAR surveying is required for a high resolution model of the bathymetry. However, these surveys are extremely expensive to perform and require extensive post-processing effort to create a usable surface model.

### Knowledge gaps

- How does canopy height and other physical characteristics of the mangrove forest affect the coastal protection offered by mangroves
- How can nearshore bathymetry be assesed at a global scale in data poor regions?

### Research Questions

-   How can mangrove canopy characteristics and nearshore bathymetry be extracted from spaceborne LiDAR data?

To answer this question, the following subquestions will be pursued:

- How can bathymetric data be isolated from data of individual photon return locations

- How to extract mangrove canopy heights from the lidar returns


## Approach

Extract detailed nearshore bathymetry along icesat2 tracks. 

How to find intersecting icesat2 paths?
- Simplify mangrove shapefile geometry
    - Dissolve on the mangrove forest shapefile
    - Explode these features and drop those below a certain area

- Get lidar data in those areas:
    - Plug that shapefile into NSIDC DAAC downloader (or loop over features)
    - Process resulting with FME or something into a workable format

- Extract data from lidar
    - Extract bathymetry using correction algorithm 
    - Extract canopy height from canopy height data

- Assess hydrodynamics
    - Use resulting bathy, surface height, and canopy height to make a 1d transect

###

![image](../figures/approach.png){width="\\textwidth"}

## Planning

The planned schedule is shown in the image below. 

![Schedule](../figures/thesis-schedule.png)
