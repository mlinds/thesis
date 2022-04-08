# %% [markdown]
# # DBSCAN distance metrics
# This notebook is used to explore different ways of parameterizing the DBSCAN algorithm to determine signal/noise points in the bathymetric returns
# %%
import numpy as np
import matplotlib.pyplot as plt
from scipy.spatial import distance
import pandas as pd
import matplotlib.cm as cm

#%%
hscale = 100
# %% [markdown]
## Loading an example set of bathymetric returns

# the data being loaded has already been filtered and is an example of the data that will be fed to the DBSCAN algorithm

# %%
df = pd.read_csv('../data/derived/mahalanobis_test_set.csv',index_col=0).query('dist_or > 17000 and dist_or < 19000')
df.plot.scatter(x='dist_or',y='Z_g')
# convert the dataframe to numpy and separate the X and Z values
pointarray = df.to_records()
xvals = np.array(pointarray.dist_or)/hscale
zvals = np.array(pointarray.Z_g)

# for the contours we need to establish a mesh grid based on the limits of the data
xgridrange = np.linspace(xvals.min(),xvals.max(),1000)
zgridrange = np.linspace(zvals.min(),zvals.max(),2000)
meshx,meshz = np.meshgrid(xgridrange,zgridrange)


# %% [markdown]
## Mahalanobis Distance
# The mahalanobis distance is based on the inverse of the covariance matrix. Therefore, the covariance of Z and X are found for this chunk

# %%
covariance_mat = np.cov(xvals,zvals)
IV = np.linalg.inv(covariance_mat)

obs_pts = np.vstack([xvals,zvals]).T
grid_pts = np.vstack([meshx.flatten(),meshz.flatten()]).T

xcenter = np.full_like(xvals,np.median(xvals))
zcenter = np.full_like(zvals,np.median(zvals))

midpoint_array = np.vstack([xcenter,zcenter]).T
# midpoint_grid = np.vstack([xcenter_grid,zcenter_grid]).T


#%%

pt_distance = distance.cdist(obs_pts,midpoint_array,metric='mahalanobis',VI=IV)
pt_distance_euc = distance.cdist(obs_pts,midpoint_array)
median_pt = [(np.median(xvals),np.median(zvals))]
distgrid = distance.cdist(np.vstack([meshx.flatten(),meshz.flatten()]).T,median_pt,metric='mahalanobis',VI=IV).reshape(meshx.shape)
distgrid_euc = distance.cdist(np.vstack([meshx.flatten(),meshz.flatten()]).T,median_pt).reshape(meshx.shape)

pt_distance = np.diag(pt_distance)
pt_distance_euc = np.diag(pt_distance_euc)

# %% [markdown]
# ### Mahalobis visualization
# The plot below shows the mahalanobis distance contours calculate for the data subset
# %%
fig,ax = plt.subplots(figsize=(20,10))
mah_contours = ax.contour(meshx,meshz,distgrid,levels=[0.2,1])
ax.clabel(mah_contours, mah_contours.levels,fontsize=20,fmt=lambda x:f'{x:.1f}m mah.')
ax.scatter(xvals,zvals,c=pt_distance)
fig.show()
# %% [markdown]
# ## Euclidian Distance

# This is the simple distance euclidian version. To ensure that we prefer horizontal neighbors, we can scale the horizontal distance down

# ### Euclidian Visualization
# %%
# add the contours of euclidian distance

fig,ax = plt.subplots(figsize=(20,10))
euc_contours = ax.contour(meshx,meshz,distgrid_euc,levels = 30)
ax.clabel(euc_contours,euc_contours.levels,fmt=lambda x:f'{x:.2f}m eucl.',fontsize=10)

ax.scatter(xvals,zvals,c=pt_distance_euc)
# plt.axis('scaled')
# ax.colorbar()
ax.set_title(f'Euclidian distance plot with {hscale}x horizontal scaling')
ax.set_xlabel(f'Horizontal Distance [m]')
ax.set_ylabel(f'Elevation [m +MSL]')
fig.show()
# %%

