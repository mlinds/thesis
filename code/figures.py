# %%
from atl_module import icesat_bathymetry
from sklearn.neighbors import KernelDensity
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, ConnectionPatch
from mpl_toolkits.mplot3d import art3d
from atl_module.point_dataframe_filters import _interpolate_dataframe
from atl_module.refraction_correction import correct_refr
import matplotlib

plt.rcParams["font.family"] = "Sans Serif"


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
from scipy.stats import gaussian_kde

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
fig.suptitle("2D KDE windowing function")
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


for startpt in [800, 1200]:
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
    ax2d.scatter(
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

    ax2d.add_patch(rec)
    # get the max Z value of the kde
    kdemax_z = kdez.max()
    # find the corresponding y value
    kdemax_y = kdey[kdez.argmax()]

    # add the seafloor location
    ax2d.scatter(s, kdemax_y, label="Calculated Seafloor elev in middle of window")

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

ax2d.legend(["All Points", "Z elevation of Maximum KDE", "All points"])
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


# %%


# %%
