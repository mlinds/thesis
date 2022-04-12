# %% [markdown]
#  # DBSCAN distance metrics
#  This notebook is used to explore different ways of parameterizing the DBSCAN algorithm to determine signal/noise points in the bathymetric returns

# %%
import numpy as np
import matplotlib.pyplot as plt
from scipy.spatial import distance
import pandas as pd
import matplotlib.cm as cm
import atl03_utils

# %%
hscale = 1

# %% [markdown]
# # Loading an example set of bathymetric returns
#  the data being loaded has already been filtered and is an example of the data that will be fed to the DBSCAN algorithm

# %%
atl03_testfile = "../data/test_sites/florida_keys/ATL03/processed_ATL03_20200902115411_10560801_005_01.nc"
beam = "gt1r"

beamdata = atl03_utils.load_beam_array_ncds(atl03_testfile, beam)

point_dataframe = atl03_utils.add_track_dist_meters(beamdata)
point_dataframe = point_dataframe.bathy.filter_high_returns()
point_dataframe = point_dataframe.bathy.filter_TEP()
point_dataframe = point_dataframe.bathy.add_sea_level()
point_dataframe = point_dataframe.bathy.filter_low_points()
point_dataframe = point_dataframe.bathy.remove_surface_points()

# get a 1km
point_dataframe = point_dataframe.query("dist_or > 7500 and dist_or < 9000")

# %%
# convert the dataframe to numpy and separate the X and Z values
pointarray = point_dataframe.to_records()
xvals = np.array(pointarray.dist_or) / hscale
zvals = np.array(pointarray.Z_g)

# for the contours we need to establish a mesh grid based on the limits of the data
xgridrange = np.linspace(xvals.min(), xvals.max(), 1000)
zgridrange = np.linspace(zvals.min(), zvals.max(), 2000)
meshx, meshz = np.meshgrid(xgridrange, zgridrange)

# %% [markdown]
# # Mahalanobis Distance
#  The mahalanobis distance is based on the inverse of the covariance matrix. Therefore, the covariance of Z and X are found for this chunk

# %%
covariance_mat = np.cov(xvals, zvals)
IV = np.linalg.inv(covariance_mat)

obs_pts = np.vstack([xvals, zvals]).T
grid_pts = np.vstack([meshx.flatten(), meshz.flatten()]).T

xcenter = np.full_like(xvals, np.median(xvals))
zcenter = np.full_like(zvals, np.median(zvals))

midpoint_array = np.vstack([xcenter, zcenter]).T
# midpoint_grid = np.vstack([xcenter_grid,zcenter_grid]).T


# %%
def plot_dist_contours(metric, **kwargs):
    median_pt = [(np.median(xvals), np.median(zvals))]

    pt_distance = distance.cdist(obs_pts, median_pt, metric=metric, **kwargs)

    distgrid = distance.cdist(
        np.vstack([meshx.flatten(), meshz.flatten()]).T,
        median_pt,
        metric=metric,
        **kwargs,
    ).reshape(meshx.shape)

    fig, ax = plt.subplots(figsize=(20, 10))
    contours = ax.contour(meshx, meshz, distgrid, levels=10)
    ax.clabel(
        contours, contours.levels, fontsize=20, fmt=lambda x: f"{x:.1f}m {metric[:3]}."
    )
    ax.scatter(xvals, zvals, c=pt_distance)

    ax.set_title(f"{metric} distance plot with {hscale}x horizontal scaling")
    ax.set_xlabel(f"Horizontal Distance [m]")
    ax.set_ylabel(f"Elevation [m +MSL]")

    fig.show()


# %% [markdown]
#  ### Mahalobis visualization
#  The plot below shows the mahalanobis distance contours calculate for the data subset

# %%
plot_dist_contours(metric="mahalanobis", VI=IV)

# %% [markdown]
#  ## Euclidian Distance
#  This is the simple distance euclidian version. To ensure that we prefer horizontal neighbors, we can scale the horizontal distance down
#  ### Euclidian Visualization

# %%
plot_dist_contours(metric="euclidean")

# %% [markdown]
# # Other Metrics

# %%
plot_dist_contours(metric="seuclidean")
plot_dist_contours(metric="minkowski")
plot_dist_contours(metric="sqeuclidean")
plot_dist_contours(metric="yule")
plot_dist_contours(metric="cityblock")


# %%
