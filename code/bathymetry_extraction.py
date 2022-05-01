# %%
# for testing I want to be able to reload my module when i change it
from importlib import reload

from bokeh.io import output_notebook
from bokeh.palettes import Spectral5
from bokeh.plotting import figure, show
from bokeh.transform import factor_cmap

import atl03_utils

atl03_utils = reload(atl03_utils)
# tells bokeh to print to notebook
output_notebook()


# %% [markdown]
#  # Bathymetry from IceSAT-2 ATLAS Photons
#
#  ## Test subset
#  ATL03 data was for an area of the Florida Keys. This locations were chosen
#   because of the availability of high-quality in-situ topobathymetric lidar
#  data which has been collected and processed by the USGS, FEMA, and the US Army Corps of Engineers.
#
#  ## Data Downloading
#
#  ### Temporal Subsetting
#  No tempral subsetting was applied.
#  ### Variable subsetting
#  The full data granules contain a lot of data which will not be relevant for extracting the bathymetry. Therefore, only a
#  # subset that are valuable to us are requested from the NASA DAAC API. This subset is defined in [this python file](./variablelist.py).
#  When the variable list is imported it dynamically creates a list of the variables needed for each beam.

# %% [markdown]
#  ## Photon Data Processing
#
#  ### Getting the geography of tracks
#  To find the path of each satellite pass, all the HDF files that are present are read, the track is calculated by inspecting the
#  individual photon returns for the maximum and minimum, and the the results are saved into a GeoDataFrame (and exported to a file)

# %%
# make a dataframe including all granule files in the data download folder
# alltracks = atl03_utils.make_gdf_from_ncdf_files("../data/test_sites/PR/ATL03/*.nc")

# alltracks.reset_index().sort_values("Percentage High confidence Ocean Returns",ascending=False)
# alltracks.to_file('../data/derived/PR_atl_tracks.gpkg')


# %% [markdown]
#  ## Vertical elevation adjustment
#
#  The Z value stored in the ATL03 data is referenced to the height relative to the WGS84 ellipsoid. Included with the ATL03 photon
#   data is a correction factor (variable `geoid`) to convert the ellipsoidal height to height on the tide-free geoid.
#  A factor (variable `geoid_free2mean`) is also included which can be added to convert the tide-free elevation to
#   elevation in the mean-tide system. Finally, to calculate the actual water surface elevation relativive to MSL,
#  the ocean tide, relative to MSL, is provided. (stored in variable `tide_ocean`). It is a rough estimate based on
#  the GOT 4.8 model, which isn't well suited to nearshore areas (@ATL03 ATBD). Therefore, further investigation
#  is required to find the best tidal model to get the actual depth along the transect.

# %% [markdown]
#  ### Track selection
#
#  *Good tracks found in PR*:
#  - ../data/test_sites/PR/ATL03/processed_ATL03_20181028071900_04530107_005_01.nc
#  - ../data/test_sites/PR/ATL03/processed_ATL03_20190127025857_04530207_005_01.nc
#  - ../data/test_sites/PR/ATL03/processed_ATL03_20190727181817_04530407_005_01.nc (good if noise points are thrown out)
#  - ../data/test_sites/PR/ATL03/processed_ATL03_20200721130011_04000801_005_01.nc (shallow but looks nice)

# %%
# gdf = atl03_utils.make_gdf_from_ncdf_files('../data/test_sites/OutputsIndonesia_testsite_1/*.nc')

# %%
atl03_testfile = "../data/test_sites/OutputsIndonesia_testsite_1/processed_ATL03_20190416114500_02780308_005_01.nc"
print(atl03_testfile)
beamlist = atl03_utils.get_beams(atl03_testfile)
print(f"beams available {beamlist}")


# %%
beam = "gt1l"
print(beam)

beamdata = atl03_utils.load_beam_array_ncds(atl03_testfile, beam)

print(f"length of the dataset is {beamdata.shape[0]} points")
metadata_dict = beamdata.dtype.metadata

