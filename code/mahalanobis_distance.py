# %%
import numpy as np
import matplotlib.pyplot as plt
from scipy.spatial import distance
import pandas as pd
import matplotlib.cm as cm

#%%
hscale = 5

df = pd.read_csv('../data/derived/mahalanobis_test_set.csv',index_col=0).query('dist_or > 10000 and dist_or < 11000')

pointarray = df.to_records()
xvals = np.array(pointarray.dist_or)/hscale
zvals = np.array(pointarray.Z_g)

xgridrange = np.linspace(xvals.min(),xvals.max(),1000)
zgridrange = np.linspace(zvals.min(),zvals.max(),2000)

meshx,meshz = np.meshgrid(xgridrange,zgridrange)

# %%
covariance_mat = np.cov(xvals,zvals)
IV = np.linalg.inv(covariance_mat)

obs_pts = np.vstack([xvals,zvals]).T
grid_pts = np.vstack([meshx.flatten(),meshz.flatten()]).T

xcenter = np.full_like(xvals,np.median(xvals))
zcenter = np.full_like(zvals,np.median(zvals))

midpoint_array = np.vstack([xcenter,zcenter]).T
midpoint_grid = np.vstack([xcenter_grid,zcenter_grid]).T


#%%

dist = distance.cdist(obs_pts,midpoint_array,metric='mahalanobis',VI=IV)
distgrid = distance.cdist(np.vstack([meshx.flatten(),meshz.flatten()]).T,[(np.median(xvals),np.median(zvals))],metric='mahalanobis',VI=IV).reshape(meshx.shape)
distgrid_euc = distance.cdist(np.vstack([meshx.flatten(),meshz.flatten()]).T,[(np.median(xvals),np.median(zvals))]).reshape(meshx.shape)



dist = np.diag(dist)

# %%
fig,ax = plt.subplots(figsize=(20,10))
CS = ax.contour(meshx,meshz,distgrid)
ax.clabel(CS, CS.levels,fontsize=20)
# plt.contour(meshx,meshz,distgrid_euc,color='red')
plt.scatter(xvals,zvals,c=dist)
# plt.axis('scaled')
plt.colorbar()
plt.show()
# %%

