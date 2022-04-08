# %%
import numpy as np
import matplotlib.pyplot as plt
from scipy.spatial import distance
import pandas as pd

#%%
df = pd.read_csv('../data/derived/mahalanobis_test_set.csv',index_col=0).query('dist_or > 9000 and dist_or < 11000')
df.plot.scatter(x='dist_or',y='Z_g')

pointarray = df.to_records()
xvals = np.array(pointarray.dist_or)
zvals = np.array(pointarray.Z_g)

xgridrange = np.linspace(xvals.min(),xvals.max(),10000)
zgridrange = np.linspace(zvals.min(),zvals.max(),10000)

covariance_mat = np.cov(xvals,zvals)
IV = np.linalg.inv(covariance_mat)
print(IV)
grid_pts = np.vstack([xgridrange,zgridrange]).T

xcenter = np.full_like(xgridrange,np.median(xvals))
zcenter = np.full_like(zgridrange,np.median(zvals))

midpoint_array = np.vstack([xcenter,zcenter]).T
#%%


dist = distance.cdist(grid_pts,midpoint_array,metric='mahalanobis',VI=IV)
print(dist.max())


h = plt.contourf(xgridrange,zgridrange,dist)
# plt.axis('scaled')
plt.colorbar()
plt.show()
# %%

