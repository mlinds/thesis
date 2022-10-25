# %
import cmocean
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
from atl_module.ATL03_preprocessing.atl03_netcdf_loading import load_beam_array_ncds
from atl_module.bathymetry_extraction import icesat_bathymetry
from atl_module.bathymetry_extraction import point_dataframe_filters as dfilt
from atl_module.bathymetry_extraction.refraction_correction import correct_refr
from atl_module.utility_functions import geospatial_functions
from atl_module.utility_functions.plotting import set_size
from matplotlib.patches import ConnectionPatch, Rectangle
from mpl_toolkits.mplot3d import art3d
from rasterio.plot import show as rastershow
from scipy.stats import gaussian_kde

# %% [markdown]
# # Plots of Filtering Process

# %%
# site = "florida_keys"
# with rasterio.open(f"../data/test_sites/{site}/in-situ-DEM/truth.vrt") as femaras:
#     fig, ax = plt.subplots(figsize=(20, 17))
#     ax.set_xlabel(f"Degrees longitude in {femaras.crs}")
#     ax.set_ylabel(f"Degrees latitude in {femaras.crs}")
#     ax.set_title("FEMA 2019 post-Irma topobathymetric Lidar data")
#     # cx.add_basemap(ax,source=cx.providers.OpenTopoMap,crs=femaras.crs)
#     image_hidden = ax.imshow(
#         femaras.read(1, masked=True),
#         cmap="inferno",
#     )
#     rastershow(femaras, cmap="inferno", ax=ax)

#     fig.colorbar(image_hidden, ax=ax)
# # %%
# fig.savefig(
#     f"../document/figures/{site}_ras.pdf",
#     dpi=500,
#     facecolor="white",
#     bbox_inches="tight",
# )
# %%
beamdata = icesat_bathymetry.load_beam_array_ncds(
    "../data/test_sites/florida_keys/ATL03/processed_ATL03_20201202073402_10560901_005_01.nc",
    "gt3l",
)
beamdata = geospatial_functions.add_track_dist_meters(beamdata)


def get_photon_plot_axis():
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.set_xlabel("Distance along transect [m]")
    ax.set_ylabel("Geoidal elevation [m]")
    return fig, ax


fig, ax = get_photon_plot_axis()

ax.scatter(
    beamdata.dist_or,
    beamdata.Z_geoid,
    s=1,
    label="All Photons from beam",
    alpha=0.2,
    rasterized=True,
)
ax.set_title("Photon Filtering results")
ax.legend()
fig.savefig(
    "../document/figures/unfiltered_transect.pdf",
    facecolor="white",
    bbox_inches="tight",
)
beamdata = icesat_bathymetry._filter_points(
    beamdata,
    low_limit_gebco=-40,
    high_limit_gebco=1,
    rolling_window=200,
    max_sea_surf_elev=1,
    filter_below_z=-40,
    filter_below_depth=-40,
    n=2.5,
    max_geoid_high_z=5,
)
ax.scatter(
    beamdata.dist_or,
    beamdata.Z_geoid,
    c="red",
    s=1,
    label="Geolocated photons after filtering",
    alpha=0.2,
    rasterized=True,
)
ax.legend()
fig.savefig(
    "../document/figures/filtered_vs_unfiltered.pdf",
    facecolor="white",
    bbox_inches="tight",
)
fig, ax = get_photon_plot_axis()
ax.set_title("Photons after filtering")
ax.scatter(beamdata.dist_or, beamdata.Z_geoid, c="red", s=1, label="Photons")
fig.savefig(
    "../document/figures/photons_after_filtering.pdf",
    facecolor="white",
    bbox_inches="tight",
)


# %% [markdown]
# # Plot of Refraction error magnitude

# %%
depth = np.linspace(-1, -40, 500)
error = np.linspace(0, 5, 1000)
Xcorr, Ycorr, Zcorr = correct_refr(
    depth=depth, pointing_vector_az=0.75 * np.pi, pointing_vector_elev=0.5 * np.pi
)

fig, ax = plt.subplots(figsize=(10, 5))

ax.plot(Zcorr, depth)
# ax.plot(Xcorr,depth)
# ax.plot(Ycorr,depth)