point_dataframe = atl03_utils.add_track_dist_meters(beamdata)

# %% [markdown]
#  ## Photon return filtering
#  Filter any points over 5m above the geoid.

# %%
point_dataframe = point_dataframe.bathy.filter_high_returns()


# %% [markdown]
#  Filter out any points that are classified as a potential TEP.
#  We also filter out any points that are greater than 35m below the sea surface. The extreme upper limit of SDB via icesat is 40m (find citation)

# %%
point_dataframe = point_dataframe.bathy.filter_TEP()


# %% [markdown]
# ## Tide Correction
# from ATL03 ATBD:
#
#  > Users should be aware that the GOT4.8 tide model used here provides values at 0.5 degree
#  resolution, so near coastlines and embayments, values should be treated with caution. See the
#  ICESat-2 Data Comparison User Guide for more detail.
#
# For now, the tide correction provided along with the photon data is used until better data is available. The tide correction from the segment level is applied to the point dataframe during loading.
#
# ## Finding the sea surface level
#
# To estimate the sea surface level, points that have assigned a high confidence of being an ocean point (according to NASA's designations) are selected, and a moving median of 31 neigboring points is taken. This median of the Z values of the high confidence points is then interpolated to all photons, interpreted linearly along the transect line. These vaulues are added to back to the table. Now every photon return below +5m geoid elevation has a sea level value. To distinguish subsurface points, we also calculate a rolling standard deviation of the same window.
#

# %%
point_dataframe = point_dataframe.bathy.add_sea_level()

# %%
point_dataframe = point_dataframe.bathy.filter_low_points()

# %% [markdown]
# Now that the sea level has been interpolated based on the median elevation of high-confidence ocean returns, we can find probable subsurface returns by removing any points within 3 standard deviations of the interpolated sea surface height.

# %%
point_dataframe = point_dataframe.bathy.remove_surface_points(min_remove=0.5)

# %%[markdown]
# ## removing deepwater points
#  to remove points that we know are too deep, the GEBCO values for each point are added. Any points with a GEBCO depth of greater than 40 are removed

point_dataframe = atl03_utils.add_dem_data(
    point_dataframe,
    [
        "../data/test_sites/florida_keys/in-situ-DEM/2019_irma.vrt",
        "../data/test_sites/florida_keys/in-situ-DEM/fema_2017.tif",
        "../data/test_sites/florida_keys/GEBCO/gebco.tif",
        "../data/CMS_Global_Map_Mangrove_Canopy_1665/data/hmax95/height_vrt.vrt",
    ],
)

# point_dataframe = point_dataframe[point_dataframe["gebco.tif"] > -40]
# %%
# %% [markdown]
#  The photons remaining after these filters are plotted below:
#

# %%
TOOLS = "hover,crosshair,pan,wheel_zoom,zoom_in,zoom_out,box_zoom,undo,redo,reset,tap,save,box_select,poly_select,lasso_select,"
point_dataframe["oc_sig_conf"] = point_dataframe.oc_sig_conf.astype("str")
p = figure(
    tools=TOOLS,
    sizing_mode="scale_width",
    height=200,
    title="All Photon Returns",
)
signal_conf_cmap = factor_cmap(
    "oc_sig_conf",
    palette=Spectral5,
    factors=sorted(point_dataframe.oc_sig_conf.unique().astype("str")),
)
p.scatter(
    source=point_dataframe,
    x="dist_or",
    y="Z",
    color=signal_conf_cmap,
    legend_field="oc_sig_conf",
)
p.line(
    source=point_dataframe,
    x="dist_or",
    y="sea_level_interp",
    legend_label="calculated sea surface",
)
show(p)
point_dataframe["oc_sig_conf"] = point_dataframe.oc_sig_conf.astype("int")


