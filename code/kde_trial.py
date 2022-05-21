# %%
import atl03_utils
from sklearn.neighbors import KernelDensity
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


# %%
atl03_testfile = "../data/test_sites/florida_keys/ATL03/processed_ATL03_20200902115411_10560801_005_01.nc"
beam = "gt2r"

beamdata = atl03_utils.load_beam_array_ncds(atl03_testfile, beam)

point_dataframe = atl03_utils.add_track_dist_meters(beamdata)
point_dataframe = point_dataframe.bathy.filter_high_returns()
point_dataframe = point_dataframe.bathy.filter_TEP()
point_dataframe = point_dataframe.bathy.add_sea_level()
point_dataframe = point_dataframe.bathy.filter_low_points()
point_dataframe = point_dataframe.bathy.remove_surface_points()

# get a 1km
# point_dataframe = point_dataframe.query("dist_or > 7500 and dist_or < 9000")

# %%
hscale = 1000
pointarray = point_dataframe.to_records()
xvals = np.array(pointarray.dist_or) / hscale
zvals = np.array(pointarray.Z_g)

# for the contours we need to establish a mesh grid based on the limits of the data
xgridrange = np.linspace(xvals.min(), xvals.max(), 200)
zgridrange = np.linspace(zvals.min(), zvals.max(), 1000)
meshx, meshz = np.meshgrid(xgridrange, zgridrange)

# needed for mahalanobis distance

covariance_mat = np.cov(xvals, zvals)
IV = np.linalg.inv(covariance_mat)


xz = np.vstack([meshx.ravel(), meshz.ravel()]).T

# %%
trainingdata = np.vstack([xvals, zvals]).T

kde = KernelDensity(kernel="gaussian").fit(X=trainingdata)
out = kde.score_samples(xz)
density = np.exp(out)
outr = density.reshape(meshx.shape)


# %%
df = (
    pd.DataFrame(xz, columns=["dist_or", "Z"])
    .assign(density=density)
    .sort_values("dist_or")
)

zprofile = meshz[outr.argmax(axis=0), 0]
xprofile = meshx[0, :]

plt.figure(figsize=(10, 5))
plt.gca().set_ylim((-15, 3))
plt.contourf(meshx, meshz, outr, levels=50)
plt.plot(xprofile, zprofile)

# %%