# %%


atl03_testfile = (
    "../data/test_sites/florida_keys/ATL03/processed_ATL03_20201202073402_10560901_005_01.nc"
)
beam = "gt3l"
# IF YOU CHANGE TRANSECTS/BEAMS REMEMBER TO CHANGE THE KDE50 VALUE ON THE PLOT AS WELL
# going to put it here for conveneince
kde50val = 0.18

beamdata = icesat_bathymetry.load_beam_array_ncds(atl03_testfile, beam)

raw_data = icesat_bathymetry.add_along_track_dist(beamdata)
point_dataframe = icesat_bathymetry._filter_points(
    raw_data,
    low_limit_gebco=-40,
    high_limit_gebco=2,
    rolling_window=100,
    max_sea_surf_elev=1,
    filter_below_z=-40,
    filter_below_depth=-40,
    n=2,
    max_geoid_high_z=5,
)

# get a 1km
point_dataframe = point_dataframe.query("dist_or > 2000 and dist_or < 6000")


# %% [markdown]
# # Using a rolling kde
#

# %% [markdown]
# ## notes
# - if the KDE magnitude is a good predictor of of signal strength, we would expect it to increase as depth decreases
# - could select KDE threshold based on mean and standard deviation, and this could be defined in terms of 'confidence that this elevation is signal', but to better justify that it should be established which distributions can be assumed for the rolling KDE and why
#

# %%

# %%
# TODO switch to distance based windowing function
def getkde(start, window):
    dataset = point_dataframe.Z_geoid[start : start + window]
    dataset = dataset.dropna()
    kde = gaussian_kde(dataset)
    xvals = np.linspace(0, -40, 1000)
    y_density = kde.evaluate(xvals)
    return xvals, y_density


# %%
# create a 3d figure showing how the rolling window kde function works to find the max density

# setup a figure to put the plots on
fig = plt.figure(figsize=(10, 8))
# fig.suptitle("2D KDE windowing function")
# setup a 2 subplot first

ax2d = fig.add_subplot(2, 2, 1)

ax2d.grid()
ax2d.set_xlabel("Along-track Distance [m]")
ax2d.set_ylabel("Photon Elevation [m +msl]")

ax2dkde = fig.add_subplot(2, 2, 2)
ax2dkde.set_xlabel("Probability Density")
ax2dkde.set_ylabel("Photon Elevation [m +msl]")

subsurf_ph = ax2d.scatter(
    point_dataframe.dist_or,
    point_dataframe.Z_geoid,
    label="Subsurface Photons",
    zorder=-1,
    alpha=0.3,
    rasterized=True,
    s=4,
)


for startpt in [800, 2400]:
    # find the x lodcation of the middle of the box, by taking average of start and end x coordinate
    s = (
        point_dataframe.dist_or.iloc[startpt] + point_dataframe.dist_or.iloc[startpt + 100]
    ) / 2
    # find the y,z values of the kde graph
    kdey, kdez = getkde(startpt, 200)

    ax2dkde.plot(kdez, kdey)
    # add rectangle showing the filter area
    # get the rectangle geometry first
    window_startpt = (
        point_dataframe.dist_or.iloc[startpt],
        point_dataframe.Z_geoid.min(),
    )
    window_width = (
        point_dataframe.dist_or.iloc[startpt + 100] - point_dataframe.dist_or.iloc[startpt]
    )
    subsetdf = point_dataframe[startpt : startpt + 100]
    photons_in_window = ax2d.scatter(
        subsetdf.dist_or,
        subsetdf.Z_geoid,
        label="Photons within window",
        s=4,
        c="#FF8702",
    )

    window_height = 50
    # add the filter rectangle to the plot
    rec = Rectangle(
        window_startpt,
        window_width,
        window_height,
        zorder=3,
        # color="black",
        fill=False,
        label="Window",
    )

    rectangle = ax2d.add_patch(rec)
    # get the max Z value of the kde
    kdemax_z = kdez.max()
    # find the corresponding y value
    kdemax_y = kdey[kdez.argmax()]

    # add the seafloor location
    sf_elev = ax2d.scatter(s, kdemax_y, label="Estiated bathymetry", c="green", s=6)

    path = ConnectionPatch(
        xyA=(kdemax_z, kdemax_y),
        coordsA="data",
        axesA=ax2dkde,
        xyB=(s, kdemax_y),
        axesB=ax2d,
        coordsB="data",
    )
    fig.add_artist(path)


