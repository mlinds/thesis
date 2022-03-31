# Work Plan

## Introduction

### Motivation

### Knowledge gaps

### Research Questions

-   In which areas of the world will investment in mangrove restoration
    provide the most benefits in terms of flood risk reduction?

To answer this question, the following subquestions will be pursued:

-   How can global-scale data be used to improve the accuracy of
    modeling of flood risk reduction due to mangrove ecosystems?

-   Based on this modeling method, where will restoration provide the
    largest reduction in flood risk?

-   Which of these hotspots will provide the largest societal return on
    investment in restoration of mangrove?

### Approach

new idea: swan transect for every single icesat-2 path that intersects a mangrove forest

how to find intersecting icesat2 paths?

- Simplify mangrove shapefile geometry
    - dissolve on the mangrove forest shapefile
    - explode these features and drop those below a certain area

- get lidar data in those areas:
    - plug that shapefile into nasa earth downloader 
    - process resulting with FME or something into a workable format

- extract data from lidar
    - extract bathymetry using correction algorithm 
    - extract canopy height (check against canopy height dataset)

- asses hydrodynamics
    - use resulting bathy, surface height, and canopy height to make a 1d transect
    - once all the swan models are prepared, run them in the azure cloud
    - move modeled forest start 10m seaward/landward and see how it affects the results 

- map results
    - 

[]{#fig:approach label="fig:approach"}
![image](figures/BN_approach.png){width="\\textwidth"}

## Planning

![\<caption\>](figures/thesis-schedule.png){#<label>}
