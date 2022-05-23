# %%
from atl_module import icesat_bathymetry
from sklearn.neighbors import KernelDensity
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle,ConnectionPatch
from mpl_toolkits.mplot3d import art3d


# %%
atl03_testfile = "../data/test_sites/florida_keys/ATL03/processed_ATL03_20201202073402_10560901_005_01.nc"
beam = "gt3l"

beamdata = icesat_bathymetry.load_beam_array_ncds(atl03_testfile, beam)

raw_data = icesat_bathymetry.add_along_track_dist(beamdata)
# .pipe(point_dataframe_filters.add_sea_surface_level)
point_dataframe = icesat_bathymetry._filter_points(raw_data)

# get a 1km
point_dataframe = point_dataframe.query("dist_or > 2000 and dist_or < 4000")

# %%
from atl_module.point_dataframe_filters import 

# %% [markdown]
# # Using a rolling kde
# 

# %%
from scipy.stats import gaussian_kde

# %%
def getkde(start,window):
    dataset = point_dataframe.Z_g[start:start+window]
    kde = gaussian_kde(dataset)
    xvals = np.linspace(0,-40,1000)
    y_density = kde.evaluate(xvals)
    return xvals,y_density

# %%
%matplotlib inline

# %%
# create a 3d figure showing how the rolling window kde function works to find the max density

# setup a figure to put the plots on
fig = plt.figure(figsize=(24,18),facecolor='w')
fig.suptitle('2D KDE windowing function')
# setup a 2 subplot first

ax2d = fig.add_subplot(2,2,1)
ax2d.scatter(
    point_dataframe.dist_or,
    point_dataframe.Z_g,
    label="Photons in bathymetric returns",
)
ax2d.grid()
ax2d.set_xlabel('Along-track Distance [m]')
ax2d.set_ylabel('Photon Location [m +msl]')

ax2dkde = fig.add_subplot(2,2,2)
ax2dkde.set_xlabel('Probability Density')
ax2dkde.set_ylabel('Photon Location [m +msl]')


# 3d plot
ax = fig.add_subplot(2,2,3,projection="3d")

ax.scatter(
    xs=point_dataframe.dist_or,
    ys=point_dataframe.Z_g,
    label="Photons in bathymetric returns",
)
# lims = ax1.get_xlim()


startpt = 1000

for startpt in [800,1200]:
    # find the x lodcation of the middle of the box, by taking average of start and end x coordinate
    s = (
        point_dataframe.dist_or.iloc[startpt]
        + point_dataframe.dist_or.iloc[startpt + 100]
    ) / 2
    # find the y,z values of the kde graph
    kdey, kdez = getkde(startpt, 200)

    ax2dkde.plot(kdez,kdey)
    # add rectangle showing the filter area
    # get the rectangle geometry first
    window_startpt = (point_dataframe.dist_or.iloc[startpt], point_dataframe.Z_g.min())
    window_width = (
        point_dataframe.dist_or.iloc[startpt + 100]
        - point_dataframe.dist_or.iloc[startpt]
    )
    window_height = point_dataframe.Z_g.max() - point_dataframe.Z_g.min()
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
    rec2 = Rectangle(
        window_startpt,
        window_width,
        window_height,
        zorder=3,
        color="black",
        fill=False,
        label="Window",
    )
    ax2d.add_patch(rec2)
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

    path = ConnectionPatch(xyA=(kdemax_z,kdemax_y),coordsA="data",axesA=ax2dkde,xyB=(s,kdemax_y),axesB=ax2d,coordsB="data")
    fig.add_artist(path)

    # plot the line from the max value to the 2d graph
    ax.plot(
        xs=[s, s],
        ys=[kdemax_y, kdemax_y],
        zs=[0, kdemax_z],
        marker="o",
        label="Location of maximum Kernel Density",
        c="r",
    )

ax.set_zlabel("Probability Density")
ax.set_xlabel("Along-track distance [m]")
ax.set_ylabel("Depth +MSL [m]")
ax.set_zlim(0, 0.2)
ax.set_ylim(-50, 5)
ax2d.set_ylim(-50, 5)
ax2dkde.set_ylim(-50, 5)
ax.legend()
ax2d.legend()
ax2dkde.legend()
ax.view_init()
fig.show()



# %%
fig.savefig('../document/figures/kde_function.png')

# %%
print(ax2d.transData)

# %%