ax2d.set_ylim(-50, 5)
ax2dkde.set_ylim(-50, 5)
ax2dkde.axvline(0.10, label="Minimum density", color="red", linestyle="dashed")
ax2dkde.axvline(kde50val, label="Transect kde$_{50}$", color="black", linestyle="dashed")
ax2dkde.legend()

ax2d.legend(
    handles=[rectangle, photons_in_window, sf_elev, subsurf_ph],
    loc="lower center",
    ncols=2,
)
ax2d.set_title("Geolocated Photon Returns")
ax2dkde.set_title("Kernel density with horizontal windowing")
fig.show()

fig.savefig("../document/figures/2d_kde_plot.pdf", bbox_inches="tight")
fig.savefig("../document/figures/2d_kde_plot.png", bbox_inches="tight")

# %%
# create a 3d figure showing how the rolling window kde function works to find the max density

# setup a figure to put the plots on
fig = plt.figure(figsize=(24, 18), facecolor="w")
fig.suptitle("2D KDE windowing function")
# setup a 2 subplot first

# 3d plot
ax = fig.add_subplot(1, 1, 1, projection="3d")

ax.scatter(
    xs=point_dataframe.dist_or,
    ys=point_dataframe.Z_geoid,
    label="Photons in subsurface zone",
    zorder=-1,
    rasterized=True,
    s=4,
)
# lims = ax1.get_xlim()


startpt = 1000

for startpt in range(0, len(point_dataframe) - 100, 50):
    # find the x lodcation of the middle of the box, by taking average of start and end x coordinate
    s = (
        point_dataframe.dist_or.iloc[startpt] + point_dataframe.dist_or.iloc[startpt + 100]
    ) / 2
    # find the y,z values of the kde graph
    kdey, kdez = getkde(startpt, 200)

    ax2dkde.plot(kdez, kdey)
    # add rectangle showing the filter area
    # get the rectangle geometry first
    window_startpt = (point_dataframe.dist_or.iloc[startpt], -40)
    window_width = (
        point_dataframe.dist_or.iloc[startpt + 100] - point_dataframe.dist_or.iloc[startpt]
    )
    window_height = 40
    # add the filter rectangle to the plot
    rec = Rectangle(
        window_startpt,
        window_width,
        window_height,
        zorder=3,
        color="black",
        fill=False,
        label="Window",
    )

    ax.add_patch(rec)
    art3d.pathpatch_2d_to_3d(rec, z=0, zdir="z")

    #
    if max(kdez) > 0.1:
        ax.plot(
            ys=kdey,
            zs=kdez,
            xs=np.full_like(kdey, s),
            color="g",
            label="Gaussian KDE of the Z values within window",
        )
    else:
        ax.plot(
            ys=kdey,
            zs=kdez,
            xs=np.full_like(kdey, s),
            color="r",
            label="Insufficient Bathymetric signal",
        )

    # get the max Z value of the kde
    kdemax_z = kdez.max()
    # find the corresponding y value
    kdemax_y = kdey[kdez.argmax()]

    # # plot the line from the max value to the 2d graph
    # ax.plot(
    #     xs=[s, s],
    #     ys=[kdemax_y, kdemax_y],
    #     zs=[0, kdemax_z],
    #     marker="o",
    #     label="Location of maximum Kernel Density",
    #     c="r",
    # )

ax.set_zlabel("Probability density [-]")
ax.set_xlabel("Along-track distance [m]")
ax.set_ylabel("Depth +MSL [m]")
ax.set_zlim(0, 0.2)
ax.set_ylim(-50, 5)
fig.show()
fig.savefig("../document/figures/3d_kde_function.pdf")


# %% [markdown]
# # Kriging figures
# %%
pts = gpd.read_file("../data/test_sites/florida_keys/kriging_pts")
pts_all = (
    gpd.read_file("../data/test_sites/florida_keys/all_bathy_pts.gpkg")
    .eval("northing=northing_raw+northing_corr")
    .eval("easting=easting_raw+easting_corr")
)

