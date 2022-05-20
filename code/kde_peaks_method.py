# %%
from scipy.signal import find_peaks
from scipy.stats import gaussian_kde
from sklearn.neighbors import KernelDensity
import numpy as np
import pandas as pd

def find_two_peaks(point_array,threshold):
    # kdefit_array = point_array[:,np.newaxis]
    kde = gaussian_kde(point_array)
    # the np.exp is because sklearn returns the log-likelihood
    # xvals = np.linspace(point_array.min(),point_array.max(),10000)
    kde_heights = kde.pdf(point_array)
    # peaks,peak_properties = find_peaks(kde_heights,pr)
    z_at_kdemax = point_array[kde_heights.argmax()]
    if max(kde_heights) <= threshold:
        return np.NaN
    return z_at_kdemax
    # return max(kde_heights)

# %%