# %% [markdown]
#  ## Clustering Signal/Noise with DBSCAN
#
#  Based largely on Ma et al.
#
#  Now that we have the raw photons, we need to determine which show the sea surface, which are the seabed, and which are noise.
#
#  DBSCAN is a clustering algotithm based on local density of points. Its two inputs main inputs are the distance between neightbors $R_a$, and the minimum cluster size $MinPts$. Any two points that are within a distance of $R_a$ are considered neighbors. If more than $MinPts$ neighboring points are in an area, they are counted as a single cluster.
#
#  ### Minimum Points
#  paramters can be set adaptively, from Ma et al:
#
#  > In this study, we modify the calculation process of MinPts to apply to the ICESat-2 datasets. First, the ATL03 raw data photons were used (including all photons with confidence from 0 to 4). In each ICESat-2 route that flew over the study area, every continuous 10,000 raw photons in the along-track direction were calculated together.
#
#  For this application, the minimum number of points was calculated using the method outlined in the paper above.
#
#  SN1 is calculated by:
#
#  $$SN_1 = \frac{\pi R_{\alpha}^2N_1}{hl}$$
#
#  - N1 is the number of signal and noise photons
#  - H is the vertical range
#  - l is along-track range
#
#  $$SN_2 = \frac{\pi R_{\alpha}^2N_2}{h_2 l}$$
#
#  - $N_2$ is the number of photons in the lower 5m
#  - $h_2$ is the height of the 5m lowest layer = 5
#
#  $$MinPts = \frac{2SN_1 - SN_2}{\ln{2SN_1 / SN_2}}$$
#
#  ### Search distance
#  Ma et al. use a $R_a$ is 1.5m in daytime and 2.5m at night. However, it was found that using this search radius selected too many points that appear to be noise, and ignored signal points. To prioritize neighboring points, the Mahalanobis distance is used.
#
#  ### Processing in chunks
#  Based on the methodology of Ma et al, the points are split into groups of approximately 10,000 points, in the along-track direction. The DBSCAN algorithm with the MinPts and Ra values calculated above is run. All points that are within a cluster are counted as signal, while all unclassifified points are assumed to be noise. It was also tried to split the dataset by distance, in chunks of 500m, to see what effect this would have.
#
#  The beam and file to apply the algorithm to can be selcted below:

# %% [markdown]
#  ### Setting DBSCAN parameters


# %%

point_dataframe = atl03_utils.cluster_signal_dbscan(point_dataframe)


# %%

signal_pts = point_dataframe[point_dataframe.SN == "signal"]
noise_pts = point_dataframe[point_dataframe.SN == "noise"]

p2 = figure(
    tools=TOOLS,
    title="Signal Vs Noise identified with DBSCAN",
    sizing_mode="scale_width",
    height=200,
)
p2.scatter("dist_or", "Z_g", source=noise_pts, color="red")
p2.scatter("dist_or", "Z_g", source=signal_pts, fill_color="blue")

show(p2)


# %% [markdown]
#  ## Comparison with in-situ Topobathy
#
#  We can extract the raster values from the USGS topobathymetry data for each photon that was classified as signal
#
#  First we define some functions for reading a raster value for each Lidar return photon

# %%
DEM_comp_plot = figure(
    tools=TOOLS,
    sizing_mode="scale_width",
    height=200,
    title="USGS Topobathy Vs. ICESAT-2 photon returns",
)
DEM_comp_plot.scatter(
    source=signal_pts,
    x="dist_or",
    y="Z_g",
    color="green",
    legend_label="Detected Signal Photon Returns",
)

DEM_comp_plot.xaxis.axis_label = "Along Track Distance [m]"
DEM_comp_plot.yaxis.axis_label = "Height relative to MSL [m]"
show(DEM_comp_plot)


# %% [markdown]
#  ## Refraction correction
#
#  The depth of each point can be corrected with the simple formula based on Snel's law:
#  $R_c  = \frac{n_1}{n_2} R_p \approx 0.75 R_p$
#
#  To get the depth at each point, the following formula is used:
#  $\text{Dep} = \text{Local sea Level} - \text{Seafloor Level}$
# %%
signal_pts = atl03_utils.add_raw_seafloor(signal_pts)