# %%


# # %%
# with rasterio.open("../data/test_sites/florida_keys/kriging_output.tif") as krigedras:
#     elevation = krigedras.read(1)
#     uncertainty = krigedras.read(2)
#     width = elevation.shape[1]
#     height = elevation.shape[0]
#     cols, rows = np.meshgrid(np.arange(width), np.arange(height))
#     xs, ys = rasterio.transform.xy(krigedras.transform, rows, cols)
#     xvals = np.array(xs)
#     yvals = np.array(ys)

# row = 250
# oned_elev = elevation[row, :]
# oned_uncert = uncertainty[row, :]
# oned_xvals = xvals[row, :]
# oned_yvals = yvals[row, :]

# resolution = oned_xvals[1] - oned_xvals[0]

# pts_in_area = pts.loc[
#     (pts.Y > oned_yvals.min() - resolution / 2) & (pts.Y < oned_yvals.min() + resolution / 2)
# ]
# pts_all_in_area = pts_all.loc[
#     (pts_all.northing > oned_yvals.min() - resolution)
#     & (pts_all.northing < oned_yvals.min() + resolution)
# ]
# # %%
# fig, ax = plt.subplots(figsize=(20, 10))
# ax.set_title("1D section of Kriging results")

# ax.plot(oned_xvals, oned_elev, label="Interpolated Line")
# ax.fill_between(
#     oned_xvals,
#     oned_elev - np.sqrt(oned_uncert),
#     oned_elev + np.sqrt(oned_uncert),
#     color="gray",
#     alpha=0.2,
#     label="Uncertainty",
# )

# ax.scatter(
#     x=pts_in_area.X,
#     y=pts_in_area.Z,
#     color="red",
#     label="Remaining points after subsampling",
# )

# ax.legend(loc="lower left")
# fig.savefig(
#     "../document/figures/1d_kriging_section.pdf",
#     bbox_inches="tight",
#     facecolor="white",
# )

# with rasterio.open("../data/test_sites/florida_keys/bilinear.tif") as bilinear:
#     gebco_elev = bilinear.read(1, masked=True)
#     oned_gebco = gebco_elev[row, :]


# ax.plot(oned_xvals, oned_gebco)

# %%

# fig, ax = plt.subplots(figsize=(20, 10))
# ax.set_title("Combination via Kalman Filter - 1D view")

# ax.plot(oned_xvals, oned_elev, label="Kriged ICESat-2 Surface")
# ax.fill_between(
#     oned_xvals,
#     oned_elev - np.sqrt(oned_uncert),
#     oned_elev + np.sqrt(oned_uncert),
#     color="#1f77b4",
#     alpha=0.1,
#     label="Kriged ICESat-2 Uncertainty",
# )

# with rasterio.open("../data/test_sites/florida_keys/bilinear.tif") as bilinear:
#     gebco_elev = bilinear.read(1, masked=True)
#     oned_gebco = gebco_elev[row, :]


# ax.plot(oned_xvals, oned_gebco, label="GEBCO Interpolation", color="#ff7f0e")
# ax.fill_between(
#     oned_xvals,
#     oned_gebco - 0.5,
#     oned_gebco + 0.5,
#     alpha=0.1,
#     color="#ff7f0e",
#     label="GEBCO Uncertainty",
# )

# with rasterio.open("../data/test_sites/florida_keys/kalman_updated.tif") as kalman_raster:
#     kalman_elev = kalman_raster.read(1)
#     oned_kalman = kalman_elev[row, :]


# ax.plot(
#     oned_xvals,
#     oned_kalman,
#     label="Estimate with Kalman Filter",
#     linewidth=3,
#     color="#2ca02c",
# )
# ax.legend(loc="lower left")
# ax.set_ylabel("Elevation [m]")
# ax.set_xlabel("Easting [m UTM 17N]")
# fig.savefig(
#     "../document/figures/kalman_1d_section.pdf",
#     bbox_inches="tight",
#     facecolor="white",
# )

