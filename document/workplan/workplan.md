# Work Plan

## Introduction

### Motivation

#### Mangroves as a coastal buffer
Sea level rise poses a threat to all coastal communities, including many of the world's largest population centers. The risk is even more existential for low-lying tropical commmunities, who have done little to contribute to the current climate crisis, but are disproportionatelly affected by the sea level rise. Low-lying nations often do not have any available high ground to move cities to, and sometimes don't have access to the resources to fully mitigate these risks through hard infrastrcture. For these reasons, mangroves forests are an important resource for these communities, providing coastal protection that can adapt to sea level rise by trapping sediment and expanding outward if conditions permit.


Current study of the effects of mangroves on wave attenuation are limited by the difficulty of gather data about these ecosystems.  Shallow water bathymetry and mangrove height are extremely difficult to survey manually. Therefore, finding an automated way of extracting this data, from any site in the world, by remote sensing techniques would provide a massive improvement to wave modeling of sites that don't have existing survey data

#### Impact of the nearshore data
One of the most important aspects of a 1D wave model is the nearshore bathymetry, since the exact shape and depth of the profile has a profound impact on the wave transformation. The current state of 1D modeling of mangrove ecosystems either relies on in-situ survey data, or on a assumed profile shape. Currently, there exists a world-wide bathymetric dataset (GEBCO), but the resolution of 1km, and the rounding of depths to the nearest meter make this data insufficient for modeling of the nearshore zone. 





### Knowledge gaps

- How does canopy height and other physical characteristics of the mangrove forest affect the coastal protection offered by mangroves
- How can nearshore bathymetry be assesed at a global scale in data poor regions?

### Research Questions

-   How can mangrove canopy characteristics and nearshore bathymetry be extracted from spaceborne LiDAR data?

To answer this question, the following subquestions will be pursued:

- How can bathymetric data be isolated from data of individual photon return locations

- How to extract mangrove canopy heights from the lidar returns

-   Based on this modeling method, where will restoration provide the
    largest reduction in flood risk?

-   Which of these hotspots will provide the largest societal return on
    investment in restoration of mangrove ecosystems?

### Approach

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
    - Once all the swan models are prepared, run them in the azure cloud
    - Move modeled forest start 10m seaward/landward and see how it affects the results 

- Map results
    - Make a global map of which locations are best suited for restoration


![image](../figures/approach.png){width="\\textwidth"}

## Planning

The planned schedule is shown in the image below. 

![Schedule](../figures/thesis-schedule.png)
