# %%
from atl_module import (
    load_netcdf,
    point_dataframe_filters,
    icesat_bathymetry,
    raster_interaction,
)
import atl_module
import pandas as pd
from bokeh.io import output_notebook
from bokeh.palettes import Spectral5
from bokeh.plotting import figure, show
from bokeh.transform import factor_cmap
import numpy as np

output_notebook()

atl03_testfile = "../data/test_sites/florida_keys/ATL03/processed_ATL03_20210601225346_10561101_005_01.nc"
beamlist = load_netcdf.get_beams(atl03_testfile)
print(atl03_testfile)

print(f"beams available {beamlist}")


# %%
beam = "gt3r"
print(beam)

beamdata = load_netcdf.load_beam_array_ncds(atl03_testfile, beam)

print(f"length of the dataset is {beamdata.shape[0]} points")
metadata_dict = beamdata.dtype.metadata
# %%

raw_data = icesat_bathymetry.add_along_track_dist(beamdata)
# .pipe(point_dataframe_filters.add_sea_surface_level)
point_dataframe = icesat_bathymetry._filter_points(raw_data)

point_dataframe = icesat_bathymetry.add_rolling_kde(point_dataframe, window=200)
point_dataframe.loc[point_dataframe.kde_val.to_numpy() < 0.0347, "z_kde"] = np.NaN
# skewness_rolling = point_dataframe.Z_g.rolling(
#     window=200, center=True, min_periods=180
# ).median()
# point_dataframe = point_dataframe.assign(sk=skewness_rolling)

# %%
try:
    point_dataframe = pd.DataFrame(point_dataframe.drop(columns="geometry"))
except KeyError:
    pass

TOOLS = "hover,crosshair,pan,wheel_zoom,zoom_in,zoom_out,box_zoom,undo,redo,reset,tap,save,box_select,poly_select,lasso_select,"
# temporarily make the ints into strings
raw_data["oc_sig_conf"] = raw_data.oc_sig_conf.astype("str")
p = figure(
    tools=TOOLS,
    sizing_mode="scale_width",
    height=200,
    title="All Photon Returns",
)
signal_conf_cmap = factor_cmap(
    "oc_sig_conf",
    palette=Spectral5,
    factors=sorted(raw_data.oc_sig_conf.unique().astype("str")),
)
p.scatter(
    source=raw_data,
    x="dist_or",
    y="Z_g",
    color=signal_conf_cmap,
    legend_field="oc_sig_conf",
)
p.line(
    source=point_dataframe,
    x="dist_or",
    y="sea_level_interp",
    legend_field="Sea Level",
)
show(p)
p = figure(
    tools=TOOLS,
    sizing_mode="scale_width",
    height=200,
    title="Filtered photon Returns",
)
p.scatter(
    source=point_dataframe,
    x="dist_or",
    y="Z_g",
    color="green",
    legend_label="points after filtering",
)

p.line(
    source=point_dataframe,
    x="dist_or",
    y="gebco_elev",
    color="red",
    legend_label="GEBCO",
)

p.line(
    source=point_dataframe,
    x="dist_or",
    y="z_kde",
    legend_label="KDE seafloor estimate",
)

# p.line(
#     source=point_dataframe,
#     x="dist_or",
#     y="sk",
#     color="black",
#     legend_label="skew",
# )
p.xaxis.axis_label = "Along Track Distance [m]"
p.yaxis.axis_label = "Height above Ellipsoid"
p.legend.location = "bottom_right"
# p.line(source=point_dataframe, x="dist_or", y="sea_level_interp",legend_label='calculated sea surface')
show(p)
# point_dataframe["oc_sig_conf"] = point_dataframe.oc_sig_conf.astype("int")

#%%
point_dataframe = point_dataframe.assign(
    z_kde_mean=point_dataframe.z_kde.rolling(window=200, center=True).mean()
)
#%%

# %% [markdown]
#  ## Comparison with in-situ Topobathy
#
#  We can extract the raster values from the USGS topobathymetry data for each photon that was classified as signal
#
#  First we define some functions for reading a raster value for each Lidar return photon

# %%
# For cleaning the raster results

dem_2019 = raster_interaction.query_raster(
    point_dataframe,
    "../data/test_sites/florida_keys/in-situ-DEM/2019_irma.vrt",
)
dem_2017 = raster_interaction.query_raster(
    point_dataframe,
    "../data/test_sites/florida_keys/in-situ-DEM/fema_2017.tif",
)

point_dataframe = point_dataframe.assign(
    fema2019_elev=dem_2019,
    # canopy_h=mangrove_heightlist,
    fema2017_elev=dem_2017,
)


# %%
DEM_comp_plot = figure(
    tools=TOOLS,
    sizing_mode="scale_width",
    height=200,
    title="USGS Topobathy Vs. ICESAT-2 photon returns",
)

DEM_comp_plot.line(
    source=point_dataframe,
    x="dist_or",
    y="fema2019_elev",
    color="red",
    legend_label="FEMA 2019 Lidar",
)

DEM_comp_plot.line(
    source=point_dataframe,
    x="dist_or",
    y="fema2017_elev",
    color="blue",
    legend_label="FEMA 2017 Lidar",
)
# DEM_comp_plot.line(
#     source=point_dataframe,
#     x="dist_or",
#     y="gebco_elev",
#     color="green",
#     legend_label="gebco",
# )

DEM_comp_plot.line(
    source=point_dataframe,
    x="dist_or",
    y="z_kde_mean",
    color="black",
    legend_label="Fitted Seafloor",
)
# DEM_comp_plot.line(
#     source=point_dataframe.eval('kde_val = kde_val*10'),
#     x="dist_or",
#     y="kde_val",
#     legend_label="actual kde",
# )
DEM_comp_plot.legend.location = "bottom_right"
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
results_plot = figure(
    tools=TOOLS,
    sizing_mode="scale_width",
    height=200,
    title="Refraction Corrected Results",
)

results_plot.line(
    source=point_dataframe,
    x="dist_or",
    y="gebco_elev",
    color="red",
    legend_label="USGS high res topobathymetric data",
)
results_plot.line(
    source=point_dataframe,
    x="dist_or",
    y="z_kde",
    color="blue",
    legend_label="Refraction corrected seafloor",
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

# %%


# %%

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