# # %%
# with rasterio.open("../data/test_sites/florida_keys/kriging_output.tif") as bilinear_raster:
#     fig, ax = plt.subplots(figsize=(20, 10))
#     ax.set_xlabel("Easting UTM 17N")
#     ax.set_ylabel("Northing UTM 17N")
#     ax.set_title("Location of 1D section")
#     # cx.add_basemap(ax, source=cx.providers.OpenTopoMap, crs=bilinear_raster.crs)
#     image_hidden = ax.imshow(
#         bilinear_raster.read(1, masked=True),
#         cmap="inferno",
#     )
#     rastershow(bilinear_raster, cmap="inferno", ax=ax)
#     ax.axhline(oned_yvals[0], linewidth=5)

#     fig.colorbar(image_hidden, ax=ax)
#     fig.savefig(
#         fname="../document/figures/horizontal_section.pdf",
#         bbox_inches="tight",
#         facecolor="white",
#     )


# %%
# example for discussion section of the effect of missclassified photons
missclass_photons_array = load_beam_array_ncds(
    "../data/unused_sites/garawlah/ATL03/processed_ATL03_20210719132927_03961202_005_01.nc",
    "gt3r",
)

missclass_df = pd.DataFrame(missclass_photons_array)

# missclass_ph_figure,missclass_ph_ax = plt.subplots(figsize=(10,5))

ax = missclass_df.astype({"oc_sig_conf": "category"}).plot.scatter(
    x="delta_time",
    y="Z_geoid",
    c="oc_sig_conf",
    cmap="Dark2",
    figsize=(20, 7.5),
    xlabel="Seconds into granule",
    ylabel="Elevation [m+Geoid]",
    ylim=(-30, 30),
)

# %%
filter_example_transect = load_beam_array_ncds(
    "../data/test_sites/florida_keys/ATL03/processed_ATL03_20210601225346_10561101_005_01.nc",
    "gt3r",
)

filtering_example_df = pd.DataFrame(filter_example_transect)

filtering_fig, filtering_ax = plt.subplots(figsize=(10, 3))

filtered_photon_df = filtering_example_df.pipe(dfilt.add_gebco)
filtering_ax.scatter(
    filtered_photon_df.X,
    filtered_photon_df.Z_geoid,
    # alpha=0.3,
    s=1,
    rasterized=True,
)
filtering_ax.plot(
    filtered_photon_df.X,
    filtered_photon_df.gebco_elev,
    c="red",
    label="GEBCO DEM height",
)
filtered_photon_df = filtered_photon_df.pipe(
    dfilt.filter_gebco, low_limit_gebco=-50, high_limit_gebco=5
)
# filtering_ax.clear()
filtering_ax.scatter(
    filtered_photon_df.X,
    filtered_photon_df.Z_geoid,
    c="green",
    label="Remaining photons",
    s=1,
    rasterized=True,
)
filtering_ax.legend()

filtering_ax.set_ylabel("Photon elevation [m +geoid]")
filtering_ax.set_xlabel("Photon Longitude WGS84")
filtering_fig.savefig(
    "../document/figures/methodology_gebco_filtering.pdf", bbox_inches="tight"
)

filtering_fig, filtering_ax = plt.subplots(figsize=(10, 3))
filtered_photon_df = filtered_photon_df.pipe(
    dfilt.add_sea_surface_level,
    rolling_window=500,
    max_sea_surf_elev=2,
)
filtering_ax.scatter(
    filtered_photon_df.X,
    filtered_photon_df.Z_geoid,
    label="Removed due to depth or absolute height",
    # alpha=0.3,
    s=2,
    rasterized=True,
)
filtering_ax.plot(
    filtered_photon_df.X,
    filtered_photon_df.sea_level_interp,
    c="red",
    label="Calculated Sea Surface",
)
filtered_photon_df = filtered_photon_df.pipe(dfilt.filter_depth, filter_below_depth=-40)
filtered_photon_df = filtered_photon_df.pipe(dfilt.filter_low_points, filter_below_z=-40)

