# Work Plan

## Introduction

### Motivation

### Knowledge gaps

- How does canopy height and other physical characteristics of the mangrove forest affect the coastal protection offered by mangroves
- How can nearshore bathymetry be assesed at a global scale in data poor regions?

### Research Questions

-   In which areas of the world will investment in mangrove restoration
    provide the most benefits in terms of flood risk reduction?

To answer this question, the following subquestions will be pursued:

- how can parameters for the classification be set dynamically

-   How can global-scale data be used to improve the accuracy of
    modeling of flood risk reduction due to mangrove ecosystems?

-   Based on this modeling method, where will restoration provide the
    largest reduction in flood risk?

-   Which of these hotspots will provide the largest societal return on
    investment in restoration of mangrove ecosystems?

### Approach

New idea: SWAN transect for every single icesat-2 path that intersects a mangrove forest

How to find intersecting icesat2 paths?

- Simplify mangrove shapefile geometry
    - Dissolve on the mangrove forest shapefile
    - Explode these features and drop those below a certain area

- Get lidar data in those areas:
    - Plug that shapefile into nasa earth downloader 
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


[]{#fig:approach label="fig:approach"}
![image](figures/BN_approach.png){width="\\textwidth"}

## Planning

![\<caption\>](figures/thesis-schedule.png){#<label>}