# %%
results_plot = figure(
    tools=TOOLS,
    sizing_mode="scale_width",
    height=200,
    title="Refraction Corrected Results",
)
results_plot.line(
    source=signal_pts,
    x="dist_or",
    y="sf_refr",
    color="blue",
    legend_label="Refraction corrected seafloor",
)
results_plot.line(
    source=point_dataframe,
    x="dist_or",
    y="height_vrt.vrt",
    color="orange",
    legend_label="Mangrove Height above ground",
)

results_plot.line(
    source=point_dataframe,
    x="dist_or",
    y="2019_irma.vrt",
    color="red",
    legend_label="FEMA 2019",
)

results_plot.line(
    source=point_dataframe,
    x="dist_or",
    y="gebco.tif",
    color="black",
    legend_label="GEBCO",
)

results_plot.xaxis.axis_label = "Along Track Distance [m]"
results_plot.yaxis.axis_label = "Height relative to MSL [m]"
show(results_plot)


# %%
p = figure(title="Comparison calculated vs 'Sea-truth' data")
p.scatter(source=signal_pts, x="in_situ_height", y="sf_refr")
# p.line(x=)
show(p)
# export_png(obj=p,filename="../document/figures/bathy_extraction/comparison.png")

# %% [markdown]
#  ## Issues to consider
#
#  - Not all tracks are equally good - some are really noisy, some are really clean. How do we programmatically select which tracks are higher quality. Is there a metric in the metadata that might predict cleaner bathymetric results?
#      - make sure to download the variable signal_conf_ph in the heights group, and entire quality group for each photon
#  - How to dynamically scale the search radius? Do we keep the 10k points and change the search radius based on the horizontal length of that chunk of 10k pts?
#  - how to deal with non-shore-normal tracks? coasts running north-south have basically no tracts in the cross shore direction.
#  - right now the results are referenced to ellipsoidal heights, to get them to MSL I need to get a
#  - how to 'start' and 'stop' the profile?
#
#  - throw out suspected bad data
#
#
#  ## api info to download
#  - wave height
#  - water level
#  (from copernicus)
#
#
#  ## Surface/subsurface split
#
#  from ATL12 ATBD section 4.2.1.2:
#
#  > As of 11/5/2019 for Release 4, we modified the surface finding procedure as  described in section 5.3.2. Instead of basing surface finding on the distribution of photon heights, it is now based on the distribution of the photon height anomalies relative to a moving 11-point bin average of high-confidence photon heights. This excludes subsurface returns under the crests of surface waves that otherwise fall inside the histogram of true surface heights. This further reduces any error due to subsurface returns, obviating the immediate need for a subsurface return correction.
#
#  ### Separating sea surface from seafloor
#
#  How to separate surface photons vs seafloor photons?
#
#  > For sea-ice and forest areas, many algorithms have been developed to detect specific signal photons from raw data photons (Kwok et al., 2016; Nie et al., 2018; Popescu et al., 2018; Neuenschwander and Pitts, 2019). In our previous studies, a method was proposed to detect the ground and seafloor photons, and a joint north sea wave project (JONSWAP) wave algorithm was developed to extract the signal photons on the water surface (Ma et al., 2019; Ma et al., 2018).
#
#  > The signal photons on sea surface and seafloor were detected using the above-mentioned method in last section. To obtain the precise water depth along ICESat-2's flight routes, the sea surface photons should be firstly discriminated against the seafloor photons. The local mean sea level Lm and the root mean square (RMS) wave height were calculated by the mean and standard deviation from the detected photons on the sea surface. All photons with the elevations lower than the local mean sea level minus 3-time RMS wave height were identified as seafloor photons.
#
#  Could run DBSCAN again with different parameters to classifiy seafloor vs sea surface

# %%