filtering_ax.scatter(
    filtered_photon_df.X,
    filtered_photon_df.Z_geoid,
    c="green",
    label="Removed due to being at or above sea surface",
    # alpha=0.3,
    s=2,
    rasterized=True,
)
filtered_photon_df = filtered_photon_df.pipe(dfilt.remove_surface_points, n=1)
filtering_ax.scatter(
    filtered_photon_df.X,
    filtered_photon_df.Z_geoid,
    c="orange",
    # alpha=0.3,
    s=2,
    rasterized=True,
)
filtering_ax.legend()

filtering_ax.set_ylabel("Photon elevation [m +geoid]")
filtering_ax.set_xlabel("Photon Longitude WGS84")
filtering_fig.savefig(
    "../document/figures/methodology_sealvl_filtering.pdf", bbox_inches="tight"
)

# %%
filtered_photon_df = filtered_photon_df.pipe(dfilt.filter_high_returns, max_geoid_high_z=5)
filtered_photon_df = filtered_photon_df.pipe(dfilt.filter_TEP_and_nonassoc)
filtered_photon_df = filtered_photon_df.pipe(dfilt.correct_for_refraction)

filtering_fig, filtering_ax = plt.subplots(figsize=(10, 3))

filtering_ax.scatter(
    filtered_photon_df.X,
    filtered_photon_df.Z_geoid,
    label="Remaining points after filtering",
    alpha=0.3,
    s=2,
    rasterized=True,
)
filtering_ax.legend(
    loc="upper center", bbox_to_anchor=(0.5, -0.05), fancybox=True, shadow=True, ncol=3
)
filtering_ax.set_ylabel("Photon elevation [m +geoid]")
filtering_ax.set_xlabel("Photon Longitude WGS84")

filtering_fig.savefig(
    "../document/figures/methodology_reminaing_after_filtering.pdf", bbox_inches="tight"
)

# %%


filtering_fig, filtering_ax = plt.subplots(figsize=(10, 3))

filtering_ax.scatter(
    filtered_photon_df.X,
    filtered_photon_df.Z_geoid,
    label="Remaining points after filtering",
    # alpha=0.3,
    s=2,
    rasterized=True,
    c="#253a79",
)
filtering_ax.scatter(
    filtered_photon_df.X,
    filtered_photon_df.Z_refr,
    label="Refraction-corrected returns",
    # alpha=0.3,
    s=2,
    rasterized=True,
    c="#FF8702",
)
filtering_ax.legend()
filtering_ax.set_ylabel("Photon elevation [m +geoid]")
filtering_ax.set_xlabel("Photon Longitude WGS84")

filtering_fig.savefig("../document/figures/methodology_refraction.pdf", bbox_inches="tight")

# %%

# 322901,1962814 : 335797,1971523
set_size()
# %%
st_croix_tracklines = gpd.read_file("../data/test_sites/stcroix/tracklines/")
bathy_pts = gpd.read_file("../data/test_sites/stcroix/kriging_pts/")


with rasterio.open("../data/for_other_figures/stcroixvalidation.tif") as femaras:
    fig, ax = plt.subplots(figsize=set_size(1, ratio=1.9))

    ax.set_xlabel(f"Degrees longitude in {femaras.crs}")
    ax.set_ylabel(f"Degrees latitude in {femaras.crs}")
    # cx.add_basemap(ax,source=cx.providers.OpenTopoMap,crs=femaras.crs)
    bathy_data_array = femaras.read(1, masked=True).filled(np.NaN)
    # mask out values greater than 0
    bathy_data_array = np.ma.masked_greater_equal(bathy_data_array, 0).filled(np.NaN)
    image_hidden = ax.imshow(
        bathy_data_array,
        cmap=cmocean.cm.deep_r,
    )
    st_croix_tracklines.to_crs(femaras.crs).plot(ax=ax, label="ICESat-2 Track", color="red")
    bathy_pts.to_crs(femaras.crs).plot(
        ax=ax, c="black", markersize=4, zorder=2, label="Bathymetry Point from ICESat-2"
    )
    rastershow(femaras, cmap=cmocean.cm.deep_r, ax=ax, vmax=0)
    ax.legend()
    fig.colorbar(image_hidden, ax=ax, label="Validation Data [+m MSL]")

    fig.savefig("../document/figures/discussion-spatial-stcroix.pdf", bbox_inches="tight")
