# %%
import geopandas as gpd
import matplotlib.pyplot as plt

# from pyrsistent import l
import numpy as np
import rasterio
from matplotlib.patches import ConnectionPatch, Rectangle
from mpl_toolkits.mplot3d import art3d
from scipy.stats import gaussian_kde

from atl_module import icesat_bathymetry
from atl_module.refraction_correction import correct_refr

import contextily as cx
import rasterio
from rasterio.plot import show as rastershow
plt.rcParams["font.family"] = "Sans Serif"
# %% [markdown]
# # Plots of Filtering Process

# %%
beamdata = icesat_bathymetry.load_beam_array_ncds(
    "../data/test_sites/florida_keys/ATL03/processed_ATL03_20201202073402_10560901_005_01.nc",
    "gt3l",
)
beamdata = icesat_bathymetry.add_along_track_dist(beamdata)


def get_photon_plot_axis():
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.set_xlabel("Distance along transect [m]")
    ax.set_ylabel("Geoidal elevation [m]")
    return fig, ax


fig, ax = get_photon_plot_axis()

ax.scatter(beamdata.dist_or, beamdata.Z, s=1, label="All Photons from beam", alpha=0.2)
ax.set_title("Photon Filtering results")
ax.legend()
fig.savefig(
    "../document/figures/unfiltered_transect.jpg",
    facecolor="white",
    bbox_inches="tight",
)
beamdata = icesat_bathymetry._filter_points(beamdata)
ax.scatter(
    beamdata.dist_or,
    beamdata.Z,
    c="red",
    s=1,
    label="Geolocated photons after filtering",
    alpha=0.2,
)
ax.legend()
fig.savefig(
    "../document/figures/filtered_vs_unfiltered.jpg",
    facecolor="white",
    bbox_inches="tight",
)
fig, ax = get_photon_plot_axis()
ax.set_title("Photons after filtering")
ax.scatter(beamdata.dist_or, beamdata.Z, c="red", s=1, label="Photons")
fig.savefig(
    "../document/figures/photons_after_filtering.jpg",
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

fig, ax = plt.subplots()

ax.plot(Zcorr, depth)
# ax.plot(Xcorr,depth)
# ax.plot(Ycorr,depth)

# %%
atl03_testfile = "../data/test_sites/florida_keys/ATL03/processed_ATL03_20201202073402_10560901_005_01.nc"
beam = "gt3l"

beamdata = icesat_bathymetry.load_beam_array_ncds(atl03_testfile, beam)

raw_data = icesat_bathymetry.add_along_track_dist(beamdata)
# .pipe(point_dataframe_filters.add_sea_surface_level)
point_dataframe = icesat_bathymetry._filter_points(raw_data)

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
def getkde(start, window):
    dataset = point_dataframe.Z_g[start : start + window]
    dataset = dataset.dropna()
    kde = gaussian_kde(dataset)
    xvals = np.linspace(0, -40, 1000)
    y_density = kde.evaluate(xvals)
    return xvals, y_density


# %%
# create a 3d figure showing how the rolling window kde function works to find the max density

# setup a figure to put the plots on
fig = plt.figure(figsize=(20, 16))
# fig.suptitle("2D KDE windowing function")
# setup a 2 subplot first

ax2d = fig.add_subplot(2, 2, 1)

ax2d.grid()
ax2d.set_xlabel("Along-track Distance [m]")
ax2d.set_ylabel("Photon Elevation [m +msl]")

ax2dkde = fig.add_subplot(2, 2, 2)
ax2dkde.set_xlabel("Probability Density")
ax2dkde.set_ylabel("Photon Elevation [m +msl]")

ax2d.scatter(
    point_dataframe.dist_or,
    point_dataframe.Z_g,
    label="Neighboring Photons",
    zorder=-1,
    alpha=0.3,
)


for startpt in [1200]:
    # find the x lodcation of the middle of the box, by taking average of start and end x coordinate
    s = (
        point_dataframe.dist_or.iloc[startpt]
        + point_dataframe.dist_or.iloc[startpt + 100]
    ) / 2
    # find the y,z values of the kde graph
    kdey, kdez = getkde(startpt, 200)

    ax2dkde.plot(kdez, kdey)
    # add rectangle showing the filter area
    # get the rectangle geometry first
    window_startpt = (point_dataframe.dist_or.iloc[startpt], point_dataframe.Z_g.min())
    window_width = (
        point_dataframe.dist_or.iloc[startpt + 100]
        - point_dataframe.dist_or.iloc[startpt]
    )
    subsetdf = point_dataframe[startpt : startpt + 100]
    photons_in_window = ax2d.scatter(
        subsetdf.dist_or,
        subsetdf.Z_g,
        label="Photons within window",
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
    sf_elev = ax2d.scatter(
        s, kdemax_y, label="Calculated Seafloor elev in middle of window"
    )

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

ax2d.legend(handles=[rectangle, photons_in_window, sf_elev])
ax2d.set_title("Geolocated Photon Returns")
ax2dkde.set_title("Kernel Density with Horizonal windowing")
fig.show()

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
    ys=point_dataframe.Z_g,
    label="Photons in bathymetric returns",
    zorder=-1,
)
# lims = ax1.get_xlim()


startpt = 1000

for startpt in range(0, len(point_dataframe) - 100, 50):
    # find the x lodcation of the middle of the box, by taking average of start and end x coordinate
    s = (
        point_dataframe.dist_or.iloc[startpt]
        + point_dataframe.dist_or.iloc[startpt + 100]
    ) / 2
    # find the y,z values of the kde graph
    kdey, kdez = getkde(startpt, 200)

    ax2dkde.plot(kdez, kdey)
    # add rectangle showing the filter area
    # get the rectangle geometry first
    window_startpt = (point_dataframe.dist_or.iloc[startpt], -40)
    window_width = (
        point_dataframe.dist_or.iloc[startpt + 100]
        - point_dataframe.dist_or.iloc[startpt]
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

ax.set_zlabel("Probability Density")
ax.set_xlabel("Along-track distance [m]")
ax.set_ylabel("Depth +MSL [m]")
ax.set_zlim(0, 0.2)
ax.set_ylim(-50, 5)
fig.show()
fig.savefig("../document/figures/3d_kde_function.png")


# %% [markdown]
# # Kriging figures
# %%
pts = gpd.read_file("../data/test_sites/florida_keys/keys_testpts.gpkg")
pts_all = gpd.read_file("../data/test_sites/florida_keys/all_bathy_pts.gpkg")
# %%
with rasterio.open("../data/test_sites/florida_keys/kriging_output.tif") as krigedras:
    elevation = krigedras.read(1)
    uncertainty = krigedras.read(2)
    width = elevation.shape[1]
    height = elevation.shape[0]
    cols, rows = np.meshgrid(np.arange(width), np.arange(height))
    xs, ys = rasterio.transform.xy(krigedras.transform, rows, cols)
    xvals = np.array(xs)
    yvals = np.array(ys)

row = 300
oned_elev = elevation[row, :]
oned_uncert = uncertainty[row, :]
oned_xvals = xvals[row, :]
oned_yvals = yvals[row, :]

resolution = oned_xvals[1] - oned_xvals[0]

pts_in_area = pts.loc[
    (pts.Y > oned_yvals.min() - resolution / 2)
    & (pts.Y < oned_yvals.min() + resolution / 2)
]
pts_all_in_area = pts_all.loc[
    (pts_all.northing > oned_yvals.min() - resolution)
    & (pts_all.northing < oned_yvals.min() + resolution)
]
# %%
fig, ax = plt.subplots(figsize=(20, 10))
ax.set_title("1D section of Kriging results")

ax.plot(oned_xvals, oned_elev, label="Interpolated Line")
ax.fill_between(
    oned_xvals,
    oned_elev - np.sqrt(oned_uncert),
    oned_elev + np.sqrt(oned_uncert),
    color="gray",
    alpha=0.2,
    label="Uncertainty",
)

ax.scatter(
    x=pts_in_area.X,
    y=pts_in_area.Z,
    color="red",
    label="Remaining points after subsampling",
)

ax.legend(loc="lower left")
fig.savefig(
    "../document/figures/1d_kriging_section.jpg",
    dpi=500,
    bbox_inches="tight",
    facecolor="white",
)

with rasterio.open("../data/test_sites/florida_keys/bilinear.tif") as bilinear:
    gebco_elev = bilinear.read(1, masked=True)
    oned_gebco = gebco_elev[row, :]


ax.plot(oned_xvals, oned_gebco)

# %%

fig, ax = plt.subplots(figsize=(20, 10))
ax.set_title("Combination via Kalman Filter - 1D view")

ax.plot(oned_xvals, oned_elev, label="Kriged ICESat-2 Surface")
ax.fill_between(
    oned_xvals,
    oned_elev - np.sqrt(oned_uncert),
    oned_elev + np.sqrt(oned_uncert),
    color="#1f77b4",
    alpha=0.1,
    label="Kriged ICESat-2 Uncertainty",
)

with rasterio.open("../data/test_sites/florida_keys/bilinear.tif") as bilinear:
    gebco_elev = bilinear.read(1, masked=True)
    oned_gebco = gebco_elev[row, :]


ax.plot(oned_xvals, oned_gebco, label="GEBCO Interpolation", color="#ff7f0e")
ax.fill_between(
    oned_xvals,
    oned_gebco - 0.5,
    oned_gebco + 0.5,
    alpha=0.1,
    color="#ff7f0e",
    label="GEBCO Uncertainty",
)

with rasterio.open(
    "../data/test_sites/florida_keys/kalman_updated.tif"
) as kalman_raster:
    kalman_elev = kalman_raster.read(1)
    oned_kalman = kalman_elev[row, :]


ax.plot(
    oned_xvals,
    oned_kalman,
    label="Estimate with Kalman Filter",
    linewidth=3,
    color="#2ca02c",
)
ax.legend(loc="lower left")
ax.set_ylabel("Elevation [m]")
ax.set_xlabel("Easting [m UTM 17N]")
fig.savefig(
    "../document/figures/kalman_1d_section.jpg",
    dpi=500,
    bbox_inches="tight",
    facecolor="white",
)

# %%
with rasterio.open('../data/test_sites/florida_keys/kriging_output.tif') as bilinear_raster:
    fig, ax = plt.subplots(figsize=(20,10))
    ax.set_xlabel(f'Easting UTM 17N')
    ax.set_ylabel(f'Northing UTM 17N')
    ax.set_title('Location of 1D section')
    cx.add_basemap(ax,source=cx.providers.OpenTopoMap,crs=bilinear_raster.crs)
    image_hidden = ax.imshow(bilinear_raster.read(1,masked=True), 
                         cmap='inferno',)
    rastershow(bilinear_raster,cmap='inferno',ax=ax)
    ax.axhline(oned_yvals[0],linewidth=5)

    fig.colorbar(image_hidden,ax=ax)
    fig.savefig(fname='../document/figures/horizontal_section.jpg',bbox_inches='tight',facecolor='white',dpi=500)
