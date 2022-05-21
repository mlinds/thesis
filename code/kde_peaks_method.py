# %%
import numpy as np
import pandas as pd
from scipy.stats import gaussian_kde
from scipy.signal import find_peaks
from sklearn.neighbors import KernelDensity 
from KDEpy import FFTKDE

# %%
def get_elev_at_max_density(point_array, threshold):
    kde = gaussian_kde(point_array)
    kde_heights = kde.pdf(point_array)

    # find the Z value at the highest density
    z_at_kdemax = point_array[kde_heights.argmax()]
    # return if we don't have anything over the threshold
    if max(kde_heights) <= threshold:
        return np.NaN
    return z_at_kdemax

def get_elev_at_max_density_sklearn(point_array, threshold):
    kde = KernelDensity().fit(point_array[:,np.newaxis])
    kde_heights = kde.score_samples(point_array[:,np.newaxis])
    print(kde_heights)

    # find the Z value at the highest density
    z_at_kdemax = point_array[kde_heights.argmax()]
    # return if we don't have anything over the threshold
    if max(kde_heights) <= threshold:
        return np.NaN
    return z_at_kdemax

def get_elev_at_max_density_kdepy(point_array, threshold):
    x,y = FFTKDE(bw='ISJ').fit(point_array).evaluate()
    return x[y.argmax()]


# %%
df = _filter_points('../data/test_sites/florida_keys/ATL03/processed_ATL03_20210303031355_10561001_005_01.nc','gt2r')
testdata = df.iloc[500:800].Z_g.to_numpy()
# %%
